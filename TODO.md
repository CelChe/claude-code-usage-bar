# TODO

Fork-local backlog. This fork runs on Windows only — everything below is
non-Windows weight that was **not** cheap or risk-free to remove in the same
pass that deleted the POSIX installers, `packaging/`, and the release-binaries
workflow.

Each item names why it was deferred. The recurring cost is the same one: these
live inside files upstream edits often, so cutting them turns every future
`git merge upstream/main` into a conflict resolution inside load-bearing code.

## Deferred removals

- [ ] **`service.py` — launchd / systemd auto-start.** Already reports
  `unsupported platform 'win32'` in `cs doctor`. Removing it means editing
  `cli.py:173-186` (the `daemon install|uninstall|service` subcommands),
  `doctor.py:189-198` (the service health line), and deleting
  `tests/test_service.py`. Three files plus a test file, all of which upstream
  touches.

- [ ] **macOS desktop HUD — `hud.py` (25KB), `hud_data.py` (7.6KB).**
  `hud.py:12` imports `AppKit`, so the whole feature is PyObjC/macOS. Wired
  into `cli.py:26` as the `hud` subcommand and into the launchd plist helpers
  (`_hud_plist_path`, `_hud_program_args`). Biggest single chunk of dead weight
  here, and the most entangled with `cli.py`.

- [ ] **POSIX branches inside `daemon.py`.** The `/proc/<pid>/cmdline` read and
  the `ps -o command=` fallback in `_process_is_our_daemon` (the win32 path via
  CIM is already ours, commit `077c90b`), plus the `signal.SIGALRM` render
  timeout at `daemon.py:457` which is inert on Windows anyway
  (`have_alarm = hasattr(signal, "SIGALRM")`). Runs every second on the live
  render path — highest merge tax, lowest payoff.

- [ ] **`darwin` / frozen-binary paths** in `cli.py`, `doctor.py`, `updater.py`.
  Includes `INSTALL_SH_URL` and `BINARY_UPGRADE_HINT` in `updater.py:23-24`,
  which now point at an `install.sh` that no longer exists in this fork (the
  URL targets upstream's copy, so nothing breaks — it is just misleading).

- [ ] **POSIX-flavoured docs and assets** — `docs/install.md`, `demo/`
  (`record_demo.sh`), `promotion/` (48KB), `PROMOTION_PLAN.md`, and the
  `curl … install.sh | bash` prose in `.claude-plugin/marketplace.json` and
  `.claude-plugin/plugin.json`. Zero runtime risk; deferred only because it is
  churn against files upstream rewrites every release.

- [ ] **`.github/workflows/ci.yml`** runs on `ubuntu-latest` and fires on every
  push to this fork. Kept deliberately: it is the only signal that a change
  here still works on the platform upstream targets, which matters while PRs
  #37-#40 are open.

## Fork divergence worth remembering

Local-only commits that must never be sent upstream, in case a merge ever
tries to reconcile them:

- `ec96763` — updater refuses to pip-install over a source checkout.
- `ef34bd9` — 18 POSIX-only test cases deleted outright.
- this pass — POSIX installers, `packaging/`, release-binaries workflow.
