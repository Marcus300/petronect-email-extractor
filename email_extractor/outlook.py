from collections.abc import Callable, Iterable
from datetime import datetime
from threading import Event

try:
    from .cleaning import find_email_id
    from .models import EmailRecord, SearchCriteria
    from .petronect import extrair_tipo_mensagem, normalize_body
except ImportError:
    # Support direct diagnostics such as `python email_extractor/outlook.py`.
    from cleaning import find_email_id
    from models import EmailRecord, SearchCriteria
    from petronect import extrair_tipo_mensagem, normalize_body


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
        return [
            self._namespace.Folders.Item(index).Name
            for index in range(1, self._namespace.Folders.Count + 1)
        ]

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
        if on_progress:
            on_progress(f"Itens encontrados na pasta: {total_items}")
        try:
            items.Sort("[ReceivedTime]", True)
        except Exception:
            # Some Outlook folders contain item types without ReceivedTime.
            pass
        for index in range(1, total_items + 1):
            if stop_event and stop_event.is_set():
                return
            message = items.Item(index)
            if not self._is_mail_item(message):
                continue
            mail_items += 1
            received_at = self._received_at(message, on_detail, index)
            if received_at is None:
                date_errors += 1
                if on_progress and date_errors <= 3:
                    on_progress("Aviso: não foi possível converter a data de recebimento de um email")
                continue
            date_items += 1
            if received_at < criteria.start_at:
                older_items += 1
                continue
            if criteria.subject.casefold() not in str(getattr(message, "Subject", "")).casefold():
                different_subject_items += 1
                continue
            subject_items += 1
            subject = str(getattr(message, "Subject", ""))
            body = str(getattr(message, "Body", ""))
            parsed = extrair_tipo_mensagem(body)
            if on_progress:
                for warning in parsed.warnings:
                    on_progress(f"Aviso no tratamento Petronect: {warning}")
            yield EmailRecord(
                received_at,
                find_email_id(normalize_body(body)),
                subject,
                parsed.tipo,
                parsed.mensagem,
                body,
                folder.FolderPath,
            )

        if on_progress:
            on_progress(
                f"Resumo da pasta: {mail_items} emails, {date_items} com data válida, "
                f"{subject_items} correspondentes ao assunto, {date_errors} datas inválidas, "
                f"{older_items} anteriores à data inicial, "
                f"{different_subject_items} fora do filtro de assunto"
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
        for index in range(1, folder.Folders.Count + 1):
            self._append_limited_folders(folders, folder.Folders.Item(index), depth + 1, max_depth)

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
                f"Subject={subject!r}; motivo={received_error}"
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
            for format_string in (
                "%m/%d/%Y %H:%M:%S", "%d/%m/%Y %H:%M:%S",
                "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S",
            ):
                try:
                    return datetime.strptime(value, format_string)
                except ValueError:
                    continue
        return None
