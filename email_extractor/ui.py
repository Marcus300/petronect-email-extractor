from datetime import datetime, date, timedelta
import os
import sys
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Thread
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
import webbrowser

from .diagnostics import format_exception, runtime_metadata
from .export import export_xlsx
from .models import SearchCriteria
from .outlook import OutlookEmailSource, OutlookUnavailableError
from .update_checker import check_for_updates
from .version import __version__


DATE_FORMAT = "%d/%m/%Y %H:%M"
PROJECT_VERSION = __version__
PROJECT_GITHUB_URL = "https://github.com/marcus300"


class ExtractorWindow:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(f"Petronect Email Extractor - v{PROJECT_VERSION}")
        self._set_window_icon()
        self.root.geometry("820x640")
        self.root.minsize(700, 500)
        self.mailbox = tk.StringVar()
        self.folder_path = tk.StringVar()
        now = datetime.now()
        self.date_day = tk.StringVar(value=now.strftime("%d"))
        self.date_month = tk.StringVar(value=now.strftime("%m"))
        self.date_year = tk.StringVar(value=now.strftime("%Y"))
        self.time_hour = tk.StringVar(value=now.strftime("%H"))
        self.time_minute = tk.StringVar(value=now.strftime("%M"))
        self.subject = tk.StringVar()
        self.output_path = tk.StringVar()
        self.progress_queue: Queue[tuple[str, object]] = Queue()
        self.stop_event = Event()
        self.worker: Thread | None = None
        self.log_file_path: Path | None = None
        self.latest_output_path: Path | None = None
        self._folder_options: dict[str, str] = {}
        self._build()
        self._load_mailboxes()
        self.root.after(100, self._process_progress)
        self.root.after(1500, self._start_update_check)

    def _set_window_icon(self) -> None:
        icon_path = self._resource_path("logo.ico")
        if icon_path.exists():
            self.root.iconbitmap(str(icon_path))

    @staticmethod
    def _resource_path(filename: str) -> Path:
        if hasattr(sys, "_MEIPASS"):
            return Path(sys._MEIPASS) / filename
        return Path(__file__).resolve().parent.parent / "docs" / "logo" / filename

    def _build(self) -> None:
        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(1, weight=1)
        toolbar = ttk.Frame(frame)
        toolbar.grid(row=0, column=2, sticky="e", pady=(0, 8))
        ttk.Button(toolbar, text="About", command=self._show_about).pack()
        ttk.Label(frame, text="Caixa de pesquisa").grid(row=0, column=0, sticky="w", pady=6)
        self.mailbox_combo = ttk.Combobox(frame, textvariable=self.mailbox, state="readonly")
        self.mailbox_combo.grid(row=0, column=1, sticky="ew", pady=6)
        self.mailbox_combo.bind("<<ComboboxSelected>>", self._mailbox_selected)
        ttk.Label(frame, text="Pasta e subpastas (até 2 níveis)").grid(row=1, column=0, sticky="w", pady=6)
        self.folder_combo = ttk.Combobox(frame, textvariable=self.folder_path, state="readonly")
        self.folder_combo.grid(row=1, column=1, sticky="ew", pady=6)
        self.folder_combo.bind("<<ComboboxSelected>>", self._folder_selected)
        ttk.Label(frame, text="Data inicial").grid(row=2, column=0, sticky="w", pady=6)
        date_frame = ttk.Frame(frame)
        date_frame.grid(row=2, column=1, sticky="w", pady=6)
        self._add_segment(date_frame, self.date_day, 2, 31, minimum=1)
        ttk.Label(date_frame, text="/").pack(side="left")
        self._add_segment(date_frame, self.date_month, 2, 12, minimum=1)
        ttk.Label(date_frame, text="/").pack(side="left")
        self._add_segment(date_frame, self.date_year, 4, 9999, minimum=1)
        ttk.Button(date_frame, text="Calendário", command=self._show_calendar).pack(side="left", padx=(8, 0))

        ttk.Label(frame, text="Hora inicial").grid(row=3, column=0, sticky="w", pady=6)
        time_frame = ttk.Frame(frame)
        time_frame.grid(row=3, column=1, sticky="w", pady=6)
        self._add_segment(time_frame, self.time_hour, 2, 23)
        ttk.Label(time_frame, text=":").pack(side="left")
        self._add_segment(time_frame, self.time_minute, 2, 59)

        ttk.Label(frame, text="Assunto contém").grid(row=4, column=0, sticky="w", pady=6)
        ttk.Entry(frame, textvariable=self.subject).grid(row=4, column=1, sticky="ew", pady=6)
        ttk.Label(frame, text="Salvar Excel em").grid(row=5, column=0, sticky="w", pady=6)
        ttk.Entry(frame, textvariable=self.output_path).grid(row=5, column=1, sticky="ew", pady=6)
        ttk.Button(frame, text="Escolher", command=self._choose_output).grid(row=5, column=2, padx=(8, 0))
        buttons = ttk.Frame(frame)
        buttons.grid(row=6, column=1, sticky="e", pady=(10, 8))
        self.search_button = ttk.Button(buttons, text="Pesquisar e gerar Excel", command=self._run)
        self.search_button.pack(side="left", padx=(0, 8))
        self.cancel_button = ttk.Button(buttons, text="Encerrar execução", command=self._cancel, state="disabled")
        self.cancel_button.pack(side="left")
        self.open_button = ttk.Button(buttons, text="Abrir Excel recente", command=self._open_latest, state="disabled")
        self.open_button.pack(side="left", padx=(8, 0))
        ttk.Label(frame, text="Log da execução").grid(row=7, column=0, sticky="nw", pady=(4, 6))
        self.log = ScrolledText(frame, height=10, state="disabled", wrap="word")
        self.log.grid(row=7, column=1, columnspan=2, sticky="nsew", pady=(4, 6))
        frame.rowconfigure(7, weight=1)
        ttk.Label(frame, text="Entrar em contato:").grid(row=9, column=0, sticky="w", pady=(8, 0))
        self._add_link(
            frame,
            "marcus.brito@emerson.com",
            "mailto:marcus.brito@emerson.com",
            row=9,
            column=1,
        )

    def _add_segment(self, parent, variable, width, maximum, *, minimum=0) -> None:
        validation = (self.root.register(self._validate_segment), "%P", str(width))
        entry = ttk.Entry(
            parent,
            textvariable=variable,
            width=width,
            justify="center",
            validate="key",
            validatecommand=validation,
        )
        entry.pack(side="left")
        entry.bind("<FocusIn>", lambda _event: entry.selection_range(0, "end"))
        entry.bind("<FocusOut>", lambda _event: self._normalize_segment(entry, variable, maximum, minimum))
        entry.bind("<Return>", lambda _event: self._normalize_segment(entry, variable, maximum, minimum))

    @staticmethod
    def _validate_segment(proposed: str, width: str) -> bool:
        return (not proposed or proposed.isdigit()) and len(proposed) <= int(width)

    @staticmethod
    def _normalize_segment(entry, variable, maximum, minimum) -> None:
        digits = "".join(character for character in variable.get() if character.isdigit())
        digits = digits[:int(entry.cget("width"))]
        if digits:
            value = min(max(int(digits), minimum), maximum)
            variable.set(f"{value:0{int(entry.cget('width'))}d}")
        else:
            variable.set(f"{minimum:0{int(entry.cget('width'))}d}")

    def _show_calendar(self) -> None:
        try:
            selected = date(int(self.date_year.get()), int(self.date_month.get()), int(self.date_day.get()))
        except ValueError:
            selected = date.today()
        popup = tk.Toplevel(self.root)
        popup.title("Selecionar data")
        # The calendar is an auxiliary dialog and intentionally has no icon.
        popup.blank_icon = tk.PhotoImage(width=1, height=1)
        popup.iconphoto(False, popup.blank_icon)
        popup.transient(self.root)
        popup.resizable(False, False)
        month = [selected.year, selected.month]
        header = ttk.Frame(popup, padding=8)
        header.pack(fill="x")
        ttk.Button(header, text="<", width=3, command=lambda: self._render_calendar(body, month, -1)).pack(side="left")
        title = ttk.Label(header, width=18, anchor="center")
        title.pack(side="left", expand=True)
        ttk.Button(header, text=">", width=3, command=lambda: self._render_calendar(body, month, 1)).pack(side="right")
        body = ttk.Frame(popup, padding=(8, 0, 8, 8))
        body.pack()
        self._render_calendar(body, month, 0, title, popup)

    def _render_calendar(self, body, month, change, title=None, popup=None) -> None:
        if change:
            month[1] += change
            if month[1] == 13:
                month[:] = [month[0] + 1, 1]
            elif month[1] == 0:
                month[:] = [month[0] - 1, 12]
        for child in body.winfo_children():
            child.destroy()
        current = date(month[0], month[1], 1)
        if title:
            title.configure(text=current.strftime("%B %Y"))
        for column, name in enumerate(("Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom")):
            ttk.Label(body, text=name, width=4, anchor="center").grid(row=0, column=column)
        first_weekday = (current.weekday() + 1) % 7
        days = (date(month[0] + (month[1] == 12), month[1] % 12 + 1, 1) - timedelta(days=1)).day
        for day_number in range(1, days + 1):
            position = first_weekday + day_number - 1
            button = ttk.Button(body, text=str(day_number), width=4, command=lambda day=day_number: self._choose_date(day, month, popup))
            button.grid(row=1 + position // 7, column=position % 7, padx=1, pady=1)

    def _choose_date(self, day, month, popup) -> None:
        self.date_day.set(f"{day:02d}")
        self.date_month.set(f"{month[1]:02d}")
        self.date_year.set(f"{month[0]:04d}")
        popup.destroy()

    def _start_datetime(self) -> datetime:
        return datetime.strptime(
            f"{self.date_day.get()}/{self.date_month.get()}/{self.date_year.get()} "
            f"{self.time_hour.get()}:{self.time_minute.get()}",
            DATE_FORMAT,
        )

    def _show_about(self) -> None:
        popup = tk.Toplevel(self.root)
        popup.title("About - Petronect Email Extractor")
        self._set_icon_for(popup)
        popup.transient(self.root)
        popup.resizable(False, False)
        popup.geometry("640x540")
        content = ttk.Frame(popup, padding=22)
        content.pack(fill="both", expand=True)
        content.columnconfigure(1, weight=1)
        logo_path = self._resource_path("logo.png")
        if logo_path.exists():
            image = tk.PhotoImage(file=str(logo_path))
            scale = max(1, (max(image.width(), image.height()) + 149) // 150)
            if scale > 1:
                image = image.subsample(scale, scale)
            popup.logo_image = image
            ttk.Label(content, image=image).grid(row=0, column=0, rowspan=5, padx=(0, 24), sticky="n")
        details = ttk.Frame(content)
        details.grid(row=0, column=1, sticky="new")
        ttk.Label(details, text="Petronect Email Extractor", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(details, text=f"Versão {PROJECT_VERSION}").pack(anchor="w", pady=(5, 14))
        ttk.Label(
            details,
            text="Ferramenta para pesquisa e extração de emails Petronect no Outlook.",
            wraplength=385,
            justify="left",
        ).pack(anchor="w")
        ttk.Label(details, text="Desenvolvido por Marcus Brito").pack(anchor="w", pady=(14, 5))
        self._add_link(details, "marcus.brito@emerson.com", "mailto:marcus.brito@emerson.com")
        self._add_link(details, "marcus300@gmail.com", "mailto:marcus300@gmail.com")
        self._add_link(details, PROJECT_GITHUB_URL, PROJECT_GITHUB_URL)

        separator = ttk.Separator(content, orient="horizontal")
        separator.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(22, 16))
        license_frame = ttk.LabelFrame(content, text="Licença", padding=14)
        license_frame.grid(row=6, column=0, columnspan=2, sticky="ew")
        ttk.Label(
            license_frame,
            text=(
                "Licença MIT\n\n"
                "Copyright (c) 2026 Marcus Brito\n\n"
                "É concedida permissão, gratuitamente, a qualquer pessoa que obtenha uma cópia "
                "deste software, para usá-lo, copiá-lo, modificá-lo e distribuí-lo, sujeita à "
                "inclusão do aviso de copyright e da licença.\n\n"
                "O software é fornecido ‘como está’, sem garantia de qualquer tipo."
            ),
            justify="left",
            wraplength=555,
        ).pack(anchor="w")
        ttk.Label(
            content,
            text="Verificação de atualizações pelo GitHub: habilitada.",
        ).grid(row=7, column=0, columnspan=2, sticky="w", pady=(14, 0))
        actions = ttk.Frame(content)
        actions.grid(row=8, column=0, columnspan=2, sticky="e", pady=(18, 0))
        ttk.Button(actions, text="Verificar atualizações", command=self._start_update_check).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Fechar", command=popup.destroy).pack(side="left")

    def _start_update_check(self) -> None:
        Thread(target=self._check_updates_worker, daemon=True).start()

    def _check_updates_worker(self) -> None:
        try:
            status = check_for_updates(PROJECT_VERSION)
            self.progress_queue.put(("update_status", status))
        except Exception as exc:
            self.progress_queue.put(("update_error", f"{type(exc).__name__}: {exc}"))

    def _set_icon_for(self, window) -> None:
        icon_path = self._resource_path("logo.ico")
        if icon_path.exists():
            window.iconbitmap(str(icon_path))

    @staticmethod
    def _add_link(
        parent,
        text: str,
        target: str,
        row: int | None = None,
        column: int = 0,
    ) -> None:
        link = tk.Label(parent, text=text, fg="#0563c1", cursor="hand2")
        if row is None:
            link.pack(anchor="w", pady=1)
        else:
            link.grid(row=row, column=column, sticky="w", pady=1)
        link.bind("<Button-1>", lambda _event: webbrowser.open(target))

    def _load_mailboxes(self) -> None:
        try:
            mailboxes = OutlookEmailSource().list_mailboxes()
        except OutlookUnavailableError as exc:
            self._write_log(str(exc))
            return
        self.mailbox_combo["values"] = mailboxes
        if mailboxes:
            self.mailbox.set(mailboxes[0])
            self._load_inbox_folders()

    def _mailbox_selected(self, _event=None) -> None:
        self._load_inbox_folders()

    def _load_inbox_folders(self) -> None:
        try:
            folders = OutlookEmailSource().list_inbox_folders(self.mailbox.get(), max_depth=2)
        except OutlookUnavailableError as exc:
            self.folder_combo["values"] = []
            self.folder_path.set("")
            self._write_log(str(exc))
            return
        values = [f"{'    ' * depth}{name}" for depth, name, _path in folders]
        self.folder_combo["values"] = values
        self._folder_options = {value: path for value, (_depth, _name, path) in zip(values, folders)}
        if values:
            self.folder_combo.current(0)
            self.folder_path.set(folders[0][2])

    def _folder_selected(self, _event=None) -> None:
        self.folder_path.set(self._folder_options.get(self.folder_combo.get(), ""))

    def _choose_output(self) -> None:
        selected = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
        if selected:
            self.output_path.set(selected)

    def _run(self) -> None:
        try:
            output_text = self.output_path.get().strip()
            if not all([self.mailbox.get().strip(), self.folder_path.get().strip(), self.subject.get().strip(), output_text]):
                raise ValueError("Selecione uma pasta e preencha data, assunto e destino do Excel.")
            criteria = SearchCriteria(self.mailbox.get().strip(), self.folder_path.get().strip(), self._start_datetime(), self.subject.get().strip(), Path(output_text))
        except ValueError as exc:
            messagebox.showerror("Dados inválidos", str(exc))
            return
        self.stop_event.clear()
        try:
            self._clear_log(Path(output_text))
        except OSError as exc:
            messagebox.showerror(
                "Destino indisponível",
                f"Não foi possível criar o log na pasta escolhida.\n\n{type(exc).__name__}: {exc}",
            )
            return
        self.latest_output_path = None
        self.open_button.configure(state="disabled")
        self.search_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self._write_log(f"Iniciando pesquisa em: {criteria.folder_path}")
        self.worker = Thread(target=self._worker_run, args=(criteria,), daemon=True)
        self.worker.start()

    def _worker_run(self, criteria: SearchCriteria) -> None:
        com_initialized = False
        try:
            import pythoncom

            pythoncom.CoInitialize()
            com_initialized = True
            source = OutlookEmailSource()
            records = source.iter_matching(
                criteria,
                self._queue_progress,
                self._queue_detail,
                self.stop_event,
            )
            count = export_xlsx(records, criteria.output_path, self._queue_progress)
            self.progress_queue.put(("cancelled" if self.stop_event.is_set() else "finished", count))
        except Exception as exc:
            self.progress_queue.put(("error", format_exception(exc)))
        finally:
            if com_initialized:
                pythoncom.CoUninitialize()

    def _queue_progress(self, message: str) -> None:
        self.progress_queue.put(("log", message))

    def _queue_detail(self, message: str) -> None:
        self.progress_queue.put(("detail", message))

    def _process_progress(self) -> None:
        try:
            while True:
                event, value = self.progress_queue.get_nowait()
                if event == "log":
                    self._write_log(str(value))
                elif event == "detail":
                    self._write_detail(str(value))
                elif event == "finished":
                    self._finish_ui()
                    self.latest_output_path = Path(self.output_path.get().strip())
                    self.open_button.configure(state="normal")
                    self._write_log(f"Arquivo Excel gerado: {self.latest_output_path}")
                    self._write_log(f"Execução concluída: {value} email(ns) exportado(s).")
                    messagebox.showinfo("Extração concluída", f"{value} email(ns) exportado(s).")
                elif event == "cancelled":
                    self._finish_ui()
                    self._write_log("Execução encerrada pelo usuário.")
                elif event == "error":
                    self._finish_ui()
                    self._write_log(f"Execução encerrada com erro:\n{value}")
                    messagebox.showerror(
                        "Erro na extração",
                        f"A execução falhou. Consulte o log detalhado em:\n{self.log_file_path}",
                    )
                elif event == "update_status":
                    if value.update_available:
                        if messagebox.askyesno(
                            "Atualização disponível",
                            f"A versão {value.latest_version} está disponível. Deseja abrir a página de download?",
                        ):
                            webbrowser.open(value.release_url)
                elif event == "update_error":
                    self._write_log(f"Não foi possível verificar atualizações: {value}")
        except Empty:
            pass
        self.root.after(100, self._process_progress)

    def _cancel(self) -> None:
        if self.worker and self.worker.is_alive():
            self.stop_event.set()
            self.cancel_button.configure(state="disabled")
            self._write_log("Solicitação de encerramento recebida.")

    def _finish_ui(self) -> None:
        self.search_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")

    def _clear_log(self, output_path: Path) -> None:
        self.log_file_path = output_path.with_name(f"{output_path.stem}_log.txt")
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_file_path.write_text("", encoding="utf-8")
        self._write_detail("=== METADADOS DA EXECUÇÃO ===")
        self._write_detail(f"versao_aplicacao={PROJECT_VERSION}")
        for item in runtime_metadata():
            self._write_detail(item)
        self._write_detail(f"caixa={self.mailbox.get().strip()}")
        self._write_detail(f"pasta={self.folder_path.get().strip()}")
        self._write_detail(f"data_inicial={self._start_datetime().isoformat(sep=' ')}")
        self._write_detail(f"arquivo_saida={output_path.resolve()}")
        self._write_detail(f"assunto_filtro={self.subject.get().strip()!r}")
        self._write_detail("=== DETALHES DA LEITURA ===")
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def _open_latest(self) -> None:
        if self.latest_output_path and self.latest_output_path.exists():
            os.startfile(str(self.latest_output_path))
        else:
            self.open_button.configure(state="disabled")

    def _write_log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log.configure(state="normal")
        self.log.insert("end", f"[{timestamp}] {message}\n")
        self.log.see("end")
        self.log.configure(state="disabled")
        if self.log_file_path:
            with self.log_file_path.open("a", encoding="utf-8") as log_file:
                log_file.write(f"[{timestamp}] {message}\n")

    def _write_detail(self, message: str) -> None:
        if self.log_file_path:
            timestamp = datetime.now().strftime("%H:%M:%S")
            with self.log_file_path.open("a", encoding="utf-8") as log_file:
                log_file.write(f"[{timestamp}] {message}\n")


def start_app() -> None:
    com_initialized = False
    try:
        # Explicit initialization is required on some Office/Windows builds.
        import pythoncom

        pythoncom.CoInitialize()
        com_initialized = True
        root = tk.Tk()
        ExtractorWindow(root)
        root.mainloop()
    finally:
        if com_initialized:
            pythoncom.CoUninitialize()
