"""Deterministic PT-BR labels and ordering helpers for the interface."""

import unicodedata


MONTH_NAMES_PT_BR = (
    "",
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
)
WEEKDAY_NAMES_SUNDAY_FIRST = ("Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb")


def alphabetical_key(value: str) -> tuple[str, str]:
    """Return a case/accent-insensitive key with a deterministic tie breaker."""
    normalized = unicodedata.normalize("NFKD", str(value).strip().casefold())
    base = "".join(character for character in normalized if not unicodedata.combining(character))
    return base, str(value).casefold()


def unique_sorted(values) -> tuple[str, ...]:
    """Sort visible independent options and remove case-insensitive duplicates."""
    unique: dict[str, str] = {}
    for value in values:
        text = str(value)
        unique.setdefault(text.casefold(), text)
    return tuple(sorted(unique.values(), key=alphabetical_key))
