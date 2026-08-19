import re

from pyinfra.api import FactBase

BINARY_PATH = "/usr/local/bin/node_exporter"

_VERSION_MATCHER = re.compile(r"node_exporter,\s+version\s+(?P<version>\S+)")


class NodeExporterVersion(FactBase):
    """
    Returns the currently installed node_exporter version (eg ``1.10.2``), or ``None`` if
    node_exporter is not installed.
    """

    def command(self) -> str:
        return f"{BINARY_PATH} --version 2>&1"

    def requires_command(self) -> str:
        return BINARY_PATH

    def process(self, output) -> str | None:
        match = _VERSION_MATCHER.search("\n".join(output))
        return match.group("version") if match else None
