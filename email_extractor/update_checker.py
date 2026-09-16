"""Update-checking infrastructure.

Network access is intentionally disabled until the project has a public GitHub
repository. Enabling it later requires setting both constants below.
"""

from dataclasses import dataclass
import json
from urllib.request import Request, urlopen


UPDATE_CHECK_ENABLED = True
GITHUB_REPOSITORY = "marcus300/petronect-email-extractor"
GITHUB_RELEASES_API_URL = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest"


@dataclass(frozen=True)
class UpdateStatus:
    enabled: bool
    current_version: str
    latest_version: str = ""
    release_url: str = ""

    @property
    def update_available(self) -> bool:
        return bool(
            self.latest_version
            and _version_tuple(self.latest_version) > _version_tuple(self.current_version)
        )


def _version_tuple(value: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in value.strip().removeprefix("v").split("."))
    except ValueError:
        return ()


def check_for_updates(current_version: str, timeout: float = 5.0) -> UpdateStatus:
    """Read the latest GitHub release only when explicitly enabled/configured."""
    if not UPDATE_CHECK_ENABLED or not GITHUB_RELEASES_API_URL:
        return UpdateStatus(False, current_version)

    request = Request(
        GITHUB_RELEASES_API_URL,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "PetronectEmailExtractor"},
    )
    with urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    return UpdateStatus(
        True,
        current_version,
        str(payload.get("tag_name", "")).removeprefix("v"),
        str(payload.get("html_url", "")),
    )
