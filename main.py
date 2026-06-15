import sys
import os

# Assicura che pywin32 trovi i binding giusti
if hasattr(sys, "frozen"):
    os.environ["PYWIN32_COM_EXCEPTION_AS_ERROR"] = "1"

import tkinter as tk
from ui import CalendarApp


def main() -> None:
    root = tk.Tk()
    root.option_add("*Font", "{Segoe UI} 10")
    app = CalendarApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
