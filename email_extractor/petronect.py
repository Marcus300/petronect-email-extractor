from dataclasses import dataclass
from datetime import datetime
import re
from html import unescape


@dataclass(frozen=True)
class PetronectResult:
    tipo: str
    mensagem: str
    warnings: tuple[str, ...] = ()
    used_fallback: bool = False


_NOTIFICATION_PATTERN = re.compile(
    r"Informamos\s+que\s+existe\s+uma\s+nova\s+mensagem"
    r"(?:\s*\(COM\s+ANEXOS\))?\s+para\s+o\s+assunto\s+"
    r"[\"“](?P<tipo>.*?)[\"”]\s+na\s+sala\s+de\s+colaboração",
    re.IGNORECASE | re.DOTALL,
)
_BR_PATTERN = re.compile(r"<\s*br\s*/?\s*>", re.IGNORECASE)
_TAG_PATTERN = re.compile(r"<[^>]+>")
_INVISIBLE_PATTERN = re.compile(r"[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f\u200b\ufeff]")
_HORIZONTAL_SPACE_PATTERN = re.compile(r"[ \t\xa0]+")
_AUTOMATIC_FOOTER_PATTERN = re.compile(
    r"\n?\s*Atenciosamente,?\s*\n\s*Serviço\s+de\s+Notificação\s+Petronect\.?\s*$",
    re.IGNORECASE,
)
_ACCESS_MARKER_PATTERN = re.compile(r"Para\s+acessar\s+a\s+oportunidade", re.IGNORECASE)
_SECURITY_BANNER_END = "ZjQcmQRYFpfptBannerEnd"
_EXTENDED_OPPORTUNITY_TYPE = "Prorrogação de Oportunidade"
_CANCELLED_OPPORTUNITY_TYPE = "Oportunidade Cancelada"
_CANCELLATION_MESSAGE_PREFIX = "foi cancelada pelo seguinte motivo:"
_EXTENDED_OPPORTUNITY_PATTERN = re.compile(
    r"Nova\s+data\s+final:\s*[“\"]\s*"
    r"(?P<date>\d{2}\.\d{2}\.\d{4})\s*,\s*"
    r"(?P<time>\d{2}:\d{2}:\d{2})\s*[”\"]\s*"
    r"\(Horário\s+de\s+Brasília\)",
    re.IGNORECASE,
)
_CANCELLATION_START_PATTERN = re.compile(
    r"foi\s+cancelada\s+pelo\s+seguinte\s+motivo\s*:", re.IGNORECASE
)
_CANCELLATION_END_PATTERN = re.compile(
    r"Essa\s+é\s+uma\s+notificação\s+automática\s+do\s+sistema\s*,?\s*"
    r"favor\s+não\s+respondê-la\s*\.?",
    re.IGNORECASE,
)
_SAFE_CANCELLATION_FOOTER_PATTERN = re.compile(
    r"(?im)^\s*(?:Requisitos?\b|Dúvidas\s+Frequentes\b|Ajuda\s*$|"
    r"Canais?\s+de\s+Atendimento\b|Atenciosamente\b|"
    r"Serviço\s+de\s+Notificação\s+Petronect\b)",
)


