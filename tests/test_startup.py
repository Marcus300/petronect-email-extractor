import threading
import unittest
from queue import Queue
from unittest.mock import Mock, patch

from email_extractor.ui import ExtractorWindow


class StartupTests(unittest.TestCase):
    def test_constructor_schedules_worker_without_starting_it_synchronously(self) -> None:
        root = Mock()
        root.after_idle = Mock(return_value="idle")
        root.after = Mock(side_effect=["start", "poll"])
        with (
            patch("email_extractor.ui.tk.StringVar", side_effect=lambda value="": Mock(get=Mock(return_value=value))),
            patch.object(
                ExtractorWindow,
                "_build",
                lambda window: setattr(window, "main_frame", Mock()),
            ),
            patch.object(ExtractorWindow, "_build_loading_screen"),
            patch.object(ExtractorWindow, "_set_window_icon"),
            patch.object(ExtractorWindow, "_start_initialization") as start,
            patch("email_extractor.ui.StartupLogger") as logger_type,
        ):
            window = ExtractorWindow(root)

        self.assertIsNone(window.startup_worker)
        start.assert_not_called()
        root.after.assert_any_call(50, start)

    @patch("email_extractor.outlook.OutlookEmailSource")
    @patch("pythoncom.CoUninitialize")
    @patch("pythoncom.CoInitialize")
    def test_worker_uses_one_com_connection_and_returns_only_plain_data(
        self, co_initialize, co_uninitialize, source_type
    ) -> None:
        source = source_type.return_value
        source.list_mailboxes.return_value = ["Caixa"]
        source.list_inbox_folders.return_value = [(0, "Inbox", r"\\Caixa\Inbox")]
        window = object.__new__(ExtractorWindow)
        window.startup_queue = Queue()
        window.startup_stop_event = threading.Event()
        window.startup_logger = Mock()

        worker_thread = threading.Thread(target=window._initialization_worker)
        worker_thread.start()
        worker_thread.join(3)

        self.assertFalse(worker_thread.is_alive())
        co_initialize.assert_called_once()
        co_uninitialize.assert_called_once()
        source_type.assert_called_once()
        source.list_mailboxes.assert_called_once()
        source.list_inbox_folders.assert_called_once_with("Caixa", max_depth=2)
        events = list(window.startup_queue.queue)
        result = next(value for event, value in events if event == "result")
        self.assertEqual(result, (["Caixa"], [(0, "Inbox", r"\\Caixa\Inbox")]))
        self.assertTrue(all(isinstance(event, str) for event, _value in events))

    def test_determined_progress_is_clamped_and_monotonic(self) -> None:
        window = object.__new__(ExtractorWindow)
        window.startup_progress = 0
        window.loading_canvas = Mock()
        window.loading_arc = "arc"
        window.loading_percent = "percent"
        window.loading_status = Mock()

        window._set_startup_progress(40, "Outlook conectado")
        window._set_startup_progress(10, "Anterior")
        window._set_startup_progress(150, "Pronto")

        self.assertEqual(window.startup_progress, 100)
        calls = window.loading_canvas.itemconfigure.call_args_list
        self.assertEqual(calls[2].kwargs["extent"], -144.0)
        self.assertEqual(calls[-2].kwargs["extent"], -360.0)

    def test_indeterminate_animation_starts_and_stops_without_worker_thread(self) -> None:
        window = object.__new__(ExtractorWindow)
        window.closing = False
        window.startup_indeterminate = False
        window.startup_angle = 90
        window.startup_animation_id = None
        window.root = Mock()
        window.root.after.return_value = "animation"
        window.loading_canvas = Mock()
        window.loading_arc = "arc"
        window.loading_percent = "percent"
        window.loading_status = Mock()

        window._set_startup_indeterminate("Conectando ao Outlook...")

        self.assertTrue(window.startup_indeterminate)
        self.assertEqual(window.startup_animation_id, "animation")
        window.startup_indeterminate = False
        window._animate_loading_ring()
        self.assertEqual(window.root.after.call_count, 1)

    def test_failure_stops_animation_and_releases_stable_interface(self) -> None:
        window = object.__new__(ExtractorWindow)
        window.closing = False
        window.startup_indeterminate = True
        window.loading_canvas = Mock()
        window.loading_arc = "arc"
        window.loading_percent = "percent"
        window.loading_status = Mock()
        window.loading_detail = Mock()
        window.loading_frame = Mock()
        window.main_frame = Mock()
        window.startup_logger = Mock(path="startup.log")
        window.root = Mock()
        with patch("email_extractor.ui.messagebox.showerror") as showerror:
            window._fail_initialization("detalhes técnicos")

        self.assertFalse(window.startup_indeterminate)
        window.loading_frame.destroy.assert_not_called()
        window.main_frame.pack.assert_called_once_with(fill="both", expand=True)
        window.root.after_idle.assert_called_once_with(window._reveal_after_startup_failure)
        showerror.assert_called_once()

    def test_success_reaches_100_and_reveals_main_interface(self) -> None:
        window = object.__new__(ExtractorWindow)
        window.startup_progress = 95
        window.startup_indeterminate = True
        window.loading_canvas = Mock()
        window.loading_arc = "arc"
        window.loading_percent = "percent"
        window.loading_status = Mock()
        window.loading_frame = Mock()
        window.main_frame = Mock()
        window.mailbox_combo = Mock()
        window.startup_logger = Mock()
        window.root = Mock()
        window._apply_initial_data = Mock()
        window._start_update_check = Mock()

        window._complete_initialization(["Caixa"], [(0, "Inbox", r"\\Caixa\Inbox")])

        self.assertEqual(window.startup_progress, 100)
        self.assertFalse(window.startup_indeterminate)
        window.loading_frame.destroy.assert_not_called()
        window.main_frame.pack.assert_called_once_with(fill="both", expand=True)
        window.mailbox_combo.focus_set.assert_not_called()
        window.root.after_idle.assert_called_once_with(window._reveal_main_interface)

    def test_excel_export_is_imported_lazily(self) -> None:
        import email_extractor.ui as ui

        self.assertFalse(hasattr(ui, "export_xlsx"))


if __name__ == "__main__":
    unittest.main()
