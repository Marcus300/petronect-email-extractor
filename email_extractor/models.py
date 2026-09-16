from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class SearchCriteria:
    mailbox_name: str
    folder_path: str
    start_at: datetime
    subject: str
    output_path: Path


@dataclass(frozen=True)
class EmailRecord:
    received_at: datetime
    email_id: str
    subject: str
    tipo: str
    mensagem: str
    body: str
    folder: str