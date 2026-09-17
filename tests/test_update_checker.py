import io
import unittest
from unittest.mock import patch

from email_extractor.update_checker import UpdateCheckError, UpdateStatus, check_for_updates


class UpdateCheckerTests(unittest.TestCase):
    def test_version_comparison_is_numeric(self) -> None:
        self.assertTrue(UpdateStatus(True, "0.0.1.0", "0.0.2.0").update_available)
        self.assertFalse(UpdateStatus(True, "0.0.2.0", "0.0.1.0").update_available)
        self.assertFalse(UpdateStatus(True, "0.0.1.0", "0.0.1.0").update_available)

    @patch("email_extractor.update_checker.urlopen")
    def test_checker_reads_latest_github_release(self, urlopen) -> None:
        response = io.BytesIO(
            b'{"tag_name":"v0.0.2.0","html_url":"https://example.test/release",'
            b'"assets":[{"name":"Petronect.Email.Extractor.v0.0.2.0.exe",'
            b'"browser_download_url":"https://github.com/marcus300/petronect-email-extractor/'
            b'releases/download/v0.0.2.0/Petronect.Email.Extractor.v0.0.2.0.exe",'
            b'"size":1234}]}'
        )
        urlopen.return_value = response
        status = check_for_updates("0.0.1.0")
        self.assertTrue(status.enabled)
        self.assertTrue(status.update_available)
        self.assertEqual(status.latest_version, "0.0.2.0")
        self.assertEqual(status.source, "github_api")
        self.assertEqual(status.asset_name, "Petronect.Email.Extractor.v0.0.2.0.exe")
        self.assertEqual(status.asset_size, 1234)

    @patch(
        "email_extractor.update_checker._latest_release_url_via_windows",
        return_value="https://github.com/marcus300/petronect-email-extractor/releases/tag/v0.0.1.2",
    )
    @patch("email_extractor.update_checker.urlopen", side_effect=OSError("certificado indisponível"))
    def test_checker_falls_back_to_latest_release_link(self, _urlopen, _latest_url) -> None:
        status = check_for_updates("0.0.1.1")
        self.assertTrue(status.update_available)
        self.assertEqual(status.latest_version, "0.0.1.2")
        self.assertEqual(status.source, "github_release_link")
        self.assertEqual(
            status.release_url,
            "https://github.com/marcus300/petronect-email-extractor/releases/tag/v0.0.1.2",
        )
        self.assertEqual(status.asset_name, "Petronect.Email.Extractor.v0.0.1.2.exe")
        self.assertIn("/releases/download/v0.0.1.2/", status.asset_url)

    @patch(
        "email_extractor.update_checker._latest_release_url_via_windows",
        side_effect=OSError("fallback indisponível"),
    )
    @patch("email_extractor.update_checker.urlopen", side_effect=OSError("API indisponível"))
    def test_checker_reports_both_failures(self, _urlopen, _latest_url) -> None:
        with self.assertRaises(UpdateCheckError) as context:
            check_for_updates("0.0.1.1")
        self.assertIn("API indisponível", str(context.exception))
        self.assertIn("fallback indisponível", str(context.exception))


if __name__ == "__main__":
    unittest.main()
