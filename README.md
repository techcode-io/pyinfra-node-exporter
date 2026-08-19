<h1 align="center">Pyinfra Node Exporter</h1>

<p align="center">
  <i align="center">Install and uninstall Prometheus node_exporter with pyinfra.</i>
</p>

<h4 align="center">
  <a href="https://github.com/techcode-io/pyinfra-node-exporter/actions/workflows/ci.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/techcode-io/pyinfra-node-exporter/ci.yml?branch=main&label=ci&style=flat-square" alt="continuous integration" style="height: 20px;">
  </a>
  <a href="https://github.com/techcode-io/pyinfra-node-exporter/graphs/contributors">
    <img src="https://img.shields.io/github/contributors-anon/techcode-io/pyinfra-node-exporter?color=yellow&style=flat-square" alt="contributors" style="height: 20px;">
  </a>
  <a href="https://opensource.org/licenses/Apache-2.0">
    <img src="https://img.shields.io/badge/apache%202.0-blue.svg?style=flat-square&label=license" alt="license" style="height: 20px;">
  </a>
  <br>
</h4>

- [Source](https://github.com/techcode-io/pyinfra-node-exporter)
- [Issues](https://github.com/techcode-io/pyinfra-node-exporter/issues)
- [Contact](mailto:adrien.mannocci@gmail.com)
- [Maintained by techcode.io](https://techcode.io)

## :package: Prerequisites

- [uv](https://docs.astral.sh/uv/) for development.
- [Podman](https://podman.io/docs) to run the end-to-end tests.

## :sparkles: Features

- Idempotent `install()`: system user/group, binary, systemd unit and running service in one call.
- Skips re-downloading the binary when the installed version already matches, using a pyinfra fact.
- `uninstall()` reverses everything: service, unit file, binary, user and group.
- Deploy functions only, no CLI: import it into any [pyinfra](https://pyinfra.com) project.

## :dart: Motivation

- We needed to manage `node_exporter` the same way across every server we operate.
- The solution should be reusable across pyinfra projects instead of copy-pasted between deploy scripts.
- The solution should be idempotent and skip work that has already been done.

## :hammer: Workflow

### Setup

The following steps will ensure your project is cloned properly.

1. Clone repository:
   ```shell
   git clone https://github.com/techcode-io/pyinfra-node-exporter
   cd pyinfra-node-exporter
   ```
2. Install dependencies and setup environment:
   ```shell
   uv sync
   uv run poe env:configure
   ```

### Lint

- To lint you have to use the workflow.

```bash
uv run poe lint
```

### Format

- To format you have to use the workflow.

```bash
uv run poe fmt
```

- It will format the project code using `ruff`.

### Test

- To test you have to use the workflow.
- Tests are based on `pytest` and run the deploy functions against a real systemd container via Podman.

```bash
uv run poe test
```

## 📖 Usage

### How it works

- `install()` and `uninstall()` are [pyinfra](https://pyinfra.com) deploy functions, wrapped with `@deploy(...)`.
- They take explicit keyword arguments instead of reading `host.data`, so any inventory can use them.
- `install()` creates the system user/group, downloads the `node_exporter` release binary, renders the systemd unit
  from a bundled template, then enables and starts the service.
- Before downloading, it checks the currently installed version using a pyinfra fact and skips the download entirely
  if it already matches.
- `uninstall()` stops and disables the service, then removes the unit file, binary, user and group.

### How to install node_exporter

- This project isn't published to PyPI yet, so add it as a git dependency pinned to a commit.
- Find the commit you want to pin to on the [commit history](https://github.com/techcode-io/pyinfra-node-exporter/commits/main),
  then add it to your pyinfra project.

```bash
uv add git+https://github.com/techcode-io/pyinfra-node-exporter --rev <commit-sha>
# or
pip install git+https://github.com/techcode-io/pyinfra-node-exporter@<commit-sha>
```

- This adds the following to your `pyproject.toml`, which you can also edit directly.

```toml
[project]
dependencies = ["pyinfra-node-exporter"]

[tool.uv.sources]
pyinfra-node-exporter = { git = "https://github.com/techcode-io/pyinfra-node-exporter", rev = "<commit-sha>" }
```

- Then call `install()` from a deploy script.

```python
from pyinfra_node_exporter import install

install()
```

### How to uninstall node_exporter

- Call `uninstall()` from a deploy script.

```python
from pyinfra_node_exporter import uninstall

uninstall()
```

### How to customize the install

- All functions accept keyword arguments; defaults match the upstream node_exporter release layout for `linux-amd64`.

```python
from pyinfra_node_exporter import DEFAULT_SERVICE_ARGS, install

install(
    version="1.10.2",
    system_user="node_exporter",
    system_group="node_exporter",
    service_args={
        **DEFAULT_SERVICE_ARGS,
        "web.listen-address": "0.0.0.0:9100",
    },
)
```

| Function                | Parameter       | Default                | Description                                                                    |
|-------------------------|-----------------|-------------------------|----------------------------------------------------------------------------------|
| `install`, `uninstall`  | `system_user`   | `node_exporter`         | System user running the service                                                |
| `install`, `uninstall`  | `system_group`  | `node_exporter`         | System group running the service                                               |
| `install`               | `version`       | `1.10.2`                | node_exporter release version to download                                      |
| `install`               | `service_args`  | `DEFAULT_SERVICE_ARGS`  | Dict of `--flag: value` (or `None` for a bare flag) passed to `node_exporter`  |

## :heart: Contributing

If you find this project useful here's how you can help, please click the :eye: **Watch** button to avoid missing
notifications about new versions, and give it a :star2: **GitHub Star**!

You can also contribute by:

- Sending a [Pull Request](https://github.com/techcode-io/pyinfra-node-exporter/pulls) with your awesome new features and bug fixed.
- Be part of the community and help resolve [Issues](https://github.com/techcode-io/pyinfra-node-exporter/issues).

## 🧾 License

The `pyinfra-node-exporter` project is free and open-source software licensed under the Apache-2.0 license.
