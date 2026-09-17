import unittest
from pathlib import Path
from unittest.mock import patch

from email_extractor.paths import DEFAULT_EXCEL_FILENAME, default_excel_path, downloads_folder


class PathTests(unittest.TestCase):
    @patch("email_extractor.paths.downloads_folder", return_value=Path("C:/Users/Test/Downloads"))
    def test_default_excel_path_uses_downloads_and_expected_filename(self, _downloads) -> None:
        self.assertEqual(
            default_excel_path(),
            Path("C:/Users/Test/Downloads") / DEFAULT_EXCEL_FILENAME,
        )

    @patch("email_extractor.paths.Path.home", return_value=Path("C:/Users/Test"))
    @patch("email_extractor.paths.sys.platform", "linux")
    def test_downloads_folder_has_portable_fallback(self, _home) -> None:
        self.assertEqual(downloads_folder(), Path("C:/Users/Test/Downloads"))


if __name__ == "__main__":
    unittest.main()
