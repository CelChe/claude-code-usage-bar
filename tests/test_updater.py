import pytest

import claude_statusbar.updater as updater

# Captured before the autouse fixture below stubs it out for every test.
_REAL_IS_SOURCE_CHECKOUT = updater._is_source_checkout


@pytest.fixture(autouse=True)
def _not_a_source_checkout(monkeypatch):
    """Default every test to the installed-copy case.

    The suite normally runs from an editable clone, where the real
    `_is_source_checkout()` is True and short-circuits the upgrade paths.
    Tests that care about the guard override this explicitly.
    """
    monkeypatch.setattr(updater, "_is_source_checkout", lambda: False)


def test_detect_install_channel_uv():
    path = "/Users/test/.local/share/uv/tools/claude-statusbar/bin/python"
    assert updater.detect_install_channel(path) == "uv"


def test_detect_install_channel_pipx():
    path = "/Users/test/.local/pipx/venvs/claude-statusbar/bin/python"
    assert updater.detect_install_channel(path) == "pipx"


def test_detect_install_channel_falls_back_to_pip():
    path = "/Users/test/miniconda3/bin/python"
    assert updater.detect_install_channel(path) == "pip"


def test_get_upgrade_command_prefers_uv(monkeypatch):
    monkeypatch.setattr(updater.shutil, "which", lambda name: "/usr/bin/uv" if name == "uv" else None)
    cmd = updater.get_upgrade_command(
        "/Users/test/.local/share/uv/tools/claude-statusbar/bin/python"
    )
    assert cmd == ["/usr/bin/uv", "tool", "install", "--upgrade", "claude-statusbar"]


def test_get_upgrade_command_prefers_pipx(monkeypatch):
    monkeypatch.setattr(updater.shutil, "which", lambda name: "/usr/bin/pipx" if name == "pipx" else None)
    cmd = updater.get_upgrade_command(
        "/Users/test/.local/pipx/venvs/claude-statusbar/bin/python"
    )
    assert cmd == ["/usr/bin/pipx", "upgrade", "claude-statusbar"]


def test_get_upgrade_command_falls_back_to_pip(monkeypatch):
    monkeypatch.setattr(updater.shutil, "which", lambda name: None)
    cmd = updater.get_upgrade_command("/Users/test/miniconda3/bin/python")
    assert cmd == [updater.sys.executable, "-m", "pip", "install", "--upgrade", "claude-statusbar"]


def test_uv_channel_without_uv_anywhere_falls_back_to_pip(monkeypatch):
    monkeypatch.setattr(updater.shutil, "which", lambda name: None)
    monkeypatch.setattr(updater, "_TOOL_DIRS", ())
    cmd = updater.get_upgrade_command(
        "/Users/test/.local/share/uv/tools/claude-statusbar/bin/python"
    )
    assert cmd[0] == updater.sys.executable


# ---------------------------------------------------------------------------
# Reliability: subprocess timeout MUST be enforced so a hung pip/uv install
# can never freeze the Claude Code statusLine render.
# ---------------------------------------------------------------------------
import subprocess


def test_run_upgrade_passes_timeout(monkeypatch):
    """_run_upgrade must always pass a timeout kwarg to subprocess.run."""
    captured = {}

    class FakeResult:
        returncode = 0

    def fake_run(*args, **kwargs):
        captured.update(kwargs)
        return FakeResult()

    monkeypatch.setattr(updater.subprocess, "run", fake_run)
    updater._run_upgrade(["echo", "hi"])
    assert "timeout" in captured
    assert captured["timeout"] == updater._UPGRADE_TIMEOUT_S


def test_run_upgrade_returns_false_on_timeout(monkeypatch):
    def hang(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs.get("timeout", 0))

    monkeypatch.setattr(updater.subprocess, "run", hang)
    assert updater._run_upgrade(["pip", "install", "x"]) is False


def test_run_upgrade_returns_false_on_oserror(monkeypatch):
    def boom(*args, **kwargs):
        raise FileNotFoundError("no such binary")

    monkeypatch.setattr(updater.subprocess, "run", boom)
    assert updater._run_upgrade(["nonexistent-tool"]) is False


def test_auto_upgrade_falls_through_to_pip(monkeypatch):
    """When primary and pipx upgrades fail, auto_upgrade must still try pip
    rather than re-raising or hanging."""
    calls = []

    class FakeResult:
        def __init__(self, rc): self.returncode = rc

    def fake_run(cmd, **kwargs):
        calls.append(cmd[0])
        return FakeResult(1)  # always fail

    monkeypatch.setattr(updater.subprocess, "run", fake_run)
    monkeypatch.setattr(updater.shutil, "which", lambda name: "/usr/bin/pipx" if name == "pipx" else None)

    assert updater.auto_upgrade() is False
    # Must have attempted pip after the others failed
    assert any("python" in c or c == "pip" or "/python" in c for c in calls), \
        f"auto_upgrade did not fall through to pip: {calls}"


def test_upgrade_current_install_reports_manual_command(monkeypatch):
    monkeypatch.setattr(updater, "get_current_version", lambda: "3.26.0")
    monkeypatch.setattr(
        updater,
        "get_upgrade_command",
        lambda: ["uv", "tool", "install", "--upgrade", "claude-statusbar"],
    )
    monkeypatch.setattr(updater, "_run_upgrade", lambda cmd: False)

    ok, msg = updater.upgrade_current_install()

    assert ok is False
    assert "uv tool install --upgrade claude-statusbar" in msg


def test_auto_upgrade_refuses_to_clobber_source_checkout(monkeypatch):
    """A PyPI install over an editable clone silently replaces local commits."""
    monkeypatch.setattr(updater, "_is_source_checkout", lambda: True)
    monkeypatch.setattr(
        updater, "_run_upgrade",
        lambda cmd: pytest.fail(f"attempted upgrade over a checkout: {cmd}"),
    )

    assert updater.auto_upgrade() is False


def test_upgrade_current_install_points_at_git_pull_for_checkout(monkeypatch):
    monkeypatch.setattr(updater, "_is_source_checkout", lambda: True)
    monkeypatch.setattr(updater, "get_current_version", lambda: "3.32.0")
    monkeypatch.setattr(
        updater, "_run_upgrade",
        lambda cmd: pytest.fail(f"attempted upgrade over a checkout: {cmd}"),
    )

    ok, msg = updater.upgrade_current_install()

    assert ok is False
    assert "git -C" in msg and "pull" in msg


def test_source_checkout_detected_for_this_clone():
    """Guards the layout sniff itself — only meaningful when the suite runs
    from the repo (the normal `pip install -e .` dev setup)."""
    from pathlib import Path
    repo = Path(updater.__file__).resolve().parents[2]
    if not (repo / "pyproject.toml").is_file():
        pytest.skip("not running from a source checkout")
    assert _REAL_IS_SOURCE_CHECKOUT() is True
