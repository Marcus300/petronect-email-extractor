from pathlib import Path
from collections.abc import Callable, Iterable
import os
import tempfile

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font

from .models import EmailRecord, uses_purchase_order_layout, uses_structured_layout


def export_xlsx(
    records: Iterable[EmailRecord],
    output_path: Path,
    on_progress: Callable[[str], None] | None = None,
    subject_filter: str = "",
) -> int:
    """Write extraction results to a readable Excel workbook."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Emails"
    purchase_order_layout = uses_purchase_order_layout(subject_filter)
    structured_layout = uses_structured_layout(subject_filter)
    if purchase_order_layout:
        headers = [
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
        ]
    elif structured_layout:
        headers = ["Data e hora de recebimento", "Assunto", "ID", "Tipo", "Mensagem"]
    else:
        headers = ["Data e hora de recebimento", "Assunto", "ID", "Body"]
    sheet.append(headers)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    count = 0
    for record in records:
        if purchase_order_layout:
            row = [
                record.received_at,
                record.subject,
                record.pedido,
                record.contrato,
                record.email_id,
                record.cliente,
                record.status,
                record.versao,
                record.valor_total,
                record.moeda,
            ]
        elif structured_layout:
            row = [record.received_at, record.subject, record.email_id, record.tipo, record.mensagem]
        else:
            row = [record.received_at, record.subject, record.email_id, record.body]
        sheet.append(row)
        count += 1
        if on_progress and count % 25 == 0:
            on_progress(f"{count} email(s) encontrado(s); preparando Excel")
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    sheet.column_dimensions["A"].width = 25
    sheet.column_dimensions["B"].width = 45
    if purchase_order_layout:
        purchase_widths = {
            "C": 16, "D": 16, "E": 14, "F": 28, "G": 24,
            "H": 10, "I": 18, "J": 10,
        }
        for column, width in purchase_widths.items():
            sheet.column_dimensions[column].width = width
        for column in ("C", "D"):
            for cell in sheet[column][1:]:
                cell.number_format = "@"
        for cell in sheet["I"][1:]:
            cell.number_format = "#,##0.00"
    else:
        sheet.column_dimensions["C"].width = 14
        sheet.column_dimensions["D"].width = 45 if structured_layout else 100
        if structured_layout:
            sheet.column_dimensions["E"].width = 90
    for cell in sheet["A"][1:]:
        cell.number_format = "dd/mm/yyyy hh:mm:ss"
    if purchase_order_layout:
        for column in ("B", "F", "G"):
            for cell in sheet[column][1:]:
                cell.alignment = Alignment(wrap_text=True, vertical="top")
    else:
        content_column = "E" if structured_layout else "D"
        for cell in sheet[content_column][1:]:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    # Save beside the destination and replace only after a complete workbook is
    # produced. This avoids leaving a corrupt final file after an interrupted save.
    temporary_name = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{output_path.stem}_", suffix=".xlsx", dir=output_path.parent, delete=False
        ) as temporary:
            temporary_name = temporary.name
        workbook.save(temporary_name)
        os.replace(temporary_name, output_path)
    finally:
        workbook.close()
        if temporary_name:
            Path(temporary_name).unlink(missing_ok=True)
    return count
