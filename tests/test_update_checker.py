import io
import unittest
from unittest.mock import patch

from email_extractor.update_checker import UpdateStatus, check_for_updates


class UpdateCheckerTests(unittest.TestCase):
    def test_version_comparison_is_numeric(self) -> None:
        self.assertTrue(UpdateStatus(True, "0.0.1.0", "0.0.2.0").update_available)
        self.assertFalse(UpdateStatus(True, "0.0.2.0", "0.0.1.0").update_available)
        self.assertFalse(UpdateStatus(True, "0.0.1.0", "0.0.1.0").update_available)

    @patch("email_extractor.update_checker.urlopen")
    def test_checker_reads_latest_github_release(self, urlopen) -> None:
        response = io.BytesIO(b'{"tag_name":"v0.0.2.0","html_url":"https://example.test/release"}')
        urlopen.return_value = response
        status = check_for_updates("0.0.1.0")
        self.assertTrue(status.enabled)
        self.assertTrue(status.update_available)
        self.assertEqual(status.latest_version, "0.0.2.0")


if __name__ == "__main__":
    unittest.main()
