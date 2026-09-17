from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .localization import unique_sorted


SUBJECT_FILTERS: dict[str, tuple[str, ...]] = {
    "0.Conjunto (Sala, Prorrogação, Cancelamento)": ("sala", "prorrogada", "cancelada"),
    "Sala": ("sala",),
    "Nova Oportunidade": ("Criação de Oportunidade", "Oportunidade Publicada"),
    "Chamado": ("Atenção ao Chamado", "ticket", "chamado"),
    "Cancelada": ("Cancelada",),
    "Prorrogada": ("Prorrogada",),
    "Pedido": ("PEDIDO", "ORDER"),
    "Relatório": ("Relatório Divulgado",),
}
SUBJECT_OPTIONS = unique_sorted(SUBJECT_FILTERS)
ROOM_SUBJECT = "Sala"
EXTENDED_OPPORTUNITY_SUBJECT = "Prorrogada"
CANCELLED_OPPORTUNITY_SUBJECT = "Cancelada"
COMBINED_SUBJECT = "0.Conjunto (Sala, Prorrogação, Cancelamento)"
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


def uses_extended_opportunity_layout(subject_filter: str) -> bool:
    """Identify the explicit Prorrogada option without inspecting the body."""
    return subject_filter.strip().casefold() == EXTENDED_OPPORTUNITY_SUBJECT.casefold()


def uses_cancelled_opportunity_layout(subject_filter: str) -> bool:
    """Identify the explicit Cancelada option without inspecting the body."""
    return subject_filter.strip().casefold() == CANCELLED_OPPORTUNITY_SUBJECT.casefold()


def uses_combined_layout(subject_filter: str) -> bool:
    """Identify the combined Sala/Prorrogada/Cancelada option."""
    return subject_filter.strip().casefold() == COMBINED_SUBJECT.casefold()


def structured_subject_category(subject: str, subject_filter: str) -> str:
    """Choose the parser for a structured filter and the message's actual Subject."""
    if uses_cancelled_opportunity_layout(subject_filter):
        return "cancelada"
    if uses_extended_opportunity_layout(subject_filter):
        return "prorrogada"
    if uses_room_layout(subject_filter):
        return "sala"
    if not uses_combined_layout(subject_filter):
        return ""
    normalized_subject = (subject or "").casefold()
    # Check the more specific opportunity states before the generic word "sala".
    if "cancelada" in normalized_subject:
        return "cancelada"
    if "prorrogada" in normalized_subject:
        return "prorrogada"
    if "sala" in normalized_subject:
        return "sala"
    return ""


def uses_structured_layout(subject_filter: str) -> bool:
    """Return whether the filter exports Tipo and Mensagem in the standard layout."""
    return (
        uses_room_layout(subject_filter)
        or uses_extended_opportunity_layout(subject_filter)
        or uses_cancelled_opportunity_layout(subject_filter)
        or uses_combined_layout(subject_filter)
    )


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
