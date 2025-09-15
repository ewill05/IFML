import tkinter as tk
from tkinter import ttk, messagebox

from utils import (
    apply_theme, set_theme, set_dpi_awareness, load_logo,
    get_available_themes, get_current_theme_name
)

try:
    from logger_tab import build_logger_tab
except Exception:
    def build_logger_tab(notebook: ttk.Notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="\ud83d\udcf7 Logger")
        ttk.Label(frame, text="pandas is required for the Logger tab").pack(padx=10, pady=10)

try:
    from species_db import build_species_db_tab
except Exception:
    def build_species_db_tab(notebook: ttk.Notebook, default_path: str = ""):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="\ud83c\udf33 Species DB")
        ttk.Label(frame, text="pandas is required for the Species DB tab").pack(padx=10, pady=10)

try:
    from audit_tab import build_audit_tab
except Exception:
    def build_audit_tab(notebook: ttk.Notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="\ud83d\udcca Audit")
        ttk.Label(frame, text="pandas is required for the Audit tab").pack(padx=10, pady=10)

APP_NAME = "IFML – TimberView"

def build_header(container: ttk.Frame):
    header = ttk.Frame(container)
    header.pack(side="top", fill="x", pady=(6, 0))

    logo_img = load_logo(max_height=150)
    if logo_img:
        lbl = ttk.Label(header, image=logo_img)
        lbl.image = logo_img
        lbl.pack(side="top", pady=(10, 6))
    else:
        ttk.Label(header, text=APP_NAME, font=("Segoe UI", 22, "bold")).pack(
            side="top", pady=(10, 6)
        )

    ttk.Separator(container, orient="horizontal").pack(fill="x", padx=8, pady=(6, 10))

def build_footer(container: ttk.Frame):
    footer = ttk.Frame(container)
    footer.pack(side="bottom", fill="x")
    ttk.Separator(footer, orient="horizontal").pack(fill="x", padx=8, pady=(6, 6))
    ttk.Label(footer, text="Created by Eli Willard V2.1A", style="Muted.TLabel").pack(
        side="bottom", pady=(0, 10)
    )

def build_theme_menu(root: tk.Tk, menubar: tk.Menu):
    themes = get_available_themes()
    theme_menu = tk.Menu(menubar, tearoff=False)
    menubar.add_cascade(label="Theme", menu=theme_menu)

    current = tk.StringVar(value=get_current_theme_name())

    def on_change(name: str):
        current.set(name)
        set_theme(root, name)

    for name in themes:
        theme_menu.add_radiobutton(
            label=name,
            value=name,
            variable=current,
            command=lambda n=name: on_change(n)
        )

def main() -> int:
    try:
        root = tk.Tk()
    except tk.TclError as e:
        print(f"Tkinter failed to initialize: {e}")
        return 1
    root.title(APP_NAME)
    root.geometry("1220x780")
    root.minsize(1060, 640)

    set_dpi_awareness(root)
    apply_theme(root, mode="Dark")  # startup theme

    shell = ttk.Frame(root); shell.pack(fill="both", expand=True)
    build_header(shell)

    content = ttk.Frame(shell, style="Card.TFrame", padding=10)
    content.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    nb = ttk.Notebook(content); nb.pack(fill="both", expand=True)

    build_logger_tab(nb)
    build_species_db_tab(nb)
    build_audit_tab(nb)

    build_footer(shell)

    menubar = tk.Menu(root); root.config(menu=menubar)
    filem = tk.Menu(menubar, tearoff=False); menubar.add_cascade(label="File", menu=filem)
    filem.add_command(label="Quit", command=root.destroy)
    helpm = tk.Menu(menubar, tearoff=False); menubar.add_cascade(label="Help", menu=helpm)
    helpm.add_command(label="About", command=lambda: messagebox.showinfo("About", APP_NAME))
    build_theme_menu(root, menubar)

    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
