import ctypes
from time import perf_counter

from email_extractor.diagnostics import write_emergency_log

PROCESS_STARTED_AT = perf_counter()


if __name__ == "__main__":
    try:
        from email_extractor.ui import start_app

        start_app(PROCESS_STARTED_AT)
    except Exception as exc:
        try:
            log_path = write_emergency_log(exc)
            ctypes.windll.user32.MessageBoxW(
                0,
                f"Não foi possível iniciar o aplicativo.\n\nLog técnico:\n{log_path}",
                "Petronect Email Extractor",
                0x10,
            )
        except Exception:
            raise
