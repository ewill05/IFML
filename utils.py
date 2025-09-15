# utils.py — multi-theme system + logo loader + DPI + observers
import os
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk

# Your logo should be at assets/logo.png
LOGO_PATH = os.path.join("assets", "logo.png")

# ──────────────────────────────────────────────────────────────────────────────
# Theme palettes
# ──────────────────────────────────────────────────────────────────────────────
_THEMES = {
    "Dark": {
        "bg":         "#111214",
        "fg":         "#EDEFF2",
        "sub":        "#1A1C20",
        "line":       "#2A2D34",
        "sel":        "#2C3430",
        "hdr":        "#20232A",
        "accent":     "#3AA981",
        "zebra_alt":  "#15171B",
        "archived_fg":"#9AA4AE",
        "missing_bg": "#3A2C2C",
    },
    "Light": {
        "bg":         "#FFFFFF",
        "fg":         "#1E2328",
        "sub":        "#F5F7FA",
        "line":       "#E2E6EA",
        "sel":        "#E7F3EE",
        "hdr":        "#F0F2F5",
        "accent":     "#5C7AEA",
        "zebra_alt":  "#FFFFFF",
        "archived_fg":"#6A7680",  # slightly stronger contrast
        "missing_bg": "#FFECE8",
    },
    "ISU": {  # Iowa State inspired (Cardinal & Gold)
        "bg":         "#FFFFFF",
        "fg":         "#231F20",
        "sub":        "#FFF8E6",
        "line":       "#F1BE48",
        "sel":        "#FFF0CC",
        "hdr":        "#C8102E",
        "accent":     "#C8102E",
        "zebra_alt":  "#FFFFFF",
        "archived_fg":"#6E5E58",  # slightly stronger contrast
        "missing_bg": "#FFE5E8",
    },
    "Forest": {
        "bg":         "#0F1A14",
        "fg":         "#E7F2EA",
        "sub":        "#15251C",
        "line":       "#254333",
        "sel":        "#193425",
        "hdr":        "#183126",
        "accent":     "#63B27A",
        "zebra_alt":  "#122219",
        "archived_fg":"#97A59E",
        "missing_bg": "#3B2D2A",
    },
    "Sand": {
        "bg":         "#FAF6EF",
        "fg":         "#2E2A21",
        "sub":        "#F2EBDC",
        "line":       "#E2D9C7",
        "sel":        "#E9E2D2",
        "hdr":        "#E5D9BF",
        "accent":     "#C59A5B",
        "zebra_alt":  "#FFFFFF",
        "archived_fg":"#7D7161",
        "missing_bg": "#F9E6DC",
    },
}

_CURRENT_THEME_NAME = "Dark"
_CURRENT_THEME = _THEMES[_CURRENT_THEME_NAME]
_THEME_LISTENERS: list[callable] = []  # callbacks fired when theme changes

# Public helpers
def get_available_themes() -> list[str]:
    return list(_THEMES.keys())

def get_current_theme_name() -> str:
    return _CURRENT_THEME_NAME

def get_palette() -> dict:
    return dict(_CURRENT_THEME)

def register_theme_listener(fn: callable):
    if fn not in _THEME_LISTENERS:
        _THEME_LISTENERS.append(fn)

def set_dpi_awareness(root: tk.Tk):
    try:
        root.tk.call('tk', 'scaling', 1.15)
    except Exception:
        pass

def load_logo(max_height: int = 150):
    try:
        if os.path.exists(LOGO_PATH):
            img = Image.open(LOGO_PATH)
            w, h = img.size
            if h <= 0:
                return None
            new_w = int(w * (max_height / h))
            img = img.resize((new_w, max_height), Image.LANCZOS)
            return ImageTk.PhotoImage(img)
    except Exception:
        return None
    return None

