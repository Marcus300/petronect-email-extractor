import tempfile
import unittest
from datetime import datetime
from decimal import Decimal
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
            self.assertEqual(export_xlsx([record], output, subject_filter="SALA"), 1)
            workbook = load_workbook(output, read_only=True)
            headers = list(workbook.active.iter_rows(min_row=1, max_row=1, values_only=True))[0]
            workbook.close()
            self.assertEqual(headers, ("Data e hora de recebimento", "Assunto", "ID", "Tipo", "Mensagem"))
            self.assertNotIn("Pasta", headers)

    def test_generic_layout_exports_untreated_body_for_blank_subject(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "emails.xlsx"
            raw_body = "<html>  Corpo original\ncom espaços  </html>"
            record = EmailRecord(
                datetime(2026, 9, 16, 13, 0),
                "7001234567",
                "Outro assunto",
                "valor tratado que não deve ser exportado",
                "mensagem tratada que não deve ser exportada",
                raw_body,
                "Inbox",
            )
            self.assertEqual(export_xlsx([record], output, subject_filter=""), 1)
            workbook = load_workbook(output, read_only=True)
            rows = list(workbook.active.iter_rows(min_row=1, max_row=2, values_only=True))
            workbook.close()
            self.assertEqual(rows[0], ("Data e hora de recebimento", "Assunto", "ID", "Body"))
            self.assertEqual(rows[1][3], raw_body)

    def test_custom_subject_uses_generic_layout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "emails.xlsx"
            record = EmailRecord(
                datetime(2026, 9, 16, 13, 0), "", "Aviso", "tipo", "mensagem", "body", "Inbox"
            )
            export_xlsx([record], output, subject_filter="Aviso")
            workbook = load_workbook(output, read_only=True)
            headers = list(workbook.active.iter_rows(min_row=1, max_row=1, values_only=True))[0]
            workbook.close()
            self.assertEqual(headers, ("Data e hora de recebimento", "Assunto", "ID", "Body"))

    def test_prorrogada_and_sala_have_identical_excel_structure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            sala_output = base / "sala.xlsx"
            prorrogada_output = base / "prorrogada.xlsx"
            sala_record = EmailRecord(
                datetime(2026, 9, 17, 13, 0), "7001234567", "SALA", "Circular", "Mensagem", "", "Inbox"
            )
            prorrogada_record = EmailRecord(
                datetime(2026, 9, 17, 14, 0),
                "7007654321",
                "Oportunidade Prorrogada",
                "Prorrogação de Oportunidade",
                "Nova data final: “22.09.2026, 20:00:00” (Horário de Brasília)",
                "",
                "Inbox",
            )
            export_xlsx([sala_record], sala_output, subject_filter="Sala")
            export_xlsx([prorrogada_record], prorrogada_output, subject_filter="Prorrogada")
            sala_workbook = load_workbook(sala_output)
            prorrogada_workbook = load_workbook(prorrogada_output)
            try:
                sala_sheet = sala_workbook.active
                prorrogada_sheet = prorrogada_workbook.active
                self.assertEqual(sala_sheet.title, prorrogada_sheet.title)
                self.assertEqual(sala_sheet.max_column, prorrogada_sheet.max_column)
                self.assertEqual(sala_sheet.freeze_panes, prorrogada_sheet.freeze_panes)
                self.assertEqual(sala_sheet.auto_filter.ref, prorrogada_sheet.auto_filter.ref)
                self.assertEqual(
                    [cell.value for cell in sala_sheet[1]],
                    [cell.value for cell in prorrogada_sheet[1]],
                )
                self.assertEqual(
                    [sala_sheet.column_dimensions[column].width for column in "ABCDE"],
                    [prorrogada_sheet.column_dimensions[column].width for column in "ABCDE"],
                )
                self.assertEqual(
                    [cell.style_id for row in sala_sheet.iter_rows() for cell in row],
                    [cell.style_id for row in prorrogada_sheet.iter_rows() for cell in row],
                )
                self.assertEqual(
                    [cell.number_format for cell in sala_sheet["A"]],
                    [cell.number_format for cell in prorrogada_sheet["A"]],
                )
                self.assertEqual(
                    [cell.alignment.wrap_text for cell in sala_sheet["E"]],
                    [cell.alignment.wrap_text for cell in prorrogada_sheet["E"]],
                )
            finally:
                sala_workbook.close()
                prorrogada_workbook.close()

    def test_cancelada_and_sala_have_identical_excel_structure_and_zero_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            sala_output = base / "sala.xlsx"
            cancelada_output = base / "cancelada.xlsx"
            sala_record = EmailRecord(
                datetime(2026, 9, 17, 13, 0), "7001234567", "SALA", "Circular", "Mensagem", "", "Inbox"
            )
            cancelada_record = EmailRecord(
                datetime(2026, 9, 17, 14, 0),
                "7007654321",
                "Oportunidade Cancelada",
                "Oportunidade Cancelada",
                "foi cancelada pelo seguinte motivo:\n\n0",
                "",
                "Inbox",
            )
            export_xlsx([sala_record], sala_output, subject_filter="Sala")
            export_xlsx([cancelada_record], cancelada_output, subject_filter="Cancelada")
            sala_workbook = load_workbook(sala_output)
            cancelada_workbook = load_workbook(cancelada_output)
            try:
                sala_sheet = sala_workbook.active
                cancelada_sheet = cancelada_workbook.active
                self.assertEqual(
                    (
                        sala_sheet.title,
                        sala_sheet.max_column,
                        sala_sheet.freeze_panes,
                        sala_sheet.auto_filter.ref,
                        [cell.value for cell in sala_sheet[1]],
                        [sala_sheet.column_dimensions[column].width for column in "ABCDE"],
                        [cell.style_id for row in sala_sheet.iter_rows() for cell in row],
                    ),
                    (
                        cancelada_sheet.title,
                        cancelada_sheet.max_column,
                        cancelada_sheet.freeze_panes,
                        cancelada_sheet.auto_filter.ref,
                        [cell.value for cell in cancelada_sheet[1]],
                        [cancelada_sheet.column_dimensions[column].width for column in "ABCDE"],
                        [cell.style_id for row in cancelada_sheet.iter_rows() for cell in row],
                    ),
                )
                self.assertEqual(
                    cancelada_sheet["E2"].value,
                    "foi cancelada pelo seguinte motivo:\n\n0",
                )
            finally:
                sala_workbook.close()
                cancelada_workbook.close()

    def test_combined_filter_exports_all_three_categories_in_one_structured_workbook(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "conjunto.xlsx"
            records = [
                EmailRecord(datetime(2026, 9, 17, 10, 0), "7000000001", "SALA", "Sala", "Mensagem Sala", "", "Inbox"),
                EmailRecord(datetime(2026, 9, 17, 10, 1), "7000000002", "Prorrogada", "Prorrogação de Oportunidade", "Nova data final", "", "Inbox"),
                EmailRecord(datetime(2026, 9, 17, 10, 2), "7000000003", "Cancelada", "Oportunidade Cancelada", "foi cancelada pelo seguinte motivo:\n\n0", "", "Inbox"),
            ]
            count = export_xlsx(
                records,
                output,
                subject_filter="0.Conjunto (Sala, Prorrogação, Cancelamento)",
            )
            workbook = load_workbook(output)
            try:
                sheet = workbook.active
                self.assertEqual(count, 3)
                self.assertEqual(
                    tuple(cell.value for cell in sheet[1]),
                    ("Data e hora de recebimento", "Assunto", "ID", "Tipo", "Mensagem"),
                )
                self.assertEqual(sheet.max_row, 4)
                self.assertEqual(
                    [sheet.cell(row=row, column=4).value for row in range(2, 5)],
                    ["Sala", "Prorrogação de Oportunidade", "Oportunidade Cancelada"],
                )
            finally:
                workbook.close()

    def test_purchase_order_uses_dedicated_ten_column_layout_and_numeric_value(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "pedidos.xlsx"
            record = EmailRecord(
                datetime(2026, 9, 17, 11, 30),
                "7001234567",
                "Novo PEDIDO 4515588132",
                "",
                "",
                "Body original",
                "Inbox",
                pedido="4515588132",
                contrato="4600676634",
                cliente="RECAP",
                status="Novo",
                versao="1",
                valor_total=Decimal("1238748.44"),
                moeda="BRL",
            )
            self.assertEqual(export_xlsx([record], output, subject_filter="Pedido"), 1)
            workbook = load_workbook(output, data_only=True)
            try:
                sheet = workbook.active
                self.assertEqual(
                    tuple(cell.value for cell in sheet[1]),
                    (
                        "Data e hora de recebimento",
                        "Assunto",
                        "Pedido",
                        "Contrato",
                        "ID",
                        "Cliente",
                        "Status",
                        "Versão",
                        "Valor Total",
                        "Moeda",
                    ),
                )
                self.assertEqual(sheet.max_column, 10)
                self.assertEqual(sheet.freeze_panes, "A2")
                self.assertEqual(sheet.auto_filter.ref, "A1:J2")
                self.assertEqual(sheet["C2"].value, "4515588132")
                self.assertEqual(sheet["D2"].value, "4600676634")
                self.assertEqual(sheet["C2"].number_format, "@")
                self.assertEqual(sheet["D2"].number_format, "@")
                self.assertAlmostEqual(sheet["I2"].value, 1238748.44, places=2)
                self.assertEqual(sheet["I2"].number_format, "#,##0.00")
            finally:
                workbook.close()

    def test_purchase_order_layout_does_not_change_existing_layouts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            record = EmailRecord(
                datetime(2026, 9, 17, 13, 0), "7001234567", "SALA", "Circular", "Mensagem", "", "Inbox"
            )
            for subject_filter in ("Sala", "Prorrogada", "Cancelada"):
                output = Path(directory) / f"{subject_filter}.xlsx"
                export_xlsx([record], output, subject_filter=subject_filter)
                workbook = load_workbook(output, read_only=True)
                try:
                    self.assertEqual(
                        tuple(cell.value for cell in workbook.active[1]),
                        ("Data e hora de recebimento", "Assunto", "ID", "Tipo", "Mensagem"),
                    )
                finally:
                    workbook.close()


if __name__ == "__main__":
    unittest.main()
