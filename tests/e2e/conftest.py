import subprocess
import time
import uuid
from collections.abc import Callable, Iterator
from functools import cache
from pathlib import Path
from shutil import which
from typing import Final

import pytest

from tests.conftest import PROJECT_TESTS_FIXTURES_DIR

IMAGE_TAG: Final[str] = "pyinfra-node-exporter-test:systemd"
SYSTEMD_CONTEXT_DIR: Final[Path] = PROJECT_TESTS_FIXTURES_DIR / "systemd"


def direct_bind(
    cmd: str, **override_kwargs
) -> Callable[..., subprocess.CompletedProcess]:
    """
    Create a callable that runs a command via subprocess.

    Args:
        cmd: command name to bind.
        **override_kwargs: keyword arguments to override in subprocess.run calls.
    Returns:
        A callable that runs the command with given arguments.
    """
    exe = which(cmd)
    if exe is None:
        raise FileNotFoundError(f"{cmd} not found")

    def run(*args, **kwargs):
        return subprocess.run(  # noqa: PLW1510 (check is always supplied via override_kwargs)
            [exe, *args],
            **{**kwargs, **override_kwargs},
        )

    return run


try:
    podman = direct_bind("podman", capture_output=True, text=True, check=False)
    podman_setup = direct_bind("podman", capture_output=True, check=True)
except FileNotFoundError:
    podman = podman_setup = None

pyinfra = direct_bind(
    "pyinfra", capture_output=True, text=True, timeout=300, check=False
)


@cache
def _podman_available() -> bool:
    if podman is None:
        return False
    return podman("info").returncode == 0


pytestmark = pytest.mark.skipif(
    not _podman_available(),
    reason="podman is not installed or its machine/socket is not running",
)


def podman_exec(container: str, command: str) -> subprocess.CompletedProcess:
    return podman("exec", container, "sh", "-c", command)


def run_pyinfra(container: str, script: str) -> subprocess.CompletedProcess:
    return pyinfra(
        "-y", f"@podman/{container}", str(PROJECT_TESTS_FIXTURES_DIR / script)
    )


@pytest.fixture(scope="module")
def systemd_container() -> Iterator[str]:
    podman_setup(
        "build",
        "-t",
        IMAGE_TAG,
        "-f",
        str(SYSTEMD_CONTEXT_DIR / "Containerfile"),
        str(SYSTEMD_CONTEXT_DIR),
    )

    container = f"pyinfra-node-exporter-test-{uuid.uuid4().hex[:8]}"
    podman_setup(
        "run",
        "-d",
        "--name",
        container,
        "--privileged",
        "--cgroupns=host",
        "-v",
        "/sys/fs/cgroup:/sys/fs/cgroup:rw",
        IMAGE_TAG,
    )

    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            status = podman_exec(
                container, "systemctl is-system-running"
            ).stdout.strip()
            if status in ("running", "degraded"):
                break
            time.sleep(1)
        else:
            raise RuntimeError(
                f"systemd never became ready in {container} (last status: {status!r})"
            )

        yield container
    finally:
        podman("rm", "-f", container)
