"""Microsoft Graph email source for the Outlook-independent test phase."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
from threading import Event
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

from .cleaning import find_email_id
from .localization import alphabetical_key
from .models import (
    ALLOWED_SENDERS,
    EmailRecord,
    SearchCriteria,
    sender_is_allowed,
    structured_subject_category,
    subject_matches,
    subject_terms,
    uses_purchase_order_layout,
)
from .petronect import (
    extrair_tipo_mensagem,
    extrair_tipo_mensagem_cancelada,
    extrair_tipo_mensagem_prorrogada,
    normalize_body,
)
from .purchase_order import extrair_pedido_compra


GRAPH_ROOT = "https://graph.microsoft.com/v1.0"
GRAPH_SCOPES = ["User.Read", "Mail.Read", "Mail.Read.Shared"]
EMBEDDED_GRAPH_CONFIG = {
    "client_id": "99944267-f7a2-49ed-89a8-89d70be31a8f",
    "tenant_id": "eb06985d-06ca-4a17-81da-629ab99f6505",
    "shared_mailboxes": [
        {
            "label": "Petrobras, Suporte",
            "user_id": "Suporte.Petrobras@emerson.com",
        },
        {
            "label": "petronect, notificacoes",
            "user_id": "notificacoes.petronect@emerson.com",
        },
    ],
}


class GraphUnavailableError(RuntimeError):
    """Raised when Graph configuration, authentication or access fails."""


@dataclass(frozen=True)
class GraphMailbox:
    label: str
    user_id: str


def graph_config_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return base / "PetronectEmailExtractor" / "graph_config.json"


def load_graph_config(path: Path | None = None) -> dict:
    """Load an optional local override, otherwise use the distributable defaults."""
    config_path = path or graph_config_path()
    if not config_path.exists():
        return _copy_embedded_config()
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GraphUnavailableError(f"Configuração Graph inválida em {config_path}: {exc}") from exc
    client_id = str(config.get("client_id", "")).strip()
    tenant_id = str(config.get("tenant_id", "")).strip()
    if not client_id or client_id.startswith("COLE_AQUI") or not tenant_id or tenant_id.startswith("COLE_AQUI"):
        return _copy_embedded_config()
    return config


def _copy_embedded_config() -> dict:
    """Return an independent copy so callers cannot mutate application defaults."""
    return {
        "client_id": EMBEDDED_GRAPH_CONFIG["client_id"],
        "tenant_id": EMBEDDED_GRAPH_CONFIG["tenant_id"],
        "shared_mailboxes": [dict(item) for item in EMBEDDED_GRAPH_CONFIG["shared_mailboxes"]],
    }


class GraphEmailSource:
    """Read mailboxes and messages through delegated Microsoft Graph access."""

    def __init__(
        self,
        on_authentication: Callable[[dict], None] | None = None,
        parent_window_handle: int | None = None,
    ) -> None:
        self._config = load_graph_config()
        self._on_authentication = on_authentication
        self._parent_window_handle = parent_window_handle
        self._token = self._acquire_token()
        self._mailboxes: dict[str, GraphMailbox] = {}

    def _acquire_token(self) -> str:
        try:
            import msal
            from msal_extensions import FilePersistenceWithDataProtection, PersistedTokenCache
        except ImportError as exc:
            raise GraphUnavailableError("Dependências MSAL não instaladas. Reinstale os requisitos.") from exc
        cache_path = graph_config_path().with_name("msal_token_cache.bin")
        cache = PersistedTokenCache(FilePersistenceWithDataProtection(str(cache_path)))
        app_options = {
            "authority": f"https://login.microsoftonline.com/{self._config['tenant_id']}",
            "token_cache": cache,
        }
        if sys.platform == "win32":
            app_options["enable_broker_on_windows"] = True
        try:
            app = msal.PublicClientApplication(
                str(self._config["client_id"]),
                **app_options,
            )
        except ImportError as exc:
            raise GraphUnavailableError(
                "O componente de autenticação WAM não está instalado. Reinstale as dependências "
                "da aplicação com suporte ao broker MSAL."
            ) from exc
        accounts = app.get_accounts()
        result = app.acquire_token_silent(GRAPH_SCOPES, account=accounts[0]) if accounts else None
        if not result:
            if sys.platform == "win32":
                window_handle = self._parent_window_handle or app.CONSOLE_WINDOW_HANDLE
                try:
                    result = app.acquire_token_interactive(
                        GRAPH_SCOPES,
                        parent_window_handle=window_handle,
                    )
                except Exception as exc:
                    raise GraphUnavailableError(
                        "Falha no login corporativo pelo Windows Web Account Manager (WAM). "
                        "Confirme a URI de redirecionamento do broker no Microsoft Entra e peça "
                        "ao TI para consultar as políticas de Conditional Access aplicadas. "
                        f"Detalhe: {type(exc).__name__}: {exc}"
                    ) from exc
            else:
                flow = app.initiate_device_flow(scopes=GRAPH_SCOPES)
                if "user_code" not in flow:
                    raise GraphUnavailableError(
                        f"Não foi possível iniciar a autenticação: {flow.get('error_description', flow)}"
                    )
                if self._on_authentication:
                    self._on_authentication(dict(flow))
                result = app.acquire_token_by_device_flow(flow)
        token = result.get("access_token") if result else None
        if not token:
            error = (result or {}).get("error", "erro_desconhecido")
            description = (result or {}).get("error_description", "resposta sem token")
            correlation_id = (result or {}).get("correlation_id", "não informado")
            raise GraphUnavailableError(
                "Falha na autenticação Microsoft Graph: "
                f"erro={error}; correlation_id={correlation_id}; detalhe={description}"
            )
        return str(token)

    def _get(self, url: str, retries: int = 4) -> dict:
        parsed_url = urlparse(url)
        if parsed_url.scheme != "https" or parsed_url.netloc.casefold() != "graph.microsoft.com":
            raise GraphUnavailableError("O Graph retornou uma URL de paginação fora do domínio permitido.")
        for attempt in range(retries + 1):
            request = Request(
                url,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Accept": "application/json",
                    "Prefer": 'outlook.body-content-type="text"',
                },
            )
            try:
                with urlopen(request, timeout=45) as response:
                    return json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                if exc.code == 429 or 500 <= exc.code < 600:
                    if attempt < retries:
                        delay = int(exc.headers.get("Retry-After", min(2 ** attempt, 16)))
                        time.sleep(max(1, min(delay, 30)))
                        continue
                try:
                    detail = json.loads(exc.read().decode("utf-8")).get("error", {}).get("message", "")
                except Exception:
                    detail = ""
                raise GraphUnavailableError(f"Microsoft Graph respondeu HTTP {exc.code}: {detail or exc.reason}") from exc
            except (URLError, TimeoutError, json.JSONDecodeError) as exc:
                raise GraphUnavailableError(f"Não foi possível consultar o Microsoft Graph: {exc}") from exc
        raise GraphUnavailableError("Limite de tentativas do Microsoft Graph excedido.")

    def _pages(self, url: str) -> Iterable[dict]:
        while url:
            data = self._get(url)
            yield from data.get("value", [])
            next_url = str(data.get("@odata.nextLink", ""))
            if next_url and urlparse(next_url).netloc.casefold() != "graph.microsoft.com":
                raise GraphUnavailableError("Paginação Graph retornou um host inesperado.")
            url = next_url

    @staticmethod
    def _user_base(user_id: str) -> str:
        return "/me" if user_id == "me" else f"/users/{quote(user_id, safe='')}"

    def list_mailboxes(self) -> list[str]:
        me = self._get(f"{GRAPH_ROOT}/me?$select=displayName,mail,userPrincipalName")
        primary_label = str(me.get("mail") or me.get("userPrincipalName") or me.get("displayName") or "Minha caixa")
        mailboxes = [GraphMailbox(primary_label, "me")]
        for item in self._config.get("shared_mailboxes", []):
            if isinstance(item, str):
                user_id, label = item.strip(), item.strip()
            else:
                user_id = str(item.get("user_id") or item.get("address") or "").strip()
                label = str(item.get("label") or user_id).strip()
            if user_id:
                mailboxes.append(GraphMailbox(label, user_id))
        self._mailboxes = {item.label: item for item in mailboxes}
        return sorted(self._mailboxes, key=alphabetical_key)

    def _mailbox(self, label: str) -> GraphMailbox:
        if label not in self._mailboxes:
            self.list_mailboxes()
        try:
            return self._mailboxes[label]
        except KeyError as exc:
            raise GraphUnavailableError(f"Caixa Graph não configurada: {label}") from exc

    @staticmethod
    def _folder_path(user_id: str, folder_id: str) -> str:
        return f"graph://{quote(user_id, safe='')}/{quote(folder_id, safe='')}"

    @staticmethod
    def _parse_folder_path(path: str) -> tuple[str, str]:
        from urllib.parse import unquote

        parsed = urlparse(path)
        if parsed.scheme != "graph" or not parsed.netloc or not parsed.path.strip("/"):
            raise GraphUnavailableError("Identificador de pasta Graph inválido.")
        return unquote(parsed.netloc), unquote(parsed.path.strip("/"))

    def list_inbox_folders(self, mailbox_name: str, max_depth: int = 2) -> list[tuple[int, str, str]]:
        """List every visible root mail folder and descendants up to max_depth."""
        mailbox = self._mailbox(mailbox_name)
        base = self._user_base(mailbox.user_id)
        inbox = self._get(f"{GRAPH_ROOT}{base}/mailFolders/inbox?$select=id,displayName,childFolderCount")
        query = urlencode({"$select": "id,displayName,childFolderCount", "$top": "100"})
        root_folders = list(self._pages(f"{GRAPH_ROOT}{base}/mailFolders?{query}"))
        root_by_id = {str(folder.get("id", "")): folder for folder in root_folders if folder.get("id")}
        root_by_id.setdefault(str(inbox["id"]), inbox)
        result: list[tuple[int, str, str]] = []

        def append(folder: dict, depth: int) -> None:
            folder_id = str(folder["id"])
            result.append((depth, str(folder.get("displayName") or "Inbox"), self._folder_path(mailbox.user_id, folder_id)))
            if depth >= max_depth or not folder.get("childFolderCount"):
                return
            children = list(self._pages(f"{GRAPH_ROOT}{base}/mailFolders/{quote(folder_id, safe='')}/childFolders?{query}"))
            for child in sorted(children, key=lambda item: alphabetical_key(str(item.get("displayName", "")))):
                append(child, depth + 1)

        inbox_id = str(inbox["id"])
        ordered_roots = sorted(
            root_by_id.values(),
            key=lambda folder: (
                str(folder.get("id")) != inbox_id,
                alphabetical_key(str(folder.get("displayName", ""))),
            ),
        )
        for root_folder in ordered_roots:
            append(root_folder, 0)
        return result

    @staticmethod
    def _received_at(value: str) -> datetime | None:
        try:
            aware = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return aware.astimezone().replace(tzinfo=None)
        except (AttributeError, TypeError, ValueError):
            return None

    def iter_matching(self, criteria: SearchCriteria, on_progress=None, on_detail=None, stop_event: Event | None = None) -> Iterable[EmailRecord]:
        user_id, root_folder_id = self._parse_folder_path(criteria.folder_path)
        base = self._user_base(user_id)
        yield from self._walk_folder(base, root_folder_id, criteria, on_progress, on_detail, stop_event, 0)

    def _walk_folder(self, base, folder_id, criteria, on_progress, on_detail, stop_event, depth):
        if stop_event and stop_event.is_set():
            return
        folder = self._get(f"{GRAPH_ROOT}{base}/mailFolders/{quote(folder_id, safe='')}?$select=id,displayName,childFolderCount")
        folder_name = str(folder.get("displayName") or folder_id)
        if on_progress:
            on_progress(f"Pesquisando via Microsoft Graph: {folder_name}")
        select = "id,receivedDateTime,subject,body,from,hasAttachments"
        cutoff_utc = criteria.start_at.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        query = urlencode(
            {
                "$select": select,
                "$filter": f"receivedDateTime ge {cutoff_utc}",
                "$orderby": "receivedDateTime desc",
                "$top": "100",
            }
        )
        url = f"{GRAPH_ROOT}{base}/mailFolders/{quote(folder_id, safe='')}/messages?{query}"
        stats = Counter()
        earliest = latest = None
        for index, message in enumerate(self._pages(url), 1):
            if stop_event and stop_event.is_set():
                return
            stats["emails"] += 1
            received = self._received_at(str(message.get("receivedDateTime", "")))
            if received is None:
                stats["datas_invalidas"] += 1
                continue
            stats["datas_validas"] += 1
            earliest = received if earliest is None else min(earliest, received)
            latest = received if latest is None else max(latest, received)
            body = str((message.get("body") or {}).get("content") or "")
            subject = str(message.get("subject") or "")
            if on_detail and index <= 3:
                on_detail(
                    f"GRAPH_EMAIL_AMOSTRA indice={index}; received_normalizado={received.isoformat(sep=' ')}; "
                    f"assunto_caracteres={len(subject)}; body_tipo={(message.get('body') or {}).get('contentType')!r}; "
                    f"body_caracteres={len(body)}; possui_anexos={bool(message.get('hasAttachments'))}"
                )
            if received < criteria.start_at:
                stats["anteriores"] += 1
                continue
            stats["periodo"] += 1
            sender = str((((message.get("from") or {}).get("emailAddress") or {}).get("address")) or "")
            if not sender_is_allowed(sender):
                stats["remetentes_rejeitados"] += 1
                continue
            stats["remetentes_permitidos"] += 1
            if not subject_matches(subject, criteria.subject):
                stats["assuntos_rejeitados"] += 1
                continue
            stats["correspondentes"] += 1
            normalized_body = normalize_body(body)
            email_id = find_email_id(normalized_body)
            if uses_purchase_order_layout(criteria.subject):
                parsed_order = extrair_pedido_compra(subject, body)
                if not parsed_order.valid:
                    continue
                yield EmailRecord(received, email_id, subject, "", "", body, folder_name, pedido=parsed_order.pedido, contrato=parsed_order.contrato, cliente=parsed_order.cliente, status=parsed_order.status, versao=parsed_order.versao, valor_total=parsed_order.valor_total, moeda=parsed_order.moeda)
                continue
            category = structured_subject_category(subject, criteria.subject)
            if category == "sala":
                parsed = extrair_tipo_mensagem(body)
                tipo, mensagem = parsed.tipo, parsed.mensagem
            elif category == "prorrogada":
                parsed = extrair_tipo_mensagem_prorrogada(subject, body)
                tipo, mensagem = parsed.tipo, parsed.mensagem
            elif category == "cancelada":
                parsed = extrair_tipo_mensagem_cancelada(subject, body)
                tipo, mensagem = parsed.tipo, parsed.mensagem
            else:
                tipo, mensagem = "", ""
            yield EmailRecord(received, email_id, subject, tipo, mensagem, body, folder_name)
        if on_progress:
            on_progress(
                f"Resumo Graph da pasta: {stats['emails']} emails, {stats['datas_validas']} com data válida, "
                f"{stats['periodo']} no período, {stats['correspondentes']} correspondentes ao assunto, "
                f"{stats['anteriores']} anteriores à data inicial, {stats['remetentes_permitidos']} dos remetentes permitidos, "
                f"{stats['remetentes_rejeitados']} fora do filtro de remetente"
            )
        if on_detail:
            on_detail(
                f"GRAPH_PASTA_ESTATISTICAS pasta={folder_name!r}; profundidade={depth}; termos_assunto={len(subject_terms(criteria.subject))}; "
                f"remetentes_configurados={len(ALLOWED_SENDERS)}; intervalo_inicio={earliest}; intervalo_fim={latest}; estatisticas={dict(stats)!r}"
            )
        if depth < 2 and folder.get("childFolderCount"):
            query = urlencode({"$select": "id,displayName,childFolderCount", "$top": "100"})
            for child in self._pages(f"{GRAPH_ROOT}{base}/mailFolders/{quote(folder_id, safe='')}/childFolders?{query}"):
                yield from self._walk_folder(base, str(child["id"]), criteria, on_progress, on_detail, stop_event, depth + 1)
