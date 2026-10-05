import unittest
from datetime import datetime
import tkinter as tk
from unittest.mock import Mock, patch

from email_extractor.ui import (
    CURRENT_CHANGELOG_SUMMARY,
    FOLDER_CACHE_TTL_SECONDS,
    ExtractorWindow,
)
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


class PopupStub:
    def __init__(self, exists=True) -> None:
        self.exists = exists
        self.deiconify = Mock()
        self.lift = Mock()
        self.focus_set = Mock()
        self.grab_release = Mock()
        self.destroy = Mock(side_effect=self._destroy)

    def _destroy(self) -> None:
        self.exists = False

    def winfo_exists(self) -> bool:
        return self.exists


class UiTests(unittest.TestCase):
    def test_about_changelog_summary_covers_current_release_highlights(self) -> None:
        self.assertIn("Microsoft Graph", CURRENT_CHANGELOG_SUMMARY)
        self.assertIn("Outlook clássico", CURRENT_CHANGELOG_SUMMARY)
        self.assertIn("fallback automático", CURRENT_CHANGELOG_SUMMARY)

    def test_calendar_real_window_is_single_instance_and_can_reopen(self) -> None:
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Ambiente sem interface Tk: {exc}")
        root.withdraw()
        try:
            window = object.__new__(ExtractorWindow)
            window.root = root
            window.calendar_popup = None
            window.date_day = tk.StringVar(master=root, value="17")
            window.date_month = tk.StringVar(master=root, value="09")
            window.date_year = tk.StringVar(master=root, value="2026")

            window._show_calendar()
            first = window.calendar_popup
            self.assertIsNotNone(first)
            self.assertTrue(first.winfo_exists())
            self.assertTrue(first.protocol("WM_DELETE_WINDOW"))

            window._show_calendar()
            self.assertIs(window.calendar_popup, first)

            window._close_calendar()
            root.update_idletasks()
            self.assertIsNone(window.calendar_popup)

            window._show_calendar()
            self.assertIsNotNone(window.calendar_popup)
            self.assertIsNot(window.calendar_popup, first)
        finally:
            window._close_calendar()
            root.destroy()

    def test_repeated_calendar_click_recovers_the_single_existing_popup(self) -> None:
        window = object.__new__(ExtractorWindow)
        popup = PopupStub()
        window.calendar_popup = popup

        for _ in range(5):
            self.assertTrue(window._recover_calendar_popup())

        self.assertIs(window.calendar_popup, popup)
        self.assertEqual(popup.deiconify.call_count, 5)
        self.assertEqual(popup.lift.call_count, 5)
        self.assertEqual(popup.focus_set.call_count, 5)

    def test_absent_or_destroyed_calendar_can_be_created_again(self) -> None:
        window = object.__new__(ExtractorWindow)
        window.calendar_popup = None
        self.assertFalse(window._recover_calendar_popup())
        window.calendar_popup = PopupStub(exists=False)
        self.assertFalse(window._recover_calendar_popup())
        self.assertIsNone(window.calendar_popup)

    def test_close_calendar_releases_and_destroys_popup_and_clears_reference(self) -> None:
        window = object.__new__(ExtractorWindow)
        popup = PopupStub()
        window.calendar_popup = popup

        window._close_calendar()

        self.assertIsNone(window.calendar_popup)
        popup.grab_release.assert_called_once()
        popup.destroy.assert_called_once()

    def test_unexpected_popup_destruction_clears_reference(self) -> None:
        window = object.__new__(ExtractorWindow)
        popup = PopupStub()
        window.calendar_popup = popup
        event = Mock(widget=popup)

        window._on_calendar_destroy(event)

        self.assertIsNone(window.calendar_popup)

    def test_closing_main_window_closes_calendar_without_orphan(self) -> None:
        window = object.__new__(ExtractorWindow)
        popup = PopupStub()
        window.calendar_popup = popup
        window._close_about = Mock()
        window.root = Mock()

        window._close_application()

        self.assertIsNone(window.calendar_popup)
        popup.destroy.assert_called_once()
        window.root.destroy.assert_called_once()

    def test_calendar_day_style_is_local_and_keeps_global_ttk_theme_untouched(self) -> None:
        button = Mock()
        ExtractorWindow._style_calendar_day(button, "today_selected")
        configured = button.configure.call_args.kwargs
        self.assertEqual(configured["background"], "#0550AE")
        self.assertEqual(configured["foreground"], "#FFFFFF")
        self.assertEqual(configured["highlightbackground"], "#54AEFF")
        self.assertEqual(configured["highlightthickness"], 2)

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

    def test_folder_dropdown_uses_cache_without_network_and_preserves_selection(self) -> None:
        window = object.__new__(ExtractorWindow)
        window.mailbox = TextVariable("petronect, notificacoes")
        window.folder_path = TextVariable(r"\\petronect, notificacoes\Inbox")
        window.folder_display = TextVariable("Inbox")
        window.folder_combo = ComboStub()
        window._folder_options = {}
        window.source_mode = "graph"
        window._start_folder_load = Mock()
        folders = [
            (0, "Inbox", r"\\petronect, notificacoes\Inbox"),
            (1, "Arquivo", r"\\petronect, notificacoes\Inbox\Arquivo"),
        ]
        window._folder_cache = {("graph", "petronect, notificacoes"): (100.0, folders)}

        with patch("email_extractor.ui.monotonic", return_value=101.0):
            window._refresh_inbox_folders()

        self.assertEqual(window.folder_path.get(), r"\\petronect, notificacoes\Inbox")
        self.assertEqual(window.folder_display.get(), "Inbox")
        self.assertEqual(window.folder_combo.values, ["Inbox", "    Arquivo"])
        self.assertEqual(
            window._folder_options["    Arquivo"],
            r"\\petronect, notificacoes\Inbox\Arquivo",
        )
        window._start_folder_load.assert_not_called()

    def test_stale_folder_cache_is_shown_then_refreshed_silently(self) -> None:
        window = object.__new__(ExtractorWindow)
        window.mailbox = TextVariable("Conta")
        window.folder_path = TextVariable("graph://me/inbox")
        window.folder_display = TextVariable("Inbox")
        window.folder_combo = ComboStub()
        window._folder_options = {}
        window.source_mode = "graph"
        window._folder_cache = {
            ("graph", "Conta"): (100.0, [(0, "Inbox", "graph://me/inbox")])
        }
        window._start_folder_load = Mock()

        with patch(
            "email_extractor.ui.monotonic",
            return_value=100.0 + FOLDER_CACHE_TTL_SECONDS,
        ):
            window._refresh_inbox_folders()

        self.assertEqual(window.folder_display.get(), "Inbox")
        window._start_folder_load.assert_called_once_with(
            "graph",
            "Conta",
            selected_path="graph://me/inbox",
            silent=True,
        )

    def test_folder_selection_keeps_graph_identifier_hidden(self) -> None:
        window = object.__new__(ExtractorWindow)
        window.folder_display = TextVariable("    Arquivo")
        window.folder_path = TextVariable("")
        window._folder_options = {
            "Inbox": "graph://Suporte.Petrobras%40emerson.com/inbox-id",
            "    Arquivo": "graph://Suporte.Petrobras%40emerson.com/archive-id",
        }

        window._folder_selected()

        self.assertEqual(window.folder_display.get(), "    Arquivo")
        self.assertEqual(
            window.folder_path.get(),
            "graph://Suporte.Petrobras%40emerson.com/archive-id",
        )

    def test_indicator_uses_requested_source_colors_and_labels(self) -> None:
        window = object.__new__(ExtractorWindow)
        window.source_indicator = TextVariable("")
        window.source_button = Mock()
        window.source_mode = "graph"

        window._update_source_indicator()
        self.assertEqual(window.source_indicator.get(), "● Entra ID")
        self.assertEqual(window.source_button.configure.call_args.kwargs["foreground"], "#168A4A")

        window.source_mode = "classic"
        window._update_source_indicator()
        self.assertEqual(window.source_indicator.get(), "● Classic")
        self.assertEqual(window.source_button.configure.call_args.kwargs["foreground"], "#CF222E")

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