def normalize_body(body: str) -> str:
    """Normalize transport/HTML noise while preserving meaningful line breaks."""
    text = unescape(body or "")
    text = _BR_PATTERN.sub("\n", text)
    text = _TAG_PATTERN.sub("", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _INVISIBLE_PATTERN.sub("", text).replace("\xa0", " ")
    lines = [_HORIZONTAL_SPACE_PATTERN.sub(" ", line).strip() for line in text.split("\n")]
    return "\n".join(lines)


def extrair_tipo_mensagem(body: str) -> PetronectResult:
    """Extract Petronect notification fields using structural delimiters only."""
    text = normalize_body(body)
    marker = _SECURITY_BANNER_END
    marker_position = text.casefold().find(marker.casefold())
    preferred_text = text[marker_position + len(marker):] if marker_position >= 0 else text
    matches = list(_NOTIFICATION_PATTERN.finditer(preferred_text))
    if not matches and marker_position >= 0:
        matches = list(_NOTIFICATION_PATTERN.finditer(text))
    warnings: list[str] = []
    if not matches:
        return PetronectResult("", "", ("TIPO Petronect não identificado",))

    notification = matches[-1]
    tipo = notification.group("tipo").strip()
    suffix = preferred_text[notification.end():]
    line_break = suffix.find("\n")
    candidate = suffix[line_break + 1:] if line_break >= 0 else suffix
    candidate = candidate.lstrip(" .:\t\r\n")
    access_match = _ACCESS_MARKER_PATTERN.search(candidate)
    if access_match:
        candidate = candidate[:access_match.start()]
    else:
        warnings.append("marcador 'Para acessar a oportunidade' não identificado")
    candidate = _AUTOMATIC_FOOTER_PATTERN.sub("", candidate)
    mensagem = _remove_outer_quotes(candidate)
    mensagem = _trim_outer_blank_lines(mensagem)
    return PetronectResult(tipo, mensagem, tuple(warnings))


def extrair_tipo_mensagem_prorrogada(subject: str, body: str) -> PetronectResult:
    """Extract the final extended deadline from a Prorrogada notification."""
    if "prorrogada" not in (subject or "").casefold():
        return PetronectResult("", "", ("Subject não classificado como Prorrogada",))

    text = normalize_body(body)
    marker_position = text.casefold().find(_SECURITY_BANNER_END.casefold())
    used_fallback = marker_position < 0
    search_text = (
        text[marker_position + len(_SECURITY_BANNER_END):]
        if marker_position >= 0
        else text
    )
    valid_values: list[tuple[str, str]] = []
    for match in _EXTENDED_OPPORTUNITY_PATTERN.finditer(search_text):
        date_value = match.group("date")
        time_value = match.group("time")
        try:
            datetime.strptime(f"{date_value} {time_value}", "%d.%m.%Y %H:%M:%S")
        except ValueError:
            continue
        valid_values.append((date_value, time_value))

    warnings: list[str] = []
    if used_fallback:
        warnings.append("Prorrogada: marcador de banner ausente; fallback aplicado ao Body completo")
    if not valid_values:
        warnings.append("Prorrogada: 'Nova data final' completa e válida não identificada")
        return PetronectResult(_EXTENDED_OPPORTUNITY_TYPE, "", tuple(warnings), used_fallback)

    distinct_values = list(dict.fromkeys(valid_values))
    if len(distinct_values) > 1:
        warnings.append(
            "Prorrogada: múltiplas novas datas finais diferentes; última ocorrência válida utilizada"
        )
    date_value, time_value = valid_values[-1]
    mensagem = (
        f"Nova data final: “{date_value}, {time_value}” "
        "(Horário de Brasília)"
    )
    return PetronectResult(
        _EXTENDED_OPPORTUNITY_TYPE,
        mensagem,
        tuple(warnings),
        used_fallback,
    )


def extrair_tipo_mensagem_cancelada(subject: str, body: str) -> PetronectResult:
    """Extract the cancellation reason from the authoritative notification body."""
    if "cancelada" not in (subject or "").casefold():
        return PetronectResult("", "", ("Subject não classificado como Cancelada",))

    text = normalize_body(body)
    marker_position = text.casefold().find(_SECURITY_BANNER_END.casefold())
    used_fallback = marker_position < 0
    search_text = (
        text[marker_position + len(_SECURITY_BANNER_END):]
        if marker_position >= 0
        else text
    )
    starts = list(_CANCELLATION_START_PATTERN.finditer(search_text))
    warnings: list[str] = []
    if used_fallback:
        warnings.append("Cancelada: marcador de banner ausente; fallback aplicado ao Body completo")
    if not starts:
        warnings.append("Cancelada: delimitador inicial do motivo não identificado")
        return PetronectResult(_CANCELLED_OPPORTUNITY_TYPE, "", tuple(warnings), used_fallback)

    candidates: list[str] = []
    for start in starts:
        remainder = search_text[start.end():]
        end = _CANCELLATION_END_PATTERN.search(remainder)
        reason = remainder[:end.start()] if end else remainder
        if end is None:
            safe_footer = _SAFE_CANCELLATION_FOOTER_PATTERN.search(reason)
            if safe_footer:
                reason = reason[:safe_footer.start()]
        candidates.append(_normalize_cancellation_reason(reason))

    if len(dict.fromkeys(candidates)) > 1:
        warnings.append(
            "Cancelada: múltiplos motivos diferentes; última ocorrência válida utilizada"
        )
    reason = candidates[-1]
    if not reason:
        warnings.append("motivo_cancelamento_vazio")
        message = _CANCELLATION_MESSAGE_PREFIX
    else:
        message = f"{_CANCELLATION_MESSAGE_PREFIX}\n\n{reason}"
    return PetronectResult(
        _CANCELLED_OPPORTUNITY_TYPE,
        message,
        tuple(warnings),
        used_fallback,
    )


def _normalize_cancellation_reason(reason: str) -> str:
    """Remove transport-only edges while preserving authored paragraphs and content."""
    lines = [line.strip() for line in reason.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    normalized: list[str] = []
    previous_blank = False
    for line in lines:
        blank = not line
        if blank and previous_blank:
            continue
        normalized.append(line)
        previous_blank = blank
    return "\n".join(normalized)


def _remove_outer_quotes(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^\"+", "", text)
    text = re.sub(r"\"+$", "", text)
    return text


def _trim_outer_blank_lines(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.strip().split("\n")).strip()
