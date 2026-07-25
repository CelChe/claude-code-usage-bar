# tests/test_cache.py
# ---------------------------------------------------------------------------
# atomic_write_text — the only surviving member of cache.py; used by every
# persistent state file in the package. (The old read_cache/write_cache/
# refresh_cache_background subsystem was removed as dead code.)
# ---------------------------------------------------------------------------
import os
from claude_statusbar.cache import atomic_write_text


def test_atomic_write_text_creates_file(tmp_path):
    p = tmp_path / "sub" / "file.txt"
    assert atomic_write_text(p, "hello") is True
    assert p.read_text(encoding="utf-8") == "hello"


def test_atomic_write_text_overwrites(tmp_path):
    p = tmp_path / "f.txt"
    atomic_write_text(p, "v1")
    atomic_write_text(p, "v2")
    assert p.read_text(encoding="utf-8") == "v2"


def test_atomic_write_text_no_temp_on_failure(tmp_path, monkeypatch):
    """If os.replace fails, the temp file must be cleaned up."""
    p = tmp_path / "f.txt"
    real_replace = os.replace

    def fail(*args, **kwargs):
        raise OSError("simulated")

    monkeypatch.setattr(os, "replace", fail)
    # write may or may not raise depending on inner handling — what matters
    # is no leftover .tmp file.
    try:
        atomic_write_text(p, "data")
    except OSError:
        pass
    leftover = list(tmp_path.glob(".f.txt.*.tmp"))
    assert leftover == [], f"temp files leaked: {leftover}"


def test_atomic_write_text_no_temp_on_success(tmp_path):
    p = tmp_path / "f.txt"
    atomic_write_text(p, "data")
    leftover = list(tmp_path.glob(".f.txt.*.tmp"))
    assert leftover == []


