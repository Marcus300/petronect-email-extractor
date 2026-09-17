from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


SUBJECT_FILTERS: dict[str, tuple[str, ...]] = {
    "Sala": ("sala",),
    "Nova Oportunidade": ("Criação de Oportunidade", "Oportunidade Publicada"),
    "Chamado": ("Atenção ao Chamado", "ticket", "chamado"),
    "Cancelada": ("Oportunidade Cancelada",),
    "Prorrogada": ("Oportunidade Prorrogada",),
    "Pedido": ("PEDIDO", "ORDER"),
    "Relatório": ("Relatório Divulgado",),
}
SUBJECT_OPTIONS = tuple(SUBJECT_FILTERS)
ROOM_SUBJECT = "Sala"
ALLOWED_SENDERS = frozenset(
    {
        "ordersender-prod@ansmtp.ariba.com",
        "petronect@petronect.com.br",
    }
)


def subject_terms(subject_filter: str) -> tuple[str, ...]:
    """Resolve a visible option to its hidden search terms, preserving free text."""
    selected = subject_filter.strip()
    if not selected:
        return ()
    for label, terms in SUBJECT_FILTERS.items():
        if selected.casefold() == label.casefold():
            return terms
    return (selected,)


def subject_matches(subject: str, subject_filter: str) -> bool:
    terms = subject_terms(subject_filter)
    normalized_subject = subject.casefold()
    return not terms or any(term.casefold() in normalized_subject for term in terms)


def sender_is_allowed(sender_email: str) -> bool:
    return sender_email.strip().casefold() in ALLOWED_SENDERS


def uses_room_layout(subject_filter: str) -> bool:
    """Use the Petronect room parser only for the explicit Sala option."""
    return subject_filter.strip().casefold() == ROOM_SUBJECT.casefold()


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
