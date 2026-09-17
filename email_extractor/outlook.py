from collections.abc import Callable, Iterable
from collections import Counter
from datetime import datetime
import locale
import re
from threading import Event

try:
    from .cleaning import find_email_id
    from .models import (
        ALLOWED_SENDERS,
        EmailRecord,
        SearchCriteria,
        sender_is_allowed,
        subject_matches,
        subject_terms,
        structured_subject_category,
        uses_purchase_order_layout,
    )
    from .petronect import (
        extrair_tipo_mensagem,
        extrair_tipo_mensagem_cancelada,
        extrair_tipo_mensagem_prorrogada,
        normalize_body,
    )
    from .localization import alphabetical_key
    from .purchase_order import extrair_pedido_compra
except ImportError:
    # Support direct diagnostics such as `python email_extractor/outlook.py`.
    from cleaning import find_email_id
    from models import (
        ALLOWED_SENDERS,
        EmailRecord,
        SearchCriteria,
        sender_is_allowed,
        subject_matches,
        subject_terms,
        structured_subject_category,
        uses_purchase_order_layout,
    )
    from petronect import (
        extrair_tipo_mensagem,
        extrair_tipo_mensagem_cancelada,
        extrair_tipo_mensagem_prorrogada,
        normalize_body,
    )
    from localization import alphabetical_key
    from purchase_order import extrair_pedido_compra


class OutlookUnavailableError(RuntimeError):
    """Raised when Outlook COM automation is not available."""


