from dataclasses import dataclass
import re
from html import unescape


@dataclass(frozen=True)
class PetronectResult:
    tipo: str
    mensagem: str
    warnings: tuple[str, ...] = ()


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
    marker = "ZjQcmQRYFpfptBannerEnd"
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


def _remove_outer_quotes(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^\"+", "", text)
    text = re.sub(r"\"+$", "", text)
    return text


def _trim_outer_blank_lines(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.strip().split("\n")).strip()