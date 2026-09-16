from pathlib import Path
from collections.abc import Callable, Iterable
import os
import tempfile

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font

from .models import EmailRecord


def export_xlsx(
    records: Iterable[EmailRecord],
    output_path: Path,
    on_progress: Callable[[str], None] | None = None,
) -> int:
    """Write extraction results to a readable Excel workbook."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Emails"
    headers = ["Data e hora de recebimento", "Assunto", "ID", "Tipo", "Menssagem"]
    sheet.append(headers)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    count = 0
    for record in records:
        sheet.append([record.received_at, record.subject, record.email_id, record.tipo, record.mensagem])
        count += 1
        if on_progress and count % 25 == 0:
            on_progress(f"{count} email(ns) encontrado(s); preparando Excel")
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    sheet.column_dimensions["A"].width = 25
    sheet.column_dimensions["B"].width = 45
    sheet.column_dimensions["C"].width = 14
    sheet.column_dimensions["D"].width = 45
    sheet.column_dimensions["E"].width = 90
    for cell in sheet["A"][1:]:
        cell.number_format = "dd/mm/yyyy hh:mm:ss"
    for cell in sheet["E"][1:]:
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
