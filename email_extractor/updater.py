"""Secure download and deferred replacement of the Windows executable."""

from collections.abc import Callable
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .update_checker import GITHUB_REPOSITORY, UpdateStatus


TRUSTED_DOWNLOAD_HOSTS = frozenset(
    {"github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com"}
)
MAX_UPDATE_SIZE = 250 * 1024 * 1024


class UpdateDownloadError(RuntimeError):
    pass


@dataclass(frozen=True)
class DownloadedUpdate:
    path: Path
    version: str
    sha256: str
    size: int


def _validate_asset(status: UpdateStatus) -> None:
    expected = {
        f"Petronect.Email.Extractor.v{status.latest_version}.exe",
        f"Petronect Email Extractor v{status.latest_version}.exe",
    }
    if status.asset_name not in expected or Path(status.asset_name).suffix.casefold() != ".exe":
        raise UpdateDownloadError("A release não contém o executável oficial esperado.")
    parsed = urlparse(status.asset_url)
    expected_prefix = f"/{GITHUB_REPOSITORY}/releases/download/".casefold()
    if parsed.scheme != "https" or parsed.hostname != "github.com" or not parsed.path.casefold().startswith(expected_prefix):
        raise UpdateDownloadError("A URL do executável não pertence ao repositório oficial.")
    if status.asset_size < 0 or status.asset_size > MAX_UPDATE_SIZE:
        raise UpdateDownloadError("O tamanho informado para a atualização é inválido.")


def _validate_final_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in TRUSTED_DOWNLOAD_HOSTS:
        raise UpdateDownloadError("O download foi redirecionado para uma origem não autorizada.")


def _is_windows_pe(path: Path) -> bool:
    try:
        with path.open("rb") as executable:
            header = executable.read(64)
            if len(header) < 64 or header[:2] != b"MZ":
                return False
            pe_offset = int.from_bytes(header[0x3C:0x40], "little")
            if pe_offset < 64 or pe_offset > MAX_UPDATE_SIZE - 4:
                return False
            executable.seek(pe_offset)
            return executable.read(4) == b"PE\0\0"
    except OSError:
        return False


