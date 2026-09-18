import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from email_extractor.update_checker import UpdateStatus
from email_extractor.updater import (
    DownloadedUpdate,
    UpdateDownloadError,
    download_update,
    schedule_executable_replacement,
)


class ResponseStub(io.BytesIO):
    def __init__(self, content: bytes, url: str, content_type: str = "application/octet-stream"):
        super().__init__(content)
        self._url = url
        self.headers = {"Content-Type": content_type, "Content-Length": str(len(content))}

    def geturl(self) -> str:
        return self._url


def status(size: int) -> UpdateStatus:
    return UpdateStatus(
        True,
        "0.0.1.1",
        "0.0.1.2",
        "https://github.com/marcus300/petronect-email-extractor/releases/tag/v0.0.1.2",
        "github_api",
        "Petronect.Email.Extractor.v0.0.1.2.exe",
        "https://github.com/marcus300/petronect-email-extractor/releases/download/"
        "v0.0.1.2/Petronect.Email.Extractor.v0.0.1.2.exe",
        size,
    )


def executable_content() -> bytes:
    content = bytearray(256)
    content[:2] = b"MZ"
    content[0x3C:0x40] = (128).to_bytes(4, "little")
    content[128:132] = b"PE\0\0"
    return bytes(content)


class UpdaterTests(unittest.TestCase):
    @patch("email_extractor.updater.subprocess.Popen")
    def test_restart_resets_pyinstaller_environment_and_retries_locked_executable(self, popen) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            current = base / "Petronect Email Extractor v0.0.2.1.exe"
            downloaded_path = base / "download" / current.name
            downloaded_path.parent.mkdir()
            current.write_bytes(executable_content())
            downloaded_path.write_bytes(executable_content())
            downloaded = DownloadedUpdate(downloaded_path, "0.0.2.1", "hash", 256)

            script_path = schedule_executable_replacement(downloaded, current)
            script = script_path.read_text(encoding="utf-8-sig")

            self.assertIn("$env:PYINSTALLER_RESET_ENVIRONMENT = '1'", script)
            self.assertIn("for ($attempt = 0; $attempt -lt 60; $attempt++)", script)
            self.assertLess(
                script.index("$env:PYINSTALLER_RESET_ENVIRONMENT = '1'"),
                script.index("Start-Process -FilePath $target"),
            )
            popen.assert_called_once()

    @patch("email_extractor.updater.urlopen")
    def test_download_is_validated_and_atomically_exposed(self, urlopen) -> None:
        content = executable_content()
        urlopen.return_value = ResponseStub(
            content,
            "https://release-assets.githubusercontent.com/github-production-release-asset/test",
        )
        with tempfile.TemporaryDirectory() as directory:
            result = download_update(status(len(content)), Path(directory))
            self.assertEqual(result.path.read_bytes(), content)
            self.assertEqual(result.size, len(content))
            self.assertFalse(result.path.with_suffix(".exe.part").exists())

    @patch("email_extractor.updater.urlopen")
    def test_html_is_rejected_without_exposing_partial_file(self, urlopen) -> None:
        content = b"<html>failure</html>"
        urlopen.return_value = ResponseStub(content, "https://github.com/error", "text/html")
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(UpdateDownloadError):
                download_update(status(len(content)), Path(directory))
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_unofficial_asset_url_is_rejected(self) -> None:
        unsafe = status(10).__class__(
            True, "0.0.1.1", "0.0.1.2", "", "github_api",
            "Petronect.Email.Extractor.v0.0.1.2.exe", "https://example.com/update.exe", 10,
        )
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(UpdateDownloadError):
                download_update(unsafe, Path(directory))

    @patch("email_extractor.updater.urlopen")
    def test_size_mismatch_removes_partial_download(self, urlopen) -> None:
        content = b"MZsmall"
        urlopen.return_value = ResponseStub(content, "https://github.com/file")
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(UpdateDownloadError):
                download_update(status(len(content) + 1), Path(directory))
            self.assertEqual(list(Path(directory).iterdir()), [])

    @patch("email_extractor.updater._download_via_windows")
    @patch("email_extractor.updater.urlopen", side_effect=OSError("certificado Python indisponível"))
    def test_windows_https_fallback_is_used(self, _urlopen, windows_download) -> None:
        content = executable_content()

        def write_download(_url, output_path, _timeout):
            output_path.write_bytes(content)
            return (
                "https://release-assets.githubusercontent.com/github-production-release-asset/test",
                "application/octet-stream",
            )

        windows_download.side_effect = write_download
        with tempfile.TemporaryDirectory() as directory:
            result = download_update(status(len(content)), Path(directory))
            self.assertEqual(result.size, len(content))
            self.assertEqual(result.path.read_bytes(), content)


if __name__ == "__main__":
    unittest.main()
