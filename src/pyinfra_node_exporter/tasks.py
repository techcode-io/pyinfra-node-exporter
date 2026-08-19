from importlib import resources
from importlib.resources.abc import Traversable
from types import MappingProxyType
from typing import Final

from pyinfra.api import deploy
from pyinfra.context import host
from pyinfra.operations import files, server, systemd

from pyinfra_node_exporter.facts import BINARY_PATH, NodeExporterVersion

UNIT_PATH: Final[str] = "/etc/systemd/system/node_exporter.service"
DOWNLOAD_DIR: Final[str] = "/tmp/node_exporter"

DEFAULT_VERSION: Final[str] = "1.12.1"
DEFAULT_SYSTEM_USER: Final[str] = "node_exporter"
DEFAULT_SYSTEM_GROUP: Final[str] = "node_exporter"
DEFAULT_SERVICE_ARGS = MappingProxyType(
    {
        "collector.interrupts": None,
        "collector.processes": None,
        "collector.systemd": None,
        "no-collector.fibrechannel": None,
        "no-collector.infiniband": None,
        "no-collector.hwmon": None,
        "no-collector.nfs": None,
        "no-collector.nfsd": None,
        "no-collector.textfile": None,
        "no-collector.zfs": None,
        "web.listen-address": "127.0.0.1:9100",
    }
)

_TEMPLATE: Final[Traversable] = (
    resources.files("pyinfra_node_exporter") / "templates" / "node_exporter.service.j2"
)


@deploy("Install node_exporter")
def install(
    version: str = DEFAULT_VERSION,
    system_user: str = DEFAULT_SYSTEM_USER,
    system_group: str = DEFAULT_SYSTEM_GROUP,
    service_args: dict | None = None,
):
    server.group(
        name="Create node_exporter system group",
        group=system_group,
    )

    server.user(
        name="Create node_exporter system user",
        user=system_user,
        group=system_group,
        system=True,
        create_home=False,
        shell="/usr/sbin/nologin",
    )

    if host.get_fact(NodeExporterVersion) != version:
        files.directory(
            name="Prepare local download path",
            path=DOWNLOAD_DIR,
            mode=755,
            present=True,
        )

        archive = f"node_exporter-{version}.linux-amd64.tar.gz"

        files.download(
            name="Download node_exporter release binary",
            src=f"https://github.com/prometheus/node_exporter/releases/download/v{version}/{archive}",
            dest=f"{DOWNLOAD_DIR}/{archive}",
        )

        server.shell(
            name="Unarchive node_exporter release binary",
            commands=[f"tar -xvf {DOWNLOAD_DIR}/{archive} -C {DOWNLOAD_DIR}"],
        )

        server.shell(
            name="Copy all binaries",
            commands=[
                f"mv {DOWNLOAD_DIR}/node_exporter-{version}.linux-amd64/node_exporter {BINARY_PATH}",
            ],
        )

        files.directory(name="Clear download path", path=DOWNLOAD_DIR, present=False)

    files.template(
        name="Copy node_exporter systemd unit file",
        src=str(_TEMPLATE),
        dest=UNIT_PATH,
        node_exporter_system_user=system_user,
        node_exporter_system_group=system_group,
        node_exporter_service_args=service_args
        if service_args is not None
        else DEFAULT_SERVICE_ARGS,
    )

    systemd.daemon_reload(name="Reload systemd daemon")

    systemd.service(
        name="Restart and enable the node_exporter service",
        service="node_exporter.service",
        running=True,
        restarted=True,
        enabled=True,
    )


@deploy("Uninstall node_exporter")
def uninstall(
    system_user: str = DEFAULT_SYSTEM_USER,
    system_group: str = DEFAULT_SYSTEM_GROUP,
):
    systemd.service(
        name="Stop and disable the node_exporter service",
        service="node_exporter.service",
        running=False,
        enabled=False,
    )

    files.file(
        name="Remove node_exporter systemd unit file",
        path=UNIT_PATH,
        present=False,
    )

    systemd.daemon_reload(name="Reload systemd daemon")

    files.file(
        name="Remove node_exporter binary",
        path=BINARY_PATH,
        present=False,
    )

    server.user(
        name="Remove node_exporter system user",
        user=system_user,
        present=False,
    )

    server.group(
        name="Remove node_exporter system group",
        group=system_group,
        present=False,
    )
