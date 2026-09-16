import unittest

from email_extractor.diagnostics import format_exception, runtime_metadata


class DiagnosticsTests(unittest.TestCase):
    def test_runtime_metadata_contains_portability_fields(self) -> None:
        metadata = "\n".join(runtime_metadata())
        self.assertIn("app_executable=", metadata)
        self.assertIn("working_directory=", metadata)
        self.assertIn("platform=", metadata)

    def test_format_exception_includes_cause_and_traceback(self) -> None:
        try:
            try:
                raise ValueError("origem")
            except ValueError as cause:
                raise RuntimeError("falha") from cause
        except RuntimeError as exc:
            result = format_exception(exc)
        self.assertIn("ValueError: origem", result)
        self.assertIn("RuntimeError: falha", result)


if __name__ == "__main__":
    unittest.main()
