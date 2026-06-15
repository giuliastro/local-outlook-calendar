import datetime
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from outlook_calendar import OutlookCalendarClient
from calendar_widget import CalendarView


class CalendarApp:
    MONTHS = [
        "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
        "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre",
    ]

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Local Outlook Calendar")
        self.root.geometry("1100x680")
        self.root.minsize(800, 500)

        self.client = OutlookCalendarClient()
        self.current_date: datetime.date = datetime.date.today()
        self._events_cache: list = []
        self._load_generation = 0
        self._loading = False
        self._auto_after_id = None
        self._load_queue: queue.Queue = queue.Queue()
        self._poll_after_id = None

        self._build_ui()
        self._connect_and_load()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("vista")
        except Exception:
            try:
                style.theme_use("clam")
            except Exception:
                pass

        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=6, pady=5)

        ttk.Button(toolbar, text="< Prec", command=self._prev_week, width=8
                   ).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="Succ >", command=self._next_week, width=8
                   ).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="Oggi", command=self._go_today, width=6
                   ).pack(side=tk.LEFT, padx=(6, 1))
        ttk.Button(toolbar, text="Aggiorna", command=self._refresh, width=8
                   ).pack(side=tk.LEFT, padx=(6, 1))

        self.week_label = ttk.Label(toolbar, text="", font=("Segoe UI", 10, "bold"))
        self.week_label.pack(side=tk.LEFT, padx=(12, 4))

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=8
        )

        ttk.Label(toolbar, text="Cerca:").pack(side=tk.LEFT, padx=(0, 2))
        self.search_entry = ttk.Entry(toolbar, width=22)
        self.search_entry.pack(side=tk.LEFT, padx=1)
        self.search_entry.bind("<KeyRelease>", lambda e: self._apply_filter())
        self.search_entry.bind("<Return>", lambda e: self._apply_filter())
        ttk.Button(toolbar, text="Cerca", command=self._apply_filter, width=6
                   ).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="X", command=self._clear_search, width=2
                   ).pack(side=tk.LEFT)

        self.calendar = CalendarView(self.root)
        self.calendar.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 2))

        status = ttk.Frame(self.root)
        status.pack(fill=tk.X, padx=6, pady=(0, 3))
        self.status_label = ttk.Label(status, text="")
        self.status_label.pack(side=tk.LEFT)

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def _connect_and_load(self) -> None:
        self._load_events()

    def _get_monday(self, date: datetime.date) -> datetime.date:
        return date - datetime.timedelta(days=date.weekday())

    def _update_week_label(self, start: datetime.date, end: datetime.date) -> None:
        start_month = self.MONTHS[start.month - 1]
        end_month = self.MONTHS[end.month - 1]
        same_month = start.month == end.month and start.year == end.year
        if same_month:
            text = f"{start.day}-{end.day} {end_month} {end.year}"
        elif start.year == end.year:
            text = f"{start.day} {start_month} - {end.day} {end_month} {end.year}"
        else:
            text = (
                f"{start.day} {start_month} {start.year} - "
                f"{end.day} {end_month} {end.year}"
            )
        self.week_label.config(text=text)

    def _load_events(self) -> None:
        lun = self._get_monday(self.current_date)
        dom = lun + datetime.timedelta(days=6)
        start = lun
        end = dom + datetime.timedelta(days=1)
        self._update_week_label(lun, dom)

        self._loading = True
        self._load_generation += 1
        generation = self._load_generation
        self.status_label.config(text="Caricamento eventi da Outlook...")
        self.calendar.set_loading("Caricamento eventi...", lun)

        worker = threading.Thread(
            target=self._load_events_worker,
            args=(generation, start, end),
            daemon=True,
        )
        worker.start()
        self._schedule_load_poll()

    def _load_events_worker(
        self, generation: int, start: datetime.date, end: datetime.date
    ) -> None:
        try:
            events = self.client.get_events_threaded(start, end)
            self._load_queue.put((generation, events, None))
        except Exception as exc:
            self._load_queue.put((generation, [], exc))

    def _schedule_load_poll(self) -> None:
        if self._poll_after_id is None:
            self._poll_after_id = self.root.after(100, self._poll_load_results)

    def _poll_load_results(self) -> None:
        self._poll_after_id = None
        handled = False

        while True:
            try:
                generation, events, error = self._load_queue.get_nowait()
            except queue.Empty:
                break
            self._finish_load(generation, events, error)
            handled = True

        if self._loading or not handled:
            self._schedule_load_poll()

    def _finish_load(self, generation: int, events: list, error: Exception | None) -> None:
        if generation != self._load_generation:
            return

        self._loading = False

        if error:
            if isinstance(error, ConnectionError):
                title = "Errore di connessione"
            else:
                title = "Errore"
            messagebox.showerror(title, f"Impossibile caricare eventi:\n{error}")
            self.status_label.config(text="Caricamento fallito")
            self.calendar.set_events([], self._get_monday(self.current_date))
            return

        self._events_cache = events
        self._apply_filter()
        self._schedule_auto_refresh()

    def _schedule_auto_refresh(self) -> None:
        if self._auto_after_id is not None:
            self.root.after_cancel(self._auto_after_id)
        self._auto_after_id = self.root.after(60000, self._auto_refresh_tick)

    def _auto_refresh_tick(self) -> None:
        self._auto_after_id = None
        if self._loading:
            self._schedule_auto_refresh()
            return
        self.calendar.refresh_now_line()
        self._schedule_auto_refresh()

    def _apply_filter(self) -> None:
        if self._loading:
            self.status_label.config(text="Caricamento eventi da Outlook...")
            return

        search = self.search_entry.get().strip().lower()
        if search:
            filtered = [
                e for e in self._events_cache
                if search in e["title"].lower()
                or search in e["location"].lower()
            ]
        else:
            filtered = self._events_cache

        monday = self._get_monday(self.current_date)
        self.calendar.set_events(filtered, monday)

        n = len(filtered)
        if n == 0 and not search:
            msg = "Nessun evento in questa settimana"
        elif n == 0:
            msg = "Nessun risultato per la ricerca"
        else:
            msg = f"{n} evento{' trovato' if n == 1 else ' trovati'}"
        self.status_label.config(text=msg)

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def _prev_week(self) -> None:
        self.current_date -= datetime.timedelta(days=7)
        self._load_events()

    def _next_week(self) -> None:
        self.current_date += datetime.timedelta(days=7)
        self._load_events()

    def _go_today(self) -> None:
        self.current_date = datetime.date.today()
        self._load_events()

    def _refresh(self) -> None:
        self._load_events()

    def _clear_search(self) -> None:
        self.search_entry.delete(0, tk.END)
        self._apply_filter()
