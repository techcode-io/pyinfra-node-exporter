# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`pyinfra-node-exporter` is a [pyinfra](https://pyinfra.com) extension package: it exposes
`install()` / `uninstall()` deploy functions that another pyinfra project imports to manage
Prometheus `node_exporter` on a host, instead of copy-pasting task files. It follows pyinfra's
`pyinfra_*` extension convention — deploy functions wrapped in `@deploy(...)` from `pyinfra.api`,
taking explicit keyword arguments rather than reading `host.data`, so the caller's inventory model
stays decoupled from this library.

## Commands

Managed with `uv`; a `poethepoet` task runner wraps the common commands (`pyproject.toml`
`[tool.poe.tasks]`):

- `uv sync` — install/update the dev environment
- `uv run poe lint` (or `uv run ruff check src`) — lint
- `uv run poe fmt` — fix import order + format (`ruff check --select I --fix` then `ruff format`)
- `uv run poe test` (or `uv run pytest tests`) — run the test suite
- `uv run pytest tests/e2e/test_tasks.py::test_install_then_uninstall -v` — run the single e2e test
- `uv run poe env:configure` — install pre-commit hooks (ruff-check, ruff-format, LF line endings,
  gitlint) for local development

Always invoke tools through `uv run <tool>` (or the `poe` tasks above). Do not call
`.venv/bin/<tool>` directly — `uv run` is what keeps the environment synced with `pyproject.toml`/
`uv.lock` before running, so a stale `.venv` doesn't silently mask dependency changes.

## Architecture

Source lives under `src/pyinfra_node_exporter/` (src layout, `uv_build` backend):

- **`tasks.py`** — the two public deploy functions, `install()` and `uninstall()`. `install()` is
  idempotent and does everything in one call: creates the system user/group, downloads/installs
  the `linux-amd64` binary (only when needed — see below), renders the systemd unit from the
  bundled Jinja template, and enables/starts the service. `uninstall()` reverses all of it.
  Deliberately *not* split into separate install/configure steps — pyinfra operations are cheap to
  re-run, and a separate `configure()` would be a footgun (nothing running until both are called).
- **`facts.py`** — `NodeExporterVersion`, a pyinfra `FactBase` that runs
  `node_exporter --version` and parses the installed version, gated by `requires_command` so it
  returns `None` cleanly when the binary isn't present yet. Also owns `BINARY_PATH`, the one path
  constant shared with `tasks.py` (imported from there, not the other way — `facts.py` has no
  dependency on `tasks.py`, keep it that way to avoid a circular import). `install()` calls
  `host.get_fact(NodeExporterVersion)` and skips the entire download/unarchive/copy block when it
  already matches the requested `version`.
- **`templates/node_exporter.service.j2`** — the systemd unit template, resolved via
  `importlib.resources.files("pyinfra_node_exporter")` (not a `__file__`-relative path) so it
  works both editable and installed as a wheel.
- **`__init__.py`** — re-exports the public surface: `install`, `uninstall`, `NodeExporterVersion`,
  and the `DEFAULT_*` constants.

The library only ever downloads `linux-amd64` release binaries (matching the upstream
`node_exporter` release layout it was extracted from) — this is intentional, not an oversight; add
arch support only if actually asked for.

## Testing

`tests/e2e/` runs the deploy functions against a **real systemd** container via pyinfra's native
`@podman` connector (not `@docker` — podman is what's available/aliased in this environment;
`pyinfra @podman/<container>` works because pyinfra ships a `PodmanConnector`). This is necessary
because the whole point of `install()`/`uninstall()` is systemd unit management, which a bare
Docker container can't exercise.

- `tests/fixtures/systemd/Containerfile` builds a minimal systemd-enabled Debian 12 image.
- `tests/e2e/conftest.py`'s `systemd_container` fixture builds that image, starts a
  `--privileged --cgroupns=host` container with `/sys/fs/cgroup` mounted, polls
  `systemctl is-system-running` until ready, and yields the container name; the whole module
  auto-skips (with a clear reason) if `podman` isn't installed or its machine/socket isn't
  reachable.
- `tests/e2e/test_tasks.py` invokes the real `pyinfra` CLI (via `run_pyinfra()`, a subprocess
  helper) against `@podman/<container>` running `tests/fixtures/tasks_install.py` /
  `tasks_uninstall.py`, then asserts on-disk/systemd state via `podman exec`.

**Architecture caveat baked into the tests:** the downloaded binary is amd64-only, so on a
non-amd64 host (e.g. Podman-on-Apple-Silicon via emulation) the Go runtime crashes for reasons
unrelated to this library (a `taggedPointerPack` Go runtime issue under QEMU/Rosetta emulation).
Structural assertions (files/user/group/unit present, service enabled) run unconditionally; the
assertions that require actually *running* the binary (service `active`, `/metrics` responding,
and the reinstall-skips-download check, since the version fact itself execs the binary) are gated
behind `_IS_NATIVE_AMD64 = platform.machine() in ("x86_64", "amd64")` in `test_tasks.py`. When
debugging a failure on Apple Silicon, don't assume it's a real regression — check whether it's this
known emulation crash first (look for `taggedPointerPack` in the output).

CI (`.github/workflows/ci.yml`) installs `podman` via `apt-get` before the test job for exactly
this reason — skip that step and the e2e test still "passes" by doing nothing.

On macOS, a stopped podman machine (`podman machine start`) looks identical to podman being
absent — `_podman_available()` returns `False` either way and the module just skips.

`subprocess.run` calls where `check=` is supplied dynamically through `**kwargs` (see
`direct_bind()` in `tests/e2e/conftest.py`) need `# noqa: PLW1510` — ruff can't verify it
statically.

## Conventions

- README/`.github/` scaffolding (badges, section layout, issue/PR templates, `dependabot.yml`,
  `labels.yml`, the CI shape) is deliberately copied from sibling `techcode-io` repos (`ignity`,
  `temply`) — check those before inventing new structure or wording.
- Commit titles must satisfy `.gitlint`: `type: subject` where type is one of
  `build|ci|docs|feat|fix|perf|refactor|test|chore|release`, 5-80 chars total; enforced by the
  commit-msg pre-commit hook.