class OutlookEmailSource:
    """Reads Outlook folders and messages without moving or changing emails."""

    def __init__(self) -> None:
        try:
            import win32com.client
        except ImportError as exc:
            raise OutlookUnavailableError(
                "pywin32 não está instalado. Instale as dependências do projeto."
            ) from exc
        try:
            self._outlook = win32com.client.Dispatch("Outlook.Application")
            self._namespace = self._outlook.GetNamespace("MAPI")
        except Exception as exc:
            raise OutlookUnavailableError(
                "Não foi possível conectar ao Outlook instalado neste computador."
            ) from exc

    def list_folder_tree(self) -> list[tuple[str, str, str]]:
        folders = []
        for index in range(1, self._namespace.Folders.Count + 1):
            mailbox = self._namespace.Folders.Item(index)
            self._append_folder_tree(folders, mailbox, mailbox.Name)
        return folders

    def list_mailboxes(self) -> list[str]:
        mailboxes = [
            self._namespace.Folders.Item(index).Name
            for index in range(1, self._namespace.Folders.Count + 1)
        ]
        return sorted(dict.fromkeys(mailboxes), key=alphabetical_key)

    def list_inbox_folders(self, mailbox_name: str, max_depth: int = 2) -> list[tuple[int, str, str]]:
        mailbox = self._namespace.Folders.Item(mailbox_name)
        inbox = self._find_inbox(mailbox)
        if inbox is None:
            raise OutlookUnavailableError(
                f"A caixa '{mailbox_name}' não possui uma pasta de entrada reconhecida."
            )
        folders: list[tuple[int, str, str]] = []
        self._append_limited_folders(folders, inbox, 0, max_depth)
        return folders

    def iter_matching(
        self,
        criteria: SearchCriteria,
        on_progress: Callable[[str], None] | None = None,
        on_detail: Callable[[str], None] | None = None,
        stop_event: Event | None = None,
    ) -> Iterable[EmailRecord]:
        mailbox = self._namespace.Folders.Item(criteria.mailbox_name)
        folder = self._find_folder(mailbox, criteria.folder_path) if criteria.folder_path else mailbox
        if folder is None:
            raise OutlookUnavailableError("A pasta selecionada não foi encontrada no Outlook.")
        yield from self._walk_folder(folder, criteria, on_progress, on_detail, stop_event)

    def _walk_folder(self, folder, criteria, on_progress, on_detail, stop_event) -> Iterable[EmailRecord]:
        if stop_event and stop_event.is_set():
            return
        if on_progress:
            on_progress(f"Pesquisando: {folder.FolderPath}")
        items = folder.Items
        total_items = items.Count
        mail_items = 0
        date_items = 0
        subject_items = 0
        date_errors = 0
        older_items = 0
        different_subject_items = 0
        allowed_sender_items = 0
        different_sender_items = 0
        non_mail_items = 0
        after_start_items = 0
        earliest_received = None
        latest_received = None
        message_classes: Counter[str] = Counter()
        received_types: Counter[str] = Counter()
        if on_progress:
            on_progress(f"Itens encontrados na pasta: {total_items}")
        sorted_by_received = False
        try:
            items.Sort("[ReceivedTime]", True)
            sorted_by_received = True
        except Exception:
            # Some Outlook folders contain item types without ReceivedTime.
            pass
        if on_detail:
            on_detail(
                f"PASTA_METADADOS caminho={folder.FolderPath!r}; total_itens={total_items}; "
                f"ordenado_por_received_time={sorted_by_received}; corte={criteria.start_at.isoformat(sep=' ')}; "
                f"assunto_informado={bool(criteria.subject)}; assunto_caracteres={len(criteria.subject)}; "
                f"termos_assunto={len(subject_terms(criteria.subject))}; remetentes_permitidos={len(ALLOWED_SENDERS)}"
            )
        for index in range(1, total_items + 1):
            if stop_event and stop_event.is_set():
                return
            message = items.Item(index)
            if not self._is_mail_item(message):
                non_mail_items += 1
                continue
            mail_items += 1
            message_class = str(self._safe_property(message, "MessageClass"))
            message_classes[message_class] += 1
            raw_received = self._safe_property(message, "ReceivedTime")
            received_types[self._type_name(raw_received)] += 1
            received_at = self._received_at(message, on_detail, index)
            if received_at is None:
                date_errors += 1
                if on_progress and date_errors <= 3:
                    on_progress("Aviso: não foi possível converter a data de recebimento de um email")
                continue
            date_items += 1
            earliest_received = received_at if earliest_received is None else min(earliest_received, received_at)
            latest_received = received_at if latest_received is None else max(latest_received, received_at)
            if on_detail and mail_items <= 3:
                on_detail(self._structural_sample(message, index, raw_received, received_at))
            if received_at < criteria.start_at:
                older_items += 1
                continue
            after_start_items += 1
            sender_email = self._sender_email(message)
            if not sender_is_allowed(sender_email):
                different_sender_items += 1
                continue
            allowed_sender_items += 1
            if not subject_matches(str(getattr(message, "Subject", "")), criteria.subject):
                different_subject_items += 1
                continue
            subject_items += 1
            subject = str(getattr(message, "Subject", ""))
            body = str(getattr(message, "Body", ""))
            normalized_body = normalize_body(body)
            email_id = find_email_id(normalized_body)
            if uses_purchase_order_layout(criteria.subject):
                purchase_order = extrair_pedido_compra(subject, body)
                if on_progress:
                    for warning in purchase_order.warnings:
                        on_progress(f"Aviso no tratamento Pedido: {warning}")
                if not purchase_order.valid:
                    continue
                yield EmailRecord(
                    received_at,
                    email_id,
                    subject,
                    "",
                    "",
                    body,
                    folder.FolderPath,
                    pedido=purchase_order.pedido,
                    contrato=purchase_order.contrato,
                    cliente=purchase_order.cliente,
                    status=purchase_order.status,
                    versao=purchase_order.versao,
                    valor_total=purchase_order.valor_total,
                    moeda=purchase_order.moeda,
                )
                continue
            structured_category = structured_subject_category(subject, criteria.subject)
            if structured_category == "sala":
                parsed = extrair_tipo_mensagem(body)
                if on_progress:
                    for warning in parsed.warnings:
                        on_progress(f"Aviso no tratamento Petronect: {warning}")
                tipo, mensagem = parsed.tipo, parsed.mensagem
            elif structured_category == "prorrogada":
                parsed = extrair_tipo_mensagem_prorrogada(subject, body)
                if on_progress:
                    for warning in parsed.warnings:
                        on_progress(f"Aviso no tratamento Prorrogada: {warning}")
                tipo, mensagem = parsed.tipo, parsed.mensagem
            elif structured_category == "cancelada":
                parsed = extrair_tipo_mensagem_cancelada(subject, body)
                if on_progress:
                    for warning in parsed.warnings:
                        on_progress(f"Aviso no tratamento Cancelada: {warning}")
                tipo, mensagem = parsed.tipo, parsed.mensagem
            else:
                tipo, mensagem = "", ""
            yield EmailRecord(
                received_at,
                email_id,
                subject,
                tipo,
                mensagem,
                body,
                folder.FolderPath,
            )

        if on_progress:
            on_progress(
                f"Resumo da pasta: {mail_items} emails, {date_items} com data válida, "
                f"{after_start_items} no período, {subject_items} correspondentes ao assunto, "
                f"{date_errors} datas inválidas, "
                f"{older_items} anteriores à data inicial, "
                f"{allowed_sender_items} dos remetentes permitidos, "
                f"{different_sender_items} fora do filtro de remetente, "
                f"{different_subject_items} fora do filtro de assunto, {non_mail_items} itens não-email"
            )
            if earliest_received is not None and latest_received is not None:
                on_progress(
                    "Intervalo de recebimento encontrado: "
                    f"{earliest_received.isoformat(sep=' ')} até {latest_received.isoformat(sep=' ')}"
                )
            if date_items and after_start_items == 0:
                on_progress(
                    "Diagnóstico: nenhum email atingiu a data inicial; "
                    f"o mais recente é {latest_received.isoformat(sep=' ') if latest_received else 'indisponível'} "
                    f"e o corte é {criteria.start_at.isoformat(sep=' ')}. "
                    "O filtro de assunto não foi aplicado a esses itens."
                )
            elif after_start_items and allowed_sender_items == 0:
                on_progress(
                    "Diagnóstico: existem emails no período, mas nenhum pertence aos "
                    "remetentes permitidos; o filtro de assunto não foi aplicado a esses itens."
                )
        if on_detail:
            on_detail(
                f"PASTA_ESTATISTICAS caminho={folder.FolderPath!r}; "
                f"intervalo_inicio={earliest_received.isoformat(sep=' ') if earliest_received else None}; "
                f"intervalo_fim={latest_received.isoformat(sep=' ') if latest_received else None}; "
                f"no_periodo={after_start_items}; remetentes_permitidos={allowed_sender_items}; "
                f"remetentes_rejeitados={different_sender_items}; classes={dict(message_classes)!r}; "
                f"tipos_received_time={dict(received_types)!r}"
            )

        for index in range(1, folder.Folders.Count + 1):
            yield from self._walk_folder(folder.Folders.Item(index), criteria, on_progress, on_detail, stop_event)

    def _append_folder_tree(self, folders, folder, mailbox_name: str) -> None:
        folders.append((mailbox_name, folder.Name, folder.FolderPath))
        for index in range(1, folder.Folders.Count + 1):
            self._append_folder_tree(folders, folder.Folders.Item(index), mailbox_name)

    def _find_inbox(self, mailbox):
        inbox_names = {"inbox", "caixa de entrada", "boîte de réception"}
        for index in range(1, mailbox.Folders.Count + 1):
            folder = mailbox.Folders.Item(index)
            if str(folder.Name).casefold() in inbox_names:
                return folder
        return None

    def _append_limited_folders(self, folders, folder, depth: int, max_depth: int) -> None:
        folders.append((depth, folder.Name, folder.FolderPath))
        if depth >= max_depth:
            return
        children = [folder.Folders.Item(index) for index in range(1, folder.Folders.Count + 1)]
        for child in sorted(children, key=lambda item: alphabetical_key(str(item.Name))):
            self._append_limited_folders(folders, child, depth + 1, max_depth)

    def _find_folder(self, folder, folder_path: str):
        if folder.FolderPath == folder_path:
            return folder
        for index in range(1, folder.Folders.Count + 1):
            found = self._find_folder(folder.Folders.Item(index), folder_path)
            if found is not None:
                return found
        return None

    @staticmethod
    def _is_mail_item(message) -> bool:
        return str(getattr(message, "MessageClass", "")).startswith("IPM.Note")

    @staticmethod
    def _received_at(message, on_detail: Callable[[str], None] | None = None, index: int | None = None) -> datetime | None:
        received_error = ""
        try:
            value = message.ReceivedTime
            converted = OutlookEmailSource._coerce_datetime(value)
            if converted is not None:
                return converted
            received_error = f"valor não convertido: {OutlookEmailSource._describe(value)}"
        except Exception:
            received_error = "ReceivedTime: {0}".format(OutlookEmailSource._exception_text())
        try:
            accessor = message.PropertyAccessor
            value = accessor.GetProperty("http://schemas.microsoft.com/mapi/proptag/0x0E060040")
            converted = OutlookEmailSource._coerce_datetime(value)
            if converted is not None:
                return converted
            received_error += f"; MAPI não convertido: {OutlookEmailSource._describe(value)}"
        except Exception:
            received_error += "; MAPI: {0}".format(OutlookEmailSource._exception_text())
        if on_detail:
            subject = OutlookEmailSource._safe_property(message, "Subject")
            message_class = OutlookEmailSource._safe_property(message, "MessageClass")
            on_detail(
                f"DATA_INVALIDA indice={index}; MessageClass={message_class!r}; "
                f"assunto_caracteres={OutlookEmailSource._safe_text_length(subject)}; motivo={received_error}"
            )
        return None

    @staticmethod
    def _exception_text() -> str:
        import sys

        return f"{type(sys.exc_info()[1]).__name__}: {sys.exc_info()[1]}"

    @staticmethod
    def _describe(value) -> str:
        return f"tipo={type(value).__module__}.{type(value).__name__}; repr={value!r}"

    @staticmethod
    def _safe_property(message, name: str):
        try:
            return getattr(message, name)
        except Exception as exc:
            return f"<erro {type(exc).__name__}: {exc}>"

    @staticmethod
    def _safe_text_length(value) -> int | str:
        try:
            return len(str(value or ""))
        except Exception as exc:
            return f"erro:{type(exc).__name__}"

    @staticmethod
    def _type_name(value) -> str:
        return f"{type(value).__module__}.{type(value).__name__}"

    @staticmethod
    def _safe_attachment_count(message) -> int | str:
        try:
            return int(message.Attachments.Count)
        except Exception as exc:
            return f"erro:{type(exc).__name__}"

    @staticmethod
    def _sender_email(message) -> str:
        """Return an SMTP address without logging or exposing it in diagnostics."""
        try:
            address = str(getattr(message, "SenderEmailAddress", "") or "").strip()
        except Exception:
            address = ""
        if address and not address.startswith("/"):
            return address
        try:
            return str(
                message.PropertyAccessor.GetProperty(
                    "http://schemas.microsoft.com/mapi/proptag/0x39FE001E"
                )
                or ""
            ).strip()
        except Exception:
            return ""

    @staticmethod
    def _structural_sample(message, index: int, raw_received, received_at: datetime) -> str:
        """Describe an email's structure without logging addresses, subject or body content."""
        subject = OutlookEmailSource._safe_property(message, "Subject")
        body = OutlookEmailSource._safe_property(message, "Body")
        html_body = OutlookEmailSource._safe_property(message, "HTMLBody")
        size = OutlookEmailSource._safe_property(message, "Size")
        message_class = OutlookEmailSource._safe_property(message, "MessageClass")
        raw_timezone = getattr(raw_received, "tzinfo", None)
        try:
            raw_offset = raw_received.utcoffset() if raw_timezone is not None else None
        except Exception as exc:
            raw_offset = f"erro:{type(exc).__name__}"
        return (
            f"EMAIL_AMOSTRA indice={index}; objeto_tipo={OutlookEmailSource._type_name(message)}; "
            f"message_class={message_class!r}; received_tipo={OutlookEmailSource._type_name(raw_received)}; "
            f"received_normalizado={received_at.isoformat(sep=' ')}; "
            f"received_tem_timezone={raw_timezone is not None}; received_utc_offset={raw_offset}; "
            f"assunto_caracteres="
            f"{OutlookEmailSource._safe_text_length(subject)}; body_caracteres="
            f"{OutlookEmailSource._safe_text_length(body)}; html_body_caracteres="
            f"{OutlookEmailSource._safe_text_length(html_body)}; anexos="
            f"{OutlookEmailSource._safe_attachment_count(message)}; tamanho_bytes={size!r}"
        )

    @staticmethod
    def _coerce_datetime(value) -> datetime | None:
        if value is None:
            return None
        if all(hasattr(value, field) for field in ("year", "month", "day")):
            try:
                return datetime(
                    int(value.year), int(value.month), int(value.day),
                    int(getattr(value, "hour", 0)), int(getattr(value, "minute", 0)),
                    int(getattr(value, "second", 0)), int(getattr(value, "microsecond", 0)),
                )
            except (TypeError, ValueError):
                pass
        if isinstance(value, str):
            for format_string in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
                try:
                    return datetime.strptime(value, format_string)
                except ValueError:
                    continue
            match = re.fullmatch(
                r"\s*(\d{1,2})/(\d{1,2})/(\d{4})[ T](\d{1,2}):(\d{2}):(\d{2})\s*",
                value,
            )
            if match:
                first, second, year, hour, minute, second_value = map(int, match.groups())
                if first > 12:
                    day, month = first, second
                elif second > 12:
                    month, day = first, second
                else:
                    locale_name = (locale.getlocale()[0] or "").replace("-", "_").casefold()
                    month_first = locale_name.startswith("en_us")
                    month, day = (first, second) if month_first else (second, first)
                try:
                    return datetime(year, month, day, hour, minute, second_value)
                except ValueError:
                    return None
        return None
