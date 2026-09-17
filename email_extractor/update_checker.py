"""Query the official GitHub repository for the latest published release."""

from dataclasses import dataclass
import json
import re
import subprocess
from urllib.request import Request, urlopen


UPDATE_CHECK_ENABLED = True
GITHUB_REPOSITORY = "marcus300/petronect-email-extractor"
GITHUB_RELEASES_API_URL = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest"
GITHUB_LATEST_RELEASE_URL = f"https://github.com/{GITHUB_REPOSITORY}/releases/latest"
_TAG_URL_PATTERN = re.compile(r"/releases/tag/v?(\d+(?:\.\d+)+)(?:[/?#]|$)", re.IGNORECASE)


class UpdateCheckError(RuntimeError):
    """Raised when neither of the secure GitHub checks can be completed."""


@dataclass(frozen=True)
class UpdateStatus:
    enabled: bool
    current_version: str
    latest_version: str = ""
    release_url: str = ""
    source: str = ""

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


def _check_via_api(current_version: str, timeout: float) -> UpdateStatus:
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
        "github_api",
    )


def _latest_release_url_via_windows(timeout: float) -> str:
    """Resolve releases/latest with the Windows HTTPS and certificate stack."""
    timeout_seconds = max(1, int(round(timeout)))
    script = rf"""
$ErrorActionPreference = 'Stop'
[void][Reflection.Assembly]::LoadWithPartialName('System.Net.Http')
$handler = [System.Net.Http.HttpClientHandler]::new()
$handler.AllowAutoRedirect = $false
$client = [System.Net.Http.HttpClient]::new($handler)
$client.Timeout = [TimeSpan]::FromSeconds({timeout_seconds})
$client.DefaultRequestHeaders.UserAgent.ParseAdd('PetronectEmailExtractor')
try {{
    $response = $client.GetAsync('{GITHUB_LATEST_RELEASE_URL}').GetAwaiter().GetResult()
    $location = $response.Headers.Location
    if ($null -eq $location) {{ throw "O GitHub não retornou o redirecionamento da última release." }}
    if (-not $location.IsAbsoluteUri) {{
        $location = [Uri]::new([Uri]'{GITHUB_LATEST_RELEASE_URL}', $location)
    }}
    [Console]::OutputEncoding = [Text.Encoding]::UTF8
    [Console]::Write($location.AbsoluteUri)
}} finally {{
    $client.Dispose()
    $handler.Dispose()
}}
"""
    startup_info = None
    if hasattr(subprocess, "STARTUPINFO"):
        startup_info = subprocess.STARTUPINFO()
        startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    completed = subprocess.run(
        ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout + 3,
        check=True,
        startupinfo=startup_info,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return completed.stdout.strip()


def _check_via_release_link(current_version: str, timeout: float) -> UpdateStatus:
    release_url = _latest_release_url_via_windows(timeout)
    match = _TAG_URL_PATTERN.search(release_url)
    if not match:
        raise ValueError(f"URL da release sem versão reconhecida: {release_url!r}")
    return UpdateStatus(True, current_version, match.group(1), release_url, "github_release_link")


def check_for_updates(current_version: str, timeout: float = 5.0) -> UpdateStatus:
    """Check the API and securely fall back to GitHub's latest-release link on Windows."""
    if not UPDATE_CHECK_ENABLED or not GITHUB_RELEASES_API_URL:
        return UpdateStatus(False, current_version)

    try:
        return _check_via_api(current_version, timeout)
    except Exception as api_error:
        try:
            return _check_via_release_link(current_version, timeout)
        except Exception as fallback_error:
            raise UpdateCheckError(
                "API do GitHub: "
                f"{type(api_error).__name__}: {api_error}; "
                "link direto pelo Windows: "
                f"{type(fallback_error).__name__}: {fallback_error}"
            ) from fallback_error
