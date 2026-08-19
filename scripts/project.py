"""Project maintenance script, invoked via poe (`uv run poe project:upgrade`)."""

import re
import sys
from pathlib import Path
from typing import Final

import urllib3

REPO_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
TASKS_PATH: Final[Path] = REPO_ROOT / "src" / "pyinfra_node_exporter" / "tasks.py"
README_PATH: Final[Path] = REPO_ROOT / "README.md"
LATEST_RELEASE_URL: Final[str] = (
    "https://api.github.com/repos/prometheus/node_exporter/releases/latest"
)
VERSION_PATTERN: Final[re.Pattern] = re.compile(
    r'^(?P<prefix>DEFAULT_VERSION(?::\s*Final\[str\])?\s*=\s*)"[^"]+"$', re.MULTILINE
)
README_SAMPLE_PATTERN: Final[re.Pattern] = re.compile(
    r'(?<=\n    version=")[^"]+(?=",\n)'
)
README_TABLE_PATTERN: Final[re.Pattern] = re.compile(
    r"(\| `install`\s*\| `version`\s*\| `)[^`]+(`\s*\|)"
)


def fetch_latest_version() -> str:
    """Return the latest node_exporter release version (eg ``1.12.1``), without the ``v`` prefix."""
    response = urllib3.request("GET", LATEST_RELEASE_URL)
    return response.json()["tag_name"].removeprefix("v")


def upgrade() -> None:
    """Bump DEFAULT_VERSION in tasks.py and README.md to the latest upstream node_exporter release."""
    latest = fetch_latest_version()
    content = TASKS_PATH.read_text()

    updated, count = VERSION_PATTERN.subn(rf'\g<prefix>"{latest}"', content, count=1)
    if count == 0:
        print(f"Could not find DEFAULT_VERSION in {TASKS_PATH}", file=sys.stderr)
        sys.exit(1)

    TASKS_PATH.write_text(updated)
    print(f"DEFAULT_VERSION set to {latest} in {TASKS_PATH.relative_to(REPO_ROOT)}")

    readme = README_PATH.read_text()
    readme_updated, sample_count = README_SAMPLE_PATTERN.subn(latest, readme, count=1)
    readme_updated, table_count = README_TABLE_PATTERN.subn(
        rf"\g<1>{latest}\g<2>", readme_updated, count=1
    )
    if sample_count == 0 or table_count == 0:
        print(
            f"Could not find DEFAULT_VERSION reference(s) in {README_PATH}",
            file=sys.stderr,
        )
        sys.exit(1)

    README_PATH.write_text(readme_updated)
    print(f"DEFAULT_VERSION set to {latest} in {README_PATH.relative_to(REPO_ROOT)}")