# Theme engine
def apply_theme(root: tk.Tk, mode: str = "Dark", accent: str | None = None):
    global _CURRENT_THEME_NAME, _CURRENT_THEME
    if mode not in _THEMES:
        mode = "Dark"
    _CURRENT_THEME_NAME = mode
    _CURRENT_THEME = dict(_THEMES[mode])
    if accent:
        _CURRENT_THEME["accent"] = accent

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    bg   = _CURRENT_THEME["bg"]
    fg   = _CURRENT_THEME["fg"]
    sub  = _CURRENT_THEME["sub"]
    line = _CURRENT_THEME["line"]
    sel  = _CURRENT_THEME["sel"]
    hdr  = _CURRENT_THEME["hdr"]
    ac   = _CURRENT_THEME["accent"]

    root.configure(bg=bg)

    style.configure(".", background=bg, foreground=fg, fieldbackground=sub)
    style.configure("TFrame", background=bg)
    style.configure("Card.TFrame", background=sub, relief="flat")
    style.configure("TLabel", background=bg, foreground=fg)
    style.configure("Muted.TLabel", foreground=_mix(fg, bg, 0.55), background=bg)
    style.configure("Strong.TLabel", font=("Segoe UI", 12, "bold"))
    style.configure("TSeparator", background=line)

    style.configure("TButton",
                    padding=(12, 8),
                    borderwidth=0,
                    focusthickness=1,
                    focuscolor=ac,
                    background=ac,
                    foreground="#FFFFFF")
    style.map("TButton",
              background=[("active", ac), ("pressed", ac)],
              relief=[("pressed", "sunken")])

    style.configure("TEntry", padding=8, relief="flat", borderwidth=1)
    style.map("TEntry", focuscolor=[("focus", ac)])
    style.configure("TCombobox", padding=6, relief="flat", borderwidth=1)
    style.map("TCombobox", focuscolor=[("focus", ac)])

    style.configure("TNotebook", tabposition="n", background=bg, borderwidth=0)
    style.configure("TNotebook.Tab",
                    padding=(18, 10),
                    background=hdr,
                    foreground=_best_text(hdr, fg, bg))
    style.map("TNotebook.Tab",
              background=[("selected", sub)],
              foreground=[("selected", fg)])

    style.configure("Treeview",
                    background=sub,
                    fieldbackground=sub,
                    foreground=fg,
                    rowheight=28,
                    borderwidth=0)
    style.configure("Treeview.Heading",
                    background=hdr,
                    foreground=_best_text(hdr, fg, bg),
                    relief="flat",
                    padding=(8, 6))
    style.map("Treeview",
              background=[("selected", sel)],
              foreground=[("selected", fg)])

    # notify listeners (tabs can re-style row tags)
    for fn in list(_THEME_LISTENERS):
        try:
            fn()
        except Exception:
            pass

def set_theme(root: tk.Tk, name: str):
    apply_theme(root, mode=name)

def _best_text(bg_color: str, light_text: str, dark_text: str) -> str:
    try:
        r, g, b = _hex_to_rgb(bg_color)
        lum = 0.2126*r + 0.7152*g + 0.0722*b
        return light_text if lum < 140 else dark_text
    except Exception:
        return light_text

def _hex_to_rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def _mix(fg: str, bg: str, t: float) -> str:
    fr, fg_, fb = _hex_to_rgb(fg)
    br, bg_, bb = _hex_to_rgb(bg)
    r = int(br + (fr - br) * t)
    g = int(bg_ + (fg_ - bg_) * t)
    b = int(bb + (fb - bb) * t)
    return f"#{r:02X}{g:02X}{b:02X}"

# Convenience for theme-adaptive row tags
def style_row_tags_for_treeview(tree: ttk.Treeview):
    pal = get_palette()
    tree.tag_configure("zebra_even", background=pal["zebra_alt"])
    tree.tag_configure("archived", foreground=pal["archived_fg"])
    tree.tag_configure("missing", background=pal["missing_bg"])
