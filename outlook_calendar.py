import datetime
import os
import sys
import pythoncom
import win32com.client
from typing import List, Dict, Optional


_LOG_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(__file__)
_LOG_PATH = os.path.join(_LOG_DIR, "mscal_debug.log")


def _log(msg: str) -> None:
    try:
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now():%H:%M:%S} {msg}\n")
    except Exception:
        pass


class OutlookCalendarClient:
    """Client per leggere il calendario Outlook locale tramite COM."""

    OL_FOLDER_CALENDAR = 9

    def __init__(self):
        self.outlook = None
        self.namespace = None
        self.calendar = None

    def connect(self) -> None:
        """Avvia la connessione a Outlook e recupera la cartella Calendario."""
        try:
            self.outlook = win32com.client.dynamic.Dispatch(
                "Outlook.Application"
            )
        except Exception as e:
            raise ConnectionError(
                "Outlook non trovato.\n\n"
                "Microsoft Outlook non risulta installato o il componente "
                "COM non e' raggiungibile.\n"
                "Verifica che Outlook sia installato correttamente."
            ) from e

        try:
            self.namespace = self.outlook.GetNamespace("MAPI")
            self.calendar = self.namespace.GetDefaultFolder(
                self.OL_FOLDER_CALENDAR
            )
        except Exception as e:
            raise ConnectionError(
                "Impossibile accedere al calendario Outlook.\n\n"
                "Cause possibili:\n"
                "- Outlook non e' configurato con un profilo di posta\n"
                "- Il profilo Outlook non e' aperto\n"
                "- Il calendario non e' disponibile\n\n"
                f"Dettagli: {e}"
            ) from e

    def _to_datetime(self, value) -> Optional[datetime.datetime]:
        if value is None:
            return None
        if isinstance(value, datetime.datetime):
            if value.tzinfo is not None:
                return value.replace(tzinfo=None)
            return value
        if isinstance(value, datetime.date):
            return datetime.datetime.combine(value, datetime.time.min)
        tname = type(value).__name__
        try:
            epoch = datetime.datetime(1899, 12, 30)
            return epoch + datetime.timedelta(days=float(value))
        except (ValueError, TypeError, OverflowError):
            pass
        if hasattr(value, "timetuple"):
            try:
                tt = value.timetuple()
                dt = datetime.datetime(tt.tm_year, tt.tm_mon, tt.tm_mday,
                                       tt.tm_hour, tt.tm_min, tt.tm_sec)
                return dt
            except Exception:
                pass
        try:
            s = str(value).replace("Z", "").replace("+00:00", "").replace("-00:00", "")
            return datetime.datetime.fromisoformat(s)
        except Exception:
            pass
        _log(f"_to_datetime fallito per {tname} = {value!r}")
        return None

    def _outlook_date(self, value: datetime.datetime) -> str:
        return value.strftime("%m/%d/%Y %I:%M %p")

    def get_events(
        self, start_date: datetime.date, end_date: datetime.date
    ) -> List[Dict]:
        _log(
            f"get_events({start_date}, {end_date})  "
            f"weekday={start_date.weekday()}  today={datetime.date.today()}"
        )
        if self.calendar is None:
            self.connect()

        start_dt = datetime.datetime.combine(start_date, datetime.time.min)
        end_dt = datetime.datetime.combine(end_date, datetime.time.min)

        items = self.calendar.Items
        items.IncludeRecurrences = True
        items.Sort("[Start]")
        try:
            restriction = (
                f"[Start] < '{self._outlook_date(end_dt)}' "
                f"AND [End] > '{self._outlook_date(start_dt)}'"
            )
            items = items.Restrict(restriction)
            items.IncludeRecurrences = True
            items.Sort("[Start]")
            _log(f"Restrict applicato: {restriction}")
        except Exception as exc:
            _log(f"Restrict non disponibile, fallback su iterazione completa: {exc}")

        # Salta gli item il cui Start ha type=None (Count sentinella)
        events: List[Dict] = []
        processed = 0
        logged_types = set()

        for item in items:
            processed += 1
            if processed > 10000:
                break

            try:
                raw_start = item.Start
                t = type(raw_start).__name__
                if t not in logged_types:
                    _log(f"Item type(Start)={t}, value={raw_start!r:.100}")
                    logged_types.add(t)

                start = self._to_datetime(raw_start)
                if start is None:
                    continue
                if start >= end_dt:
                    break
                if start < start_dt:
                    end = self._to_datetime(item.End)
                    if end is None or end <= start_dt:
                        continue

                organizer = ""
                try:
                    organizer = item.Organizer
                except Exception:
                    pass
                is_all_day = False
                try:
                    is_all_day = bool(item.AllDayEvent)
                except Exception:
                    pass
                events.append({
                    "title": item.Subject or "(Senza titolo)",
                    "start": start,
                    "end": self._to_datetime(item.End),
                    "location": item.Location or "",
                    "organizer": organizer,
                    "is_recurring": bool(item.IsRecurring),
                    "is_all_day": is_all_day,
                })
            except Exception as exc:
                if "NoneType" not in str(exc):
                    _log(f"Event error: {exc}")
                continue

        events.sort(key=lambda e: e["start"] or datetime.datetime.max)
        _log(f"eventi raccolti = {len(events)}, processati = {processed}")
        for e in events[:3]:
            _log(f"  evento: {e['title']} @ {e['start']}")
        return events

    def get_events_threaded(
        self, start_date: datetime.date, end_date: datetime.date
    ) -> List[Dict]:
        pythoncom.CoInitialize()
        try:
            client = OutlookCalendarClient()
            client.connect()
            return client.get_events(start_date, end_date)
        finally:
            pythoncom.CoUninitialize()
