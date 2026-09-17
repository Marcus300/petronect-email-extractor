"""Parser for SAP Business Network / Ariba purchase-order notifications."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import re

from .petronect import normalize_body


_SECURITY_BANNER_END = "ZjQcmQRYFpfptBannerEnd"
_ORDER_NUMBER_PATTERN = re.compile(r"\b45\d{8}\b")
_CONTRACT_NUMBER_PATTERN = re.compile(r"\b46\d{8}\b")
_ORDER_BLOCK_PATTERN = re.compile(r"\bPedido\s+de\s+compra\b", re.IGNORECASE)
_VERSION_PATTERN = re.compile(r"\bVersão\s*:\s*(?P<version>\d+)\b", re.IGNORECASE)
_STATUS_PATTERN = re.compile(
    r"\bPedido\s+de\s+compra\b\s*\((?P<status>.*?)\)",
    re.IGNORECASE | re.DOTALL,
)
_MONEY_PAIR_PATTERN = re.compile(
    r"\bValor\s*:\s*(?:R?\$\s*)?"
    r"(?P<amount>\d{1,3}(?:\.\d{3})*,\d{2})\s*"
    r"(?P<currency>[A-Z]{3})\b",
    re.IGNORECASE,
)
_URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)
_IMAGE_REFERENCE_PATTERN = re.compile(
    r"\b\S+\.(?:gif|png|jpe?g|svg)(?:\?\S*)?\b", re.IGNORECASE
)
_MARKDOWN_PATTERN = re.compile(r"[\[\]!*_`]+")
_EXPLICIT_CONTRACT_PATTERN = re.compile(
    r"(?i)\bcontrato(?:\s+n[º°o.]?|\s*:)\s*(46\d{8})\b"
)


@dataclass(frozen=True)
class PurchaseOrderResult:
    valid: bool
    pedido: str = ""
    contrato: str = ""
    cliente: str = ""
    status: str = ""
    versao: str = ""
    valor_total: Decimal | None = None
    moeda: str = ""
    warnings: tuple[str, ...] = ()
    used_fallback: bool = False


def extrair_pedido_compra(subject: str, body: str) -> PurchaseOrderResult:
    """Extract one purchase-order header without using item/subtotal values."""
    text = normalize_body(body)
    marker_position = text.casefold().find(_SECURITY_BANNER_END.casefold())
    used_fallback = marker_position < 0
    content = (
        text[marker_position + len(_SECURITY_BANNER_END):]
        if marker_position >= 0
        else text
    )
    warnings: list[str] = []
    if used_fallback:
        warnings.append("Pedido: marcador de banner ausente; fallback aplicado ao Body completo")

    block_match = _ORDER_BLOCK_PATTERN.search(content)
    if not block_match:
        warnings.append("pedido_bloco_principal_nao_identificado")
        return PurchaseOrderResult(False, warnings=tuple(warnings), used_fallback=used_fallback)

    block_from_order = content[block_match.start():]
    version_match = _VERSION_PATTERN.search(block_from_order)
    header_block = (
        block_from_order[:version_match.end()]
        if version_match
        else block_from_order
    )

    subject_orders = _unique(_ORDER_NUMBER_PATTERN.findall(subject or ""))
    body_orders = _unique(_ORDER_NUMBER_PATTERN.findall(header_block))
    pedido = ""
    if len(subject_orders) == 1:
        pedido = subject_orders[0]
        if len(body_orders) == 1 and body_orders[0] != pedido:
            warnings.append("pedido_subject_body_divergente")
        elif len(body_orders) > 1:
            warnings.append("pedido_body_ambiguo")
    elif len(subject_orders) > 1:
        warnings.append("pedido_subject_ambiguo")
        if len(body_orders) == 1:
            pedido = body_orders[0]
            warnings.append("pedido_obtido_por_fallback_do_body")
    elif len(body_orders) == 1:
        pedido = body_orders[0]
        warnings.append("pedido_obtido_por_fallback_do_body")
    elif len(body_orders) > 1:
        warnings.append("pedido_body_ambiguo")
    else:
        warnings.append("pedido_nao_identificado")

    status = ""
    status_match = _STATUS_PATTERN.search(header_block)
    if status_match:
        status = _clean_status(status_match.group("status"))
    if not status:
        warnings.append("pedido_status_nao_identificado")

    versao = version_match.group("version") if version_match else ""
    if not versao:
        warnings.append("pedido_versao_nao_identificada")

    value_scope = (
        block_from_order[:version_match.start()]
        if version_match
        else header_block
    )
    value_pairs = list(_MONEY_PAIR_PATTERN.finditer(value_scope))
    valor_total = None
    moeda = ""
    if value_pairs:
        selected_value = value_pairs[-1]
        valor_total = _parse_brazilian_decimal(selected_value.group("amount"))
        moeda = selected_value.group("currency").upper()
        if valor_total is None:
            warnings.append("pedido_valor_invalido")
            moeda = ""
    else:
        warnings.append("pedido_valor_moeda_nao_identificados")

    cliente = _extract_client(content)
    if not cliente:
        warnings.append("pedido_cliente_nao_identificado")

    contrato, contract_warning = _extract_contract(content)
    if contract_warning:
        warnings.append(contract_warning)

    return PurchaseOrderResult(
        True,
        pedido,
        contrato,
        cliente,
        status,
        versao,
        valor_total,
        moeda,
        tuple(warnings),
        used_fallback,
    )


def _clean_status(value: str) -> str:
    text = _URL_PATTERN.sub(" ", value)
    text = _IMAGE_REFERENCE_PATTERN.sub(" ", text)
    text = _MARKDOWN_PATTERN.sub(" ", text)
    text = re.sub(r"[<>]+", " ", text)
    return " ".join(text.split()).strip(" -:;|")


def _parse_brazilian_decimal(value: str) -> Decimal | None:
    try:
        return Decimal(value.replace(".", "").replace(",", "."))
    except (InvalidOperation, AttributeError):
        return None


def _extract_client(content: str) -> str:
    lines = [line.strip() for line in content.split("\n")]
    for index, line in enumerate(lines):
        if line.casefold() != "de:":
            continue
        cursor = index + 1
        while cursor < len(lines) and not lines[cursor]:
            cursor += 1
        if cursor >= len(lines) or lines[cursor].casefold() != "cliente":
            continue
        cursor += 1
        while cursor < len(lines) and not lines[cursor]:
            cursor += 1
        return lines[cursor] if cursor < len(lines) else ""
    return ""


def _extract_contract(content: str) -> tuple[str, str]:
    lines = [line.strip() for line in content.split("\n")]
    formal_contracts: list[str] = []
    for index, line in enumerate(lines):
        if line.rstrip(":").casefold() != "número do contrato":
            continue
        for candidate_line in lines[index + 1:index + 7]:
            match = _CONTRACT_NUMBER_PATTERN.search(candidate_line)
            if match:
                formal_contracts.append(match.group(0))
                break
    unique_formal = _unique(formal_contracts)
    if len(unique_formal) == 1:
        return unique_formal[0], ""
    if len(unique_formal) > 1:
        return "", "pedido_multiplos_contratos_formais"

    fallback_contracts = _unique(_EXPLICIT_CONTRACT_PATTERN.findall(content))
    if len(fallback_contracts) == 1:
        return fallback_contracts[0], "contrato_obtido_por_fallback_explicito"
    if len(fallback_contracts) > 1:
        return "", "pedido_contrato_fallback_ambiguo"
    return "", "pedido_contrato_nao_identificado"


def _unique(values) -> list[str]:
    return list(dict.fromkeys(values))
