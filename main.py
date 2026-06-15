import sys
import os

# Assicura che pywin32 trovi i binding giusti
if hasattr(sys, "frozen"):
    os.environ["PYWIN32_COM_EXCEPTION_AS_ERROR"] = "1"

import tkinter as tk
from ui import CalendarApp


def asset_path(relative_path: str) -> str:
    base_dir = getattr(sys, "_MEIPASS", os.path.dirname(__file__))
    return os.path.join(base_dir, relative_path)


def set_app_icon(root: tk.Tk) -> None:
    try:
        icon = tk.PhotoImage(file=asset_path(os.path.join("assets", "icon.png")))
        root.iconphoto(True, icon)
        root._app_icon = icon
    except Exception:
        pass


def main() -> None:
    root = tk.Tk()
    root.option_add("*Font", "{Segoe UI} 10")
    set_app_icon(root)
    app = CalendarApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
