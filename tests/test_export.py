import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from openpyxl import load_workbook

from email_extractor.export import export_xlsx
from email_extractor.models import EmailRecord


class ExportTests(unittest.TestCase):
    def test_excel_contains_subject_and_not_folder(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "emails.xlsx"
            record = EmailRecord(
                datetime(2026, 9, 16, 13, 0),
                "7001234567",
                "[EXTERNAL] SALA",
                "Folha de dados",
                "Boa tarde!",
                "body original",
                "Pedido 7001234567",
            )
            self.assertEqual(export_xlsx([record], output), 1)
            workbook = load_workbook(output, read_only=True)
            headers = list(workbook.active.iter_rows(min_row=1, max_row=1, values_only=True))[0]
            workbook.close()
            self.assertEqual(headers, ("Data e hora de recebimento", "Assunto", "ID", "Tipo", "Menssagem"))
            self.assertNotIn("Pasta", headers)


if __name__ == "__main__":
    unittest.main()