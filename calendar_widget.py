import datetime
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
from typing import List, Dict, Optional, Tuple


class CalendarView(tk.Frame):
    DAY_HEADER_H = 56
    ALL_DAY_ROW_H = 18
    ALL_DAY_MAX_ROWS = 2
    HEADER_H = DAY_HEADER_H + ALL_DAY_ROW_H * ALL_DAY_MAX_ROWS + 8
    TIME_W = 52
    HOUR_H = 66
    WORK_START = 8
    WORK_END = 18
    COLORS = [
        "#1A73E8", "#7B1FA2", "#E8710A", "#0D8043", "#C5221F",
        "#4285F4", "#34A853", "#FBBC04", "#FF6D01", "#00ACC1",
        "#8E24AA", "#43A047", "#5C6BC0", "#EC407A",
    ]

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self._events: List[Dict] = []
        self._monday: Optional[datetime.date] = None
        self._day_w = 120
        self._today = datetime.date.today()
        self._first_render = True
        self._tooltip_win: Optional[tk.Toplevel] = None
        self._hovered_ev: Optional[int] = None
        self._fonts: Dict = {}
        self._loading_message = ""
        self._build()

    def _build(self) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        hf = tk.Frame(self, height=self.HEADER_H, bg="#F8F9FA")
        hf.grid(row=0, column=0, sticky="ew")
        hf.grid_propagate(False)
        self.header_canvas = tk.Canvas(
            hf, height=self.HEADER_H, bg="#F8F9FA", highlightthickness=0
        )
        self.header_canvas.pack(fill=tk.BOTH, expand=True)

        body = tk.Frame(self)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(body, bg="#FFFFFF", highlightthickness=0)
        scroll = ttk.Scrollbar(body, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scroll.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")

        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-3, "units"))
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(3, "units"))
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Leave>", self._hide_tooltip)
        self.header_canvas.bind("<Motion>", self._on_header_motion)
        self.header_canvas.bind("<Leave>", self._hide_tooltip)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_events(self, events: List[Dict], monday: datetime.date) -> None:
        self._events = events
        self._monday = monday
        self._today = datetime.date.today()
        self._first_render = True
        self._loading_message = ""
        self._render()

    def set_loading(self, message: str, monday: datetime.date) -> None:
        self._events = []
        self._monday = monday
        self._today = datetime.date.today()
        self._first_render = True
        self._loading_message = message
        self._render()

    def refresh_now_line(self) -> None:
        self.canvas.delete("now")
        cw = self.canvas.winfo_width()
        if cw > 50:
            self._draw_now(cw)

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _on_mousewheel(self, event: tk.Event) -> None:
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_resize(self, _=None) -> None:
        if self._monday:
            cw = self.canvas.winfo_width()
            if cw > 50:
                self.header_canvas.configure(width=cw)
            self._render()

    def _on_motion(self, event: tk.Event) -> None:
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        found = self.canvas.find_closest(cx, cy)
        if not found:
            return
        item = found[0]
        self._handle_hover(self.canvas, item, event)

    def _on_header_motion(self, event: tk.Event) -> None:
        found = self.header_canvas.find_closest(event.x, event.y)
        if not found:
            return
        self._handle_hover(self.header_canvas, found[0], event)

    def _handle_hover(self, canvas: tk.Canvas, item: int, event: tk.Event) -> None:
        current = canvas.find_withtag("current")
        if item not in current:
            item = current[0] if current else item
        tags = canvas.gettags(item)
        ev_idx = None
        for t in tags:
            if t.startswith("ev_"):
                try:
                    ev_idx = int(t[3:])
                except ValueError:
                    pass
                break
        if ev_idx is not None and ev_idx != self._hovered_ev:
            self._hovered_ev = ev_idx
            self._show_tooltip(event, ev_idx)
        elif ev_idx is None and self._hovered_ev is not None:
            self._hovered_ev = None
            self._hide_tooltip()

    def _show_tooltip(self, event: tk.Event, ev_idx: int) -> None:
        self._hide_tooltip()
        ev = self._events[ev_idx]
        if not ev:
            return

        win = tk.Toplevel(self.canvas)
        win.wm_overrideredirect(True)
        win.wm_geometry(f"+{event.x_root + 12}+{event.y_root + 8}")
        win.configure(bg="#FFFFFF", bd=0)
        win.attributes("-topmost", True)

        frame = tk.Frame(win, bg="#FFFFFF", bd=1, relief=tk.SOLID,
                         highlightbackground="#DADCE0", highlightthickness=1)
        frame.pack()

        title = ev.get("title", "").strip()
        ts = ev["start"].strftime("%H:%M") if ev.get("start") else ""
        te = ev["end"].strftime("%H:%M") if ev.get("end") else ""
        time_s = f"{ts} - {te}" if ts and te else ts or te or ""
        org = ev.get("organizer", "").strip()

        tk.Label(frame, text=title, bg="#FFFFFF", font=("Segoe UI", 9, "bold"),
                 fg="#3C4043", wraplength=280, anchor="w", justify="left"
                 ).pack(fill=tk.X, padx=8, pady=(6, 0))

        if time_s:
            tk.Label(frame, text=time_s, bg="#FFFFFF", font=("Segoe UI", 9),
                     fg="#70757A", anchor="w"
                     ).pack(fill=tk.X, padx=8, pady=(1, 0))

        if org:
            tk.Label(frame, text=f"Organizzatore: {org}", bg="#FFFFFF",
                     font=("Segoe UI", 8), fg="#70757A", anchor="w"
                     ).pack(fill=tk.X, padx=8, pady=(0, 4))

        self._tooltip_win = win

    def _hide_tooltip(self, _=None) -> None:
        if self._tooltip_win:
            self._tooltip_win.destroy()
            self._tooltip_win = None

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def _render(self) -> None:
        cw = self.canvas.winfo_width()
        if cw < 80:
            return

        dw = max(110, (cw - self.TIME_W) / 7)
        self._day_w = dw
        th = 24 * self.HOUR_H + 4

        self.canvas.delete("all")
        self.canvas.configure(scrollregion=(0, 0, cw, th))
        self._hovered_ev = None
        self._hide_tooltip()

        self._draw_header(cw, dw)
        self._draw_body_grid(cw, dw)
        if self._loading_message:
            self._draw_loading(cw)
        else:
            self._draw_events(cw, dw)
            self._draw_now(cw)

        if self._first_render:
            self._first_render = False
            target_y = self.WORK_START * self.HOUR_H
            vh = max(100, self.canvas.winfo_height())
            target_y = max(0, target_y - vh * 0.10)
            self.canvas.yview_moveto(target_y / th)

    def _draw_loading(self, cw: float) -> None:
        vh = max(160, self.canvas.winfo_height())
        y = self.canvas.canvasy(0) + min(vh * 0.42, 420)
        self.canvas.create_text(
            cw / 2, y,
            text=self._loading_message,
            font=("Segoe UI", 12, "bold"),
            fill="#3C4043",
            anchor="center",
            tags="loading",
        )

    # ------------------------------------------------------------------
    # Header (fixed, outside scroll)
    # ------------------------------------------------------------------

    def _draw_header(self, cw: float, dw: float) -> None:
        hc = self.header_canvas
        hc.delete("all")

        today_idx = -1
        if self._monday:
            for i in range(7):
                if self._monday + datetime.timedelta(days=i) == self._today:
                    today_idx = i
                    break

        labels = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
        for i in range(7):
            x = self.TIME_W + i * dw
            d = (self._monday + datetime.timedelta(days=i)) if self._monday else None
            is_today = i == today_idx
            bg = "#EBF3FE" if is_today else "#F8F9FA"

            hc.create_rectangle(
                x, 0, x + dw, self.DAY_HEADER_H, fill=bg, outline="#DADCE0"
            )
            hc.create_text(
                x + dw / 2, 8, text=labels[i].upper(),
                font=("Segoe UI", 9),
                fill="#1A73E8" if is_today else "#70757A", anchor="n",
            )
            if d:
                if is_today:
                    cx, cy = x + dw / 2, 37
                    hc.create_oval(
                        cx - 15, cy - 15, cx + 15, cy + 15,
                        fill="#1A73E8", outline=""
                    )
                    hc.create_text(
                        cx, cy, text=str(d.day),
                        font=("Segoe UI", 10, "bold"), fill="white",
                    )
                else:
                    hc.create_text(
                        x + dw / 2, 37, text=str(d.day),
                        font=("Segoe UI", 10), fill="#3C4043", anchor="center",
                    )

        hc.create_rectangle(
            0, self.DAY_HEADER_H, cw, self.HEADER_H,
            fill="#FFFFFF", outline="#DADCE0",
        )
        hc.create_text(
            self.TIME_W - 6, self.DAY_HEADER_H + 13,
            text="Giorno",
            font=("Segoe UI", 7),
            fill="#70757A",
            anchor="e",
        )
        self._draw_all_day_header(cw, dw)

        for i in range(8):
            xx = self.TIME_W + i * dw if i < 7 else cw
            hc.create_line(xx, 0, xx, self.HEADER_H, fill="#DADCE0")
        hc.create_line(0, self.DAY_HEADER_H, cw, self.DAY_HEADER_H, fill="#DADCE0")

    # ------------------------------------------------------------------
    # Body grid
    # ------------------------------------------------------------------

    def _draw_body_grid(self, cw: float, dw: float) -> None:
        today_idx = -1
        if self._monday:
            for i in range(7):
                if self._monday + datetime.timedelta(days=i) == self._today:
                    today_idx = i
                    break

        for i in range(7):
            x = self.TIME_W + i * dw
            day = self._monday + datetime.timedelta(days=i) if self._monday else None
            fill = ""
            if i == today_idx:
                fill = "#F2F6FC"
            elif day and day.weekday() >= 5:
                fill = "#FAFAFA"
            if fill:
                self.canvas.create_rectangle(
                    x, 0, x + dw, 24 * self.HOUR_H + 4,
                    fill=fill, outline="", tags="day_bg"
                )

        for y1, y2 in ((0, self.WORK_START * self.HOUR_H),
                       (self.WORK_END * self.HOUR_H, 24 * self.HOUR_H + 4)):
            if y2 <= y1:
                continue
            self.canvas.create_rectangle(
                self.TIME_W, y1, cw, y2,
                fill="#FBFBFB", outline="", stipple="gray25", tags="off_hours"
            )

        for h in range(24):
            y = h * self.HOUR_H
            if h > 0:
                self.canvas.create_text(
                    self.TIME_W - 6, y, text=f"{h:02d}:00",
                    font=("Segoe UI", 9), fill="#70757A", anchor="e",
                )
            shade = "#E8EAED" if h % 2 == 0 else "#F1F3F4"
            self.canvas.create_line(0, y, cw, y, fill=shade)
            if h == self.WORK_START or h == self.WORK_END:
                self.canvas.create_line(self.TIME_W, y, cw, y, fill="#DADCE0", width=2)

        for i in range(8):
            x = self.TIME_W + i * dw if i < 7 else cw
            self.canvas.create_line(x, 0, x, 24 * self.HOUR_H + 4, fill="#E8EAED")

    # ------------------------------------------------------------------
    # Current time line
    # ------------------------------------------------------------------

    def _draw_now(self, cw: float) -> None:
        if not self._monday:
            return
        now = datetime.datetime.now()
        if not (self._monday <= now.date() < self._monday + datetime.timedelta(days=7)):
            return
        minutes = now.hour * 60 + now.minute
        y = (minutes / 60) * self.HOUR_H
        self.canvas.create_line(self.TIME_W, y, cw, y, fill="#EA4335", width=2, tags="now")
        self.canvas.create_oval(
            self.TIME_W - 5, y - 5, self.TIME_W + 5, y + 5,
            fill="#EA4335", outline="white", width=2, tags="now",
        )
        self.canvas.create_text(
            self.TIME_W - 7, y, text=now.strftime("%H:%M"),
            font=("Segoe UI", 8, "bold"), fill="#EA4335", anchor="e", tags="now",
        )

    # ------------------------------------------------------------------
    # All-day events (fixed in header)
    # ------------------------------------------------------------------

    def _draw_all_day_header(self, cw: float, dw: float) -> None:
        hc = self.header_canvas
        by_day: Dict[int, List] = {i: [] for i in range(7)}
        for ev_idx, ev in enumerate(self._events):
            if self._is_all_day(ev):
                for idx in self._all_day_indices(ev):
                    by_day[idx].append((ev_idx, ev))

        for idx, evs in by_day.items():
            if not evs:
                continue
            x = self.TIME_W + idx * dw
            visible_count = self.ALL_DAY_MAX_ROWS
            if len(evs) > self.ALL_DAY_MAX_ROWS:
                visible_count -= 1
            visible = evs[:visible_count]
            for j, (ev_idx, ev) in enumerate(visible):
                y = self.DAY_HEADER_H + 4 + j * self.ALL_DAY_ROW_H
                c = self._event_color(ev)
                tags = ("ev", f"ev_{ev_idx}")
                hc.create_rectangle(
                    x + 3, y, x + dw - 3, y + self.ALL_DAY_ROW_H - 3,
                    fill=self._alpha(c, 0.15), outline=c, width=0.5, tags=tags,
                )
                aw = max(8, dw - 10)
                f = self._get_font(8, "bold")
                txt = self._truncated(ev.get("title", ""), f, aw)
                hc.create_text(
                    x + 7, y + 7, text=txt,
                    font=f, fill=c, anchor="w", tags=tags,
                )

            hidden = len(evs) - len(visible)
            if hidden > 0:
                y = self.DAY_HEADER_H + 4 + (self.ALL_DAY_MAX_ROWS - 1) * self.ALL_DAY_ROW_H
                hc.create_rectangle(
                    x + 3, y, x + dw - 3, y + self.ALL_DAY_ROW_H - 3,
                    fill="#F1F3F4", outline="#DADCE0", width=0.5,
                )
                hc.create_text(
                    x + 7, y + 7, text=f"+{hidden} altri",
                    font=self._get_font(8), fill="#5F6368", anchor="w",
                )

    def _all_day_indices(self, ev: Dict) -> List[int]:
        if not self._monday:
            return []
        s, e = ev.get("start"), ev.get("end")
        if not s or not e:
            return []

        start_idx = (s.date() - self._monday).days
        if e.time() == datetime.time.min and e.date() > s.date():
            end_date = e.date() - datetime.timedelta(days=1)
        else:
            end_date = e.date()
        end_idx = (end_date - self._monday).days

        start_idx = max(0, start_idx)
        end_idx = min(6, end_idx)
        if end_idx < start_idx:
            return []
        return list(range(start_idx, end_idx + 1))

    def _is_all_day(self, ev: Dict) -> bool:
        s, e = ev.get("start"), ev.get("end")
        if not s or not e:
            return False
        if ev.get("is_all_day"):
            return True
        if (e - s).total_seconds() >= 82800:
            return True
        return False

    # ------------------------------------------------------------------
    # Timed events with overlapping layout
    # ------------------------------------------------------------------

    def _draw_events(self, cw: float, dw: float) -> None:
        if not self._monday:
            return

        per_day: List[List] = [[] for _ in range(7)]

        for ev_idx, ev in enumerate(self._events):
            if self._is_all_day(ev):
                continue
            s, e = ev.get("start"), ev.get("end")
            if not s or not e:
                continue
            for idx in range(7):
                day = datetime.datetime.combine(
                    self._monday + datetime.timedelta(days=idx), datetime.time.min
                )
                day_end = day + datetime.timedelta(days=1)
                if s >= day_end or e <= day:
                    continue
                ms = 0 if s < day else (s.hour * 60 + s.minute)
                me = 24 * 60 if e > day_end else (e.hour * 60 + e.minute)
                per_day[idx].append((ms, me, ev_idx))

        for idx in range(7):
            if not per_day[idx]:
                continue
            per_day[idx].sort(key=lambda x: (x[0], x[1]))

            for group in self._overlap_groups(per_day[idx]):
                assignments = self._assign_columns(group)
                total_cols = max((col for _ev_idx, col, _ms, _me in assignments), default=0) + 1
                for ev_idx, col, ms, me in assignments:
                    ev = self._events[ev_idx]
                    self._draw_event_block(ev, ev_idx, idx, dw, ms, me, col, total_cols)

    def _overlap_groups(self, items: List[Tuple[int, int, int]]) -> List[List[Tuple[int, int, int]]]:
        groups: List[List[Tuple[int, int, int]]] = []
        current: List[Tuple[int, int, int]] = []
        current_end = -1

        for ms, me, ev_idx in items:
            if not current or ms < current_end:
                current.append((ms, me, ev_idx))
                current_end = max(current_end, me)
            else:
                groups.append(current)
                current = [(ms, me, ev_idx)]
                current_end = me

        if current:
            groups.append(current)
        return groups

    def _assign_columns(
        self, group: List[Tuple[int, int, int]]
    ) -> List[Tuple[int, int, int, int]]:
        columns: List[List[Tuple[int, int]]] = []
        assignments: List[Tuple[int, int, int, int]] = []

        for ms, me, ev_idx in group:
            col = 0
            while col < len(columns):
                free = all(ms >= cme or me <= cms for cms, cme in columns[col])
                if free:
                    break
                col += 1
            if col >= len(columns):
                columns.append([])
            columns[col].append((ms, me))
            assignments.append((ev_idx, col, ms, me))

        return assignments

    def _draw_event_block(self, ev: Dict, ev_idx: int, idx: int, dw: float,
                          ms: int, me: int, col: int, total_cols: int) -> None:
        base_x = self.TIME_W + idx * dw
        col_w = dw / total_cols
        x = base_x + col * col_w

        top = (ms / 60) * self.HOUR_H
        ht = max(12, ((me - ms) / 60) * self.HOUR_H - 1)
        color = self._event_color(ev)
        p, bw = 1, 4
        tags = ("ev", f"ev_{ev_idx}")

        self.canvas.create_rectangle(
            x + p, top + p, x + p + bw, top + ht - p,
            fill=color, outline="", tags=tags,
        )
        self.canvas.create_rectangle(
            x + p + bw, top + p, x + col_w - p, top + ht - p,
            fill="#FFFFFF", outline="#DADCE0", width=0.5, tags=tags,
        )

        tw = max(4, col_w - p - bw - 10)
        th = ht - p * 2 - 4

        title = ev.get("title", "").strip()
        if th >= 18:
            f = self._get_font(8, "bold")
            text_y = top + p + 2
            title_h = th
            if th >= 32:
                time_f = self._get_font(7)
                self.canvas.create_text(
                    x + p + bw + 3, text_y,
                    text=self._event_time_text(ev),
                    font=time_f, fill="#70757A", anchor="nw", width=tw, tags=tags,
                )
                time_h = max(11, time_f.metrics("linespace") - 1)
                text_y += time_h
                title_h = max(8, th - time_h)

            txt = self._fit_text_block(title, f, tw, title_h)
            self.canvas.create_text(
                x + p + bw + 3, text_y, text=txt,
                font=f, fill="#3C4043", anchor="nw", width=tw, tags=tags,
            )

    def _get_font(self, size: int, weight: str = "normal") -> tkfont.Font:
        key = (size, weight)
        if key not in self._fonts:
            self._fonts[key] = tkfont.Font(family="Segoe UI", size=size, weight=weight)
        return self._fonts[key]

    def _truncated(self, text: str, font: tkfont.Font, max_w: float) -> str:
        if not text:
            return ""
        if font.measure(text) <= max_w:
            return text
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if font.measure(text[:mid] + "\u2026") <= max_w:
                lo = mid
            else:
                hi = mid - 1
        return text[:lo] + "\u2026"

    def _ellipsized(self, text: str, font: tkfont.Font, max_w: float) -> str:
        if font.measure(text + "\u2026") <= max_w:
            return text + "\u2026"
        return self._truncated(text, font, max_w)

    def _fit_text_block(
        self, text: str, font: tkfont.Font, max_w: float, max_h: float
    ) -> str:
        text = " ".join((text or "").split())
        if not text or max_w <= 4 or max_h <= 8:
            return ""

        line_h = max(1, font.metrics("linespace"))
        max_lines = max(1, int(max_h // line_h))
        words = text.split(" ")
        lines: List[str] = []
        current = ""

        for word in words:
            candidate = word if not current else f"{current} {word}"
            if font.measure(candidate) <= max_w:
                current = candidate
                continue

            if current:
                lines.append(current)
                current = word
            else:
                lines.append(self._truncated(word, font, max_w))
                current = ""

            if len(lines) >= max_lines:
                break

        if current and len(lines) < max_lines:
            lines.append(current)

        if not lines:
            return ""

        used_text = " ".join(lines)
        if len(used_text) < len(text) or len(lines) > max_lines:
            lines = lines[:max_lines]
            lines[-1] = self._ellipsized(lines[-1], font, max_w)

        return "\n".join(lines[:max_lines])

    def _event_time_text(self, ev: Dict) -> str:
        s, e = ev.get("start"), ev.get("end")
        if not s or not e:
            return ""
        return f"{s:%H:%M}-{e:%H:%M}"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _event_color(self, ev: Dict) -> str:
        idx = hash(ev.get("title", "")) % len(self.COLORS)
        return self.COLORS[idx]

    def _alpha(self, hex_color: str, alpha: float) -> str:
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        ar = int(255 + (r - 255) * alpha)
        ag = int(255 + (g - 255) * alpha)
        ab = int(255 + (b - 255) * alpha)
        return f"#{ar:02x}{ag:02x}{ab:02x}"
