import unittest
from datetime import datetime

from email_extractor.ui import ExtractorWindow
from email_extractor.models import uses_room_layout


class TextVariable:
    def __init__(self, value: str) -> None:
        self.value = value

    def get(self) -> str:
        return self.value


class UiTests(unittest.TestCase):
    def test_date_and_time_segments_accept_partial_numeric_input(self) -> None:
        self.assertTrue(ExtractorWindow._validate_segment("", "2"))
        self.assertTrue(ExtractorWindow._validate_segment("2", "2"))
        self.assertTrue(ExtractorWindow._validate_segment("23", "2"))
        self.assertFalse(ExtractorWindow._validate_segment("234", "2"))
        self.assertFalse(ExtractorWindow._validate_segment("2a", "2"))

    def test_start_datetime_uses_segment_fields(self) -> None:
        window = object.__new__(ExtractorWindow)
        window.date_day = TextVariable("16")
        window.date_month = TextVariable("09")
        window.date_year = TextVariable("2026")
        window.time_hour = TextVariable("01")
        window.time_minute = TextVariable("05")
        self.assertEqual(window._start_datetime(), datetime(2026, 9, 16, 1, 5))

    def test_only_sala_uses_room_layout(self) -> None:
        self.assertTrue(uses_room_layout("SALA"))
        self.assertTrue(uses_room_layout(" sala "))
        self.assertFalse(uses_room_layout(""))
        self.assertFalse(uses_room_layout("[EXTERNAL] SALA"))


if __name__ == "__main__":
    unittest.main()
