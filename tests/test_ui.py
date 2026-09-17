import unittest
from datetime import datetime
from unittest.mock import Mock, patch

from email_extractor.ui import ExtractorWindow
from email_extractor.models import uses_room_layout


class TextVariable:
    def __init__(self, value: str) -> None:
        self.value = value

    def get(self) -> str:
        return self.value

    def set(self, value: str) -> None:
        self.value = value


class ComboStub:
    def __init__(self) -> None:
        self.values = []
        self.current_index = None

    def __setitem__(self, key, value) -> None:
        if key == "values":
            self.values = value

    def current(self, index: int) -> None:
        self.current_index = index


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

    @patch("email_extractor.ui.OutlookEmailSource")
    def test_folder_dropdown_refreshes_subfolders_and_preserves_selection(self, source_type) -> None:
        window = object.__new__(ExtractorWindow)
        window.mailbox = TextVariable("petronect, notificacoes")
        window.folder_path = TextVariable(r"\\petronect, notificacoes\Inbox")
        window.folder_combo = ComboStub()
        window._folder_options = {}
        window._write_log = lambda _message: None
        source_type.return_value.list_inbox_folders.return_value = [
            (0, "Inbox", r"\\petronect, notificacoes\Inbox"),
            (1, "Arquivo", r"\\petronect, notificacoes\Inbox\Arquivo"),
        ]

        window._refresh_inbox_folders()

        self.assertEqual(window.folder_path.get(), r"\\petronect, notificacoes\Inbox")
        self.assertEqual(window.folder_combo.values, ["Inbox", "    Arquivo"])
        self.assertEqual(
            window._folder_options["    Arquivo"],
            r"\\petronect, notificacoes\Inbox\Arquivo",
        )

    def test_today_returns_to_current_month_year_and_updates_fields(self) -> None:
        window = object.__new__(ExtractorWindow)
        window.date_day = TextVariable("01")
        window.date_month = TextVariable("01")
        window.date_year = TextVariable("2025")
        window._render_calendar = Mock()
        month = [2025, 1]
        selected = [datetime(2025, 1, 1).date()]
        today = datetime(2026, 9, 17).date()

        window._select_today("body", month, "title", selected, today)

        self.assertEqual(month, [2026, 9])
        self.assertEqual(selected[0], today)
        self.assertEqual(
            (window.date_day.get(), window.date_month.get(), window.date_year.get()),
            ("17", "09", "2026"),
        )
        window._render_calendar.assert_called_once()

    def test_future_cutoff_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "não podem ser posteriores"):
            ExtractorWindow._validate_start_not_future(
                datetime(2026, 9, 17, 15, 1),
                datetime(2026, 9, 17, 15, 0),
            )
        ExtractorWindow._validate_start_not_future(
            datetime(2026, 9, 17, 15, 0),
            datetime(2026, 9, 17, 15, 0),
        )

    @patch("email_extractor.ui.messagebox.showerror")
    def test_future_cutoff_does_not_start_search_or_create_log(self, showerror) -> None:
        window = object.__new__(ExtractorWindow)
        window.mailbox = TextVariable("Caixa")
        window.folder_path = TextVariable(r"\\Caixa\Inbox")
        window.output_path = TextVariable(r"C:\Temp\emails.xlsx")
        window.subject = TextVariable("Cancelada")
        window.root = object()
        window._start_datetime = Mock(return_value=datetime(2026, 9, 17, 15, 1))
        window._clear_log = Mock()
        with patch("email_extractor.ui.datetime") as datetime_type:
            datetime_type.now.return_value = datetime(2026, 9, 17, 15, 0)
            window._run()
        window._clear_log.assert_not_called()
        showerror.assert_called_once()


if __name__ == "__main__":
    unittest.main()