def _download_via_windows(url: str, output_path: Path, timeout: float) -> tuple[str, str]:
    """Download with the Windows trust/proxy stack when Python TLS is unavailable."""
    if sys.platform != "win32":
        raise UpdateDownloadError("O fallback HTTPS do Windows não está disponível.")
    escape = lambda value: str(value).replace("'", "''")
    timeout_seconds = max(1, int(round(timeout)))
    script = f"""
$ErrorActionPreference = 'Stop'
[void][Reflection.Assembly]::LoadWithPartialName('System.Net.Http')
$handler = [System.Net.Http.HttpClientHandler]::new()
$handler.AllowAutoRedirect = $true
$client = [System.Net.Http.HttpClient]::new($handler)
$client.Timeout = [TimeSpan]::FromSeconds({timeout_seconds})
$client.DefaultRequestHeaders.UserAgent.ParseAdd('PetronectEmailExtractor')
try {{
    $response = $client.GetAsync('{escape(url)}', [System.Net.Http.HttpCompletionOption]::ResponseHeadersRead).GetAwaiter().GetResult()
    $response.EnsureSuccessStatusCode() | Out-Null
    $inputStream = $response.Content.ReadAsStreamAsync().GetAwaiter().GetResult()
    $outputStream = [System.IO.File]::Create('{escape(output_path)}')
    try {{ $inputStream.CopyTo($outputStream) }} finally {{ $outputStream.Dispose(); $inputStream.Dispose() }}
    [Console]::OutputEncoding = [Text.Encoding]::UTF8
    [Console]::WriteLine($response.RequestMessage.RequestUri.AbsoluteUri)
    [Console]::Write($response.Content.Headers.ContentType.MediaType)
}} finally {{
    if ($null -ne $response) {{ $response.Dispose() }}
    $client.Dispose()
    $handler.Dispose()
}}
"""
    startup_info = subprocess.STARTUPINFO()
    startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    completed = subprocess.run(
        ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout + 5,
        check=True,
        startupinfo=startup_info,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    lines = completed.stdout.splitlines()
    if not lines:
        raise UpdateDownloadError("O fallback do Windows não informou a origem final do download.")
    return lines[0].strip(), lines[1].strip() if len(lines) > 1 else ""


def download_update(
    status: UpdateStatus,
    destination: Path | None = None,
    timeout: float = 30.0,
    on_progress: Callable[[int, int], None] | None = None,
) -> DownloadedUpdate:
    """Download to a partial file, validate it, then atomically expose the EXE."""
    _validate_asset(status)
    base = destination or Path(tempfile.mkdtemp(prefix="PetronectEmailExtractor-update-"))
    base.mkdir(parents=True, exist_ok=True)
    final_path = base / status.asset_name
    partial_path = final_path.with_suffix(final_path.suffix + ".part")
    partial_path.unlink(missing_ok=True)
    request = Request(
        status.asset_url,
        headers={"Accept": "application/octet-stream", "User-Agent": "PetronectEmailExtractor"},
    )
    digest = hashlib.sha256()
    size = 0
    try:
        announced = 0
        try:
            with urlopen(request, timeout=timeout) as response, partial_path.open("xb") as output:
                _validate_final_url(response.geturl())
                content_type = str(response.headers.get("Content-Type", "")).casefold()
                if "text/html" in content_type:
                    raise UpdateDownloadError("O GitHub retornou HTML em vez do executável.")
                announced = int(response.headers.get("Content-Length", 0) or 0)
                if announced > MAX_UPDATE_SIZE:
                    raise UpdateDownloadError("A atualização excede o limite de tamanho permitido.")
                while chunk := response.read(1024 * 256):
                    size += len(chunk)
                    if size > MAX_UPDATE_SIZE:
                        raise UpdateDownloadError("A atualização excede o limite de tamanho permitido.")
                    output.write(chunk)
                    digest.update(chunk)
                    if on_progress:
                        on_progress(size, status.asset_size or announced)
                output.flush()
                os.fsync(output.fileno())
        except UpdateDownloadError:
            raise
        except Exception as python_https_error:
            partial_path.unlink(missing_ok=True)
            try:
                final_url, content_type = _download_via_windows(status.asset_url, partial_path, timeout)
                _validate_final_url(final_url)
                if "text/html" in content_type.casefold():
                    raise UpdateDownloadError("O GitHub retornou HTML em vez do executável.")
                with partial_path.open("rb") as downloaded_file:
                    while chunk := downloaded_file.read(1024 * 256):
                        size += len(chunk)
                        if size > MAX_UPDATE_SIZE:
                            raise UpdateDownloadError("A atualização excede o limite de tamanho permitido.")
                        digest.update(chunk)
                        if on_progress:
                            on_progress(size, status.asset_size)
            except Exception as windows_https_error:
                raise UpdateDownloadError(
                    "Falha no download HTTPS pelo Python e pelo fallback do Windows: "
                    f"{type(python_https_error).__name__}: {python_https_error}; "
                    f"{type(windows_https_error).__name__}: {windows_https_error}"
                ) from windows_https_error
        if status.asset_size and size != status.asset_size:
            raise UpdateDownloadError("O tamanho baixado não corresponde ao asset publicado.")
        if not _is_windows_pe(partial_path):
            raise UpdateDownloadError("O arquivo baixado não é um executável Windows válido.")
        os.replace(partial_path, final_path)
        return DownloadedUpdate(final_path, status.latest_version, digest.hexdigest(), size)
    except Exception:
        partial_path.unlink(missing_ok=True)
        raise


def schedule_executable_replacement(downloaded: DownloadedUpdate, current_executable: Path) -> Path:
    """Start a hidden helper that waits, replaces the closed EXE and restarts it."""
    current_executable = current_executable.resolve()
    if current_executable.suffix.casefold() != ".exe" or not current_executable.exists():
        raise UpdateDownloadError("O executável atual não pôde ser identificado com segurança.")
    if downloaded.path.suffix.casefold() != ".exe" or not downloaded.path.exists():
        raise UpdateDownloadError("O executável baixado não está disponível para instalação.")
    script_path = downloaded.path.parent / "instalar_atualizacao.ps1"
    escape = lambda value: str(value).replace("'", "''")
    script = f"""$ErrorActionPreference = 'Stop'
$processId = {os.getpid()}
$download = '{escape(downloaded.path)}'
$target = '{escape(current_executable)}'
$backup = "$target.anterior"
for ($attempt = 0; $attempt -lt 60; $attempt++) {{
    if (-not (Get-Process -Id $processId -ErrorAction SilentlyContinue)) {{ break }}
    Start-Sleep -Seconds 1
}}
if (Get-Process -Id $processId -ErrorAction SilentlyContinue) {{ exit 2 }}
try {{
    if (Test-Path -LiteralPath $backup) {{ Remove-Item -LiteralPath $backup -Force }}
    Move-Item -LiteralPath $target -Destination $backup
    Move-Item -LiteralPath $download -Destination $target
    Start-Process -FilePath $target
    Remove-Item -LiteralPath $backup -Force
}} catch {{
    if ((-not (Test-Path -LiteralPath $target)) -and (Test-Path -LiteralPath $backup)) {{
        Move-Item -LiteralPath $backup -Destination $target
    }}
    throw
}} finally {{
    Remove-Item -LiteralPath $MyInvocation.MyCommand.Path -Force -ErrorAction SilentlyContinue
}}
"""
    script_path.write_text(script, encoding="utf-8-sig")
    subprocess.Popen(
        [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-WindowStyle",
            "Hidden",
            "-File",
            str(script_path),
        ],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return script_path
