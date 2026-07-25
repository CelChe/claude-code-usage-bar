import sys

import pytest


# ---------------------------------------------------------------------------
# POSIX-only tests (fork-local)
# ---------------------------------------------------------------------------
# These assert behaviour Windows does not have. They fail here for reasons that
# have nothing to do with the code under test, and a permanently red suite hides
# real regressions. Skipped by node id rather than by editing the test files, so
# merges from upstream never conflict on this.
_POSIX_ONLY = {
    # time.tzset() is Unix-only, so the fixture's timezone switch is a no-op and
    # every bucket assertion downstream compares against the wrong local time.
    "test_projection.py::test_bucket_for_time_distinguishes_weekday_work_weekend_and_night": "time.tzset",
    "test_projection.py::test_bucket_for_time_uses_system_local_timezone": "time.tzset",
    "test_projection.py::test_learned_bucket_rates_from_positive_deltas": "time.tzset",
    "test_projection.py::test_learned_bucket_rates_compress_duplicate_plateaus": "time.tzset",
    "test_projection.py::test_learned_bucket_rates_ignore_stale_lower_session_readings": "time.tzset",
    "test_projection.py::test_learned_bucket_rates_accept_heavy_real_5h_burn": "time.tzset",
    "test_projection.py::test_integrate_future_buckets_uses_future_schedule": "time.tzset",

    # Windows ignores the Unix permission bits these rely on: a read-only
    # directory still accepts writes, an unreadable file still reads.
    "test_cache.py::test_atomic_write_text_returns_false_on_readonly_dir": "unix permission bits",
    "test_setup.py::test_project_setup_refuses_unreadable_existing_file": "unix permission bits",

    # Symlink creation needs SeCreateSymbolicLinkPrivilege (WinError 1314).
    "test_updater.py::test_detect_install_channel_uv_tool_python_symlink": "symlink privilege",
    "test_updater.py::test_uv_found_in_well_known_dir_when_not_on_path": "symlink privilege",

    # Path.home() reads USERPROFILE on Windows, so monkeypatching HOME does not
    # isolate these — they read (and write) the developer's real cache.
    "test_balance_render.py::test_no_spawn_when_spawn_false": "HOME not honoured",
    "test_no_quota_integration.py::test_heuristic_switches_layout_without_env": "HOME not honoured",

    # pip names the launcher cs.EXE; these compare against the bare name.
    "test_setup.py::test_creates_statusline_when_missing": "cs.EXE shim name",
    "test_setup.py::test_project_setup_creates_fresh_settings": "cs.EXE shim name",

    # flock locks an inode; Windows has no equivalent.
    "test_daemon.py::test_release_pidfile_leaves_someone_elses_file_alone": "flock inode semantics",

    # workspace_id hashes a path; separators differ from the POSIX fixtures.
    "test_party.py::test_workspace_id_matches_agentparty_fixtures": "path separators",
    "test_party.py::test_reads_statusline_cache_and_renders_no_color": "path separators",
}


def pytest_collection_modifyitems(items):
    if sys.platform != "win32":
        return
    for item in items:
        nodeid = item.nodeid.replace("\\", "/")
        for suffix, reason in _POSIX_ONLY.items():
            if nodeid.endswith(suffix):
                item.add_marker(pytest.mark.skip(reason=f"POSIX-only: {reason}"))
                break


@pytest.fixture(autouse=True)
def _isolate_rate_latest(tmp_path, monkeypatch):
    """Keep every test off the real ~/.cache/claude-statusbar/rate_latest.json.

    predict.reconcile_account (reached via forecast() and core.main's render
    path) reads+writes that shared account-global store. Without isolation tests
    would pollute the developer's real cache and leak state into each other.
    Each test gets its own throwaway path."""
    try:
        import claude_statusbar.predict as predict
        monkeypatch.setattr(predict, "_LATEST_PATH", tmp_path / "rate_latest.json")
        monkeypatch.setattr(predict, "_PROJECTION_PATH", tmp_path / "rate_projection.json")
        # Stores are account-keyed (suffix from ~/.claude.json); pin the
        # account to "unknown" so tests get the exact paths they monkeypatch,
        # independent of the developer's real login. Account-switch tests
        # override this stub locally.
        monkeypatch.setattr(predict, "account_id", lambda: None)
    except Exception:
        pass
    # Same problem in the relay-balance cache: it resolves its directory with
    # os.path.expanduser("~"), which on Windows reads USERPROFILE and ignores
    # the HOME the tests monkeypatch — so a passing test writes a fake
    # `bal $1,234.50` entry into the developer's live cache. Pin it.
    try:
        import claude_statusbar.balance_cache as balance_cache
        monkeypatch.setattr(balance_cache, "_cache_root",
                            lambda: tmp_path / "balance")
    except Exception:
        pass
