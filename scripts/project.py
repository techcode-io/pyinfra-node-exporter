"""Project maintenance script, invoked via poe (`uv run poe project:upgrade`)."""

import os
import re
import sys
import uuid
from pathlib import Path
from typing import Final, NamedTuple

import urllib3


class VersionBump(NamedTuple):
    before: str
    after: str

    @property
    def changed(self) -> bool:
        return self.before != self.after


REPO_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
TASKS_PATH: Final[Path] = REPO_ROOT / "src" / "pyinfra_node_exporter" / "tasks.py"
README_PATH: Final[Path] = REPO_ROOT / "README.md"
LATEST_RELEASE_URL: Final[str] = (
    "https://api.github.com/repos/prometheus/node_exporter/releases/latest"
)
CURRENT_VERSION_PATTERN: Final[re.Pattern] = re.compile(
    r'^DEFAULT_VERSION(?::\s*Final\[str\])?\s*=\s*"(?P<version>[^"]+)"$', re.MULTILINE
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


def upgrade_node_exporter() -> VersionBump:
    """Bump DEFAULT_VERSION in tasks.py and README.md to the latest upstream node_exporter release."""
    content = TASKS_PATH.read_text()
    current_match = CURRENT_VERSION_PATTERN.search(content)
    if current_match is None:
        print(f"Could not find DEFAULT_VERSION in {TASKS_PATH}", file=sys.stderr)
        sys.exit(1)
    current = current_match.group("version")

    latest = fetch_latest_version()

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

    return VersionBump(current, latest)


def upgrade() -> None:
    """Bump DEFAULT_VERSION in tasks.py and README.md to the latest upstream node_exporter release."""
    upgrade_node_exporter()


def _write_github_output(values: dict[str, str]) -> None:
    """Append ``key=value`` pairs to the ``$GITHUB_OUTPUT`` file, using heredocs for multi-line values."""
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        print("GITHUB_OUTPUT is not set; skipping output write", file=sys.stderr)
        sys.exit(1)

    with Path(output_path).open("a") as fh:
        for key, value in values.items():
            if "\n" in value:
                delimiter = f"EOF_{uuid.uuid4().hex}"
                fh.write(f"{key}<<{delimiter}\n{value}\n{delimiter}\n")
            else:
                fh.write(f"{key}={value}\n")


def upgrade_ci() -> None:
    """Bump the node_exporter version and write the diff as GitHub Actions step outputs.

    Used by the Dependabot++ workflow (`.github/workflows/dependabot-plus-plus.yml`) in place of
    hand-rolled bash diffing, so the "what changed" and "how to describe it" logic lives in one
    tested place alongside the upgrade logic itself.
    """
    bump = upgrade_node_exporter()

    if not bump.changed:
        _write_github_output({"updated": "false"})
        return

    title = f"build(deps): bump node_exporter to {bump.after}"
    workflow_url = (
        f"https://github.com/{os.environ.get('GITHUB_REPOSITORY', '')}"
        "/actions/workflows/dependabot-plus-plus.yml"
    )
    body = "\n".join(
        [
            "## Summary",
            f"Automated update of the default node_exporter version from `{bump.before}` to `{bump.after}`.",
            "",
            (
                f"This PR updates `DEFAULT_VERSION` in `{TASKS_PATH.relative_to(REPO_ROOT)}` to track "
                "the latest upstream node_exporter release."
            ),
            "",
            "## Changes",
            (
                f"- `{TASKS_PATH.relative_to(REPO_ROOT)}` / `{README_PATH.relative_to(REPO_ROOT)}`: "
                f"`DEFAULT_VERSION` `{bump.before}` → `{bump.after}`"
            ),
            "",
            "## Release Notes",
            (
                f"See [node_exporter v{bump.after} release notes]"
                f"(https://github.com/prometheus/node_exporter/releases/tag/v{bump.after})"
            ),
            "",
            "---",
            f"🤖 This PR was created automatically by the [Dependabot++ workflow]({workflow_url})",
        ]
    )
    commit_message = (
        f"{title}\n\nUpdates node_exporter from {bump.before} to {bump.after}"
    )

    _write_github_output(
        {
            "updated": "true",
            "title": title,
            "branch": f"automation-upgrade-{bump.after}",
            "commit_message": commit_message,
            "body": body,
        }
    )
