# species_db.py (stable build)
# Requires: pandas, openpyxl (for .xlsx)

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
from shared_config import set_db_path  # <-- saves chosen path for the logger

DISPLAY_ORDER = ["Genus", "Species", "Common Name", "Family"]
HEADER_ALIASES = {
    "genus": "Genus",
    "species": "Species",
    "commonname": "Common Name",
    "common_name": "Common Name",
    "family": "Family",
}

def _normalize_headers(df: pd.DataFrame) -> pd.DataFrame:
    ren = {}
    for col in df.columns:
        key = col.strip().lower().replace(" ", "").replace("_", "")
        ren[col] = HEADER_ALIASES.get(key, col.strip())
    return df.rename(columns=ren)

def _ensure_columns(df: pd.DataFrame, columns):
    for c in columns:
        if c not in df.columns:
            df[c] = ""
    return df

def _read_any(path: str) -> pd.DataFrame:
    if path.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(path, dtype=str)
    return pd.read_csv(path, dtype=str)

def _write_any(df: pd.DataFrame, path: str):
    if path.lower().endswith((".xlsx", ".xls")):
        df.to_excel(path, index=False)
    else:
        df.to_csv(path, index=False)

class SpeciesDBController:
    def __init__(self, tree: ttk.Treeview, status_var: tk.StringVar, nofile_label: ttk.Label):
        self.tree = tree
        self.status_var = status_var
        self.nofile_label = nofile_label
        self.file_path = ""
        self.df_full = pd.DataFrame()
        self.df_view = pd.DataFrame()

        # Preconfigure columns so UI is never blank
        self.tree["columns"] = DISPLAY_ORDER
        self.tree["show"] = "headings"
        widths = {"Genus": 160, "Species": 160, "Common Name": 240, "Family": 180}
        for col in DISPLAY_ORDER:
            self.tree.heading(col, text=col, anchor="w")
            self.tree.column(col, width=widths.get(col, 140), anchor="w", stretch=True)

    # ---------- File ops ----------
    def select_file(self):
        path = filedialog.askopenfilename(
            title="Select Species Database (.xlsx or .csv)",
            filetypes=[("Excel/CSV", "*.xlsx;*.xls;*.csv"), ("All files", "*.*")]
        )
        if not path:
            return
        self.load_from_path(path)

    def load_from_path(self, path: str):
        try:
            df = _read_any(path)
            df = _normalize_headers(df)
            df = _ensure_columns(df, DISPLAY_ORDER)
            self.df_full = df.fillna("")
            self.file_path = path
            set_db_path(self.file_path)  # <-- share with logger (confirmed present before) :contentReference[oaicite:1]{index=1}
            self._refresh_view_table()
            self._set_status(f"Loaded: {os.path.basename(path)}  |  {len(self.df_full)} rows")
            self._show_nofile(False)
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load file:\n{e}")
            self._show_nofile(True)

    # ---------- Table ops ----------
    def _refresh_view_table(self, filtered_df: pd.DataFrame = None):
        df = filtered_df if filtered_df is not None else self.df_full
        self.df_view = df[DISPLAY_ORDER].copy() if not df.empty else pd.DataFrame(columns=DISPLAY_ORDER)

        self.tree.delete(*self.tree.get_children())
        for _, row in self.df_view.iterrows():
            self.tree.insert("", "end", values=[row.get(c, "") for c in DISPLAY_ORDER])

        if self.file_path and self.df_view.empty:
            self._set_status("File loaded but no rows found.")

    # ---------- Search ----------
    def filter_rows(self, q: str):
        q = (q or "").strip().lower()
        if not self.file_path:
            self._set_status("Open a database file to search.")
            return
        if not q:
            self._refresh_view_table(self.df_full)
            self._set_status(f"{len(self.df_full)} rows")
            return
        mask = pd.Series(False, index=self.df_full.index)
        for col in DISPLAY_ORDER:
            mask |= self.df_full[col].fillna("").str.lower().str.contains(q)
        filt = self.df_full[mask]
        self._refresh_view_table(filt)
        self._set_status(f"{len(filt)} matching rows")

    # ---------- Add row ----------
    def add_species(self, genus: str, species: str, common: str, family: str):
        if not self.file_path:
            messagebox.showwarning("No File", "Load or choose a database file first.")
            return
        genus = (genus or "").strip()
        species = (species or "").strip()
        common = (common or "").strip()
        family = (family or "").strip()

        if not genus or not species:
            messagebox.showwarning("Missing Data", "Genus and Species are required.")
            return

        new_row = {c: "" for c in (self.df_full.columns if not self.df_full.empty else DISPLAY_ORDER)}
        new_row["Genus"] = genus
        new_row["Species"] = species
        new_row["Common Name"] = common
        new_row["Family"] = family

        if self.df_full.empty:
            self.df_full = pd.DataFrame(columns=DISPLAY_ORDER)

        self.df_full = pd.concat([self.df_full, pd.DataFrame([new_row])], ignore_index=True)

        try:
            _write_any(self.df_full, self.file_path)
            # keep shared path fresh in case user created/moved the file externally
            set_db_path(self.file_path)
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not write to file:\n{e}")
            return

        self._refresh_view_table()
        self._set_status(f"Added {genus} {species}. Total {len(self.df_full)} rows.")

    def _set_status(self, txt: str):
        if self.status_var is not None:
            self.status_var.set(txt)

    def _show_nofile(self, show: bool):
        if show:
            self.nofile_label.place(relx=0.5, rely=0.5, anchor="center")
        else:
            self.nofile_label.place_forget()

# ---------------- UI Builder ----------------
def build_species_db_tab(notebook: ttk.Notebook, default_path: str = ""):
    parent = ttk.Frame(notebook)
    notebook.add(parent, text="Species DB")

    status_var = tk.StringVar(value="Ready")
    status_bar = ttk.Label(parent, textvariable=status_var, anchor="w")
    status_bar.pack(side="bottom", fill="x")

    sub = ttk.Notebook(parent)
    sub.pack(side="top", fill="both", expand=True, padx=8, pady=8)

    # -------- View Tab --------
    view_tab = ttk.Frame(sub)
    sub.add(view_tab, text="View")

    topbar = ttk.Frame(view_tab)
    topbar.pack(side="top", fill="x", padx=6, pady=6)

    btn_open = ttk.Button(topbar, text="Open DB…")
    lbl_path = ttk.Label(topbar, text="")
    lbl_search = ttk.Label(topbar, text="Search:")
    ent_search = ttk.Entry(topbar, width=28)

    btn_open.pack(side="left")
    ttk.Separator(topbar, orient="vertical").pack(side="left", fill="y", padx=6)
    lbl_search.pack(side="left", padx=(4, 2))
    ent_search.pack(side="left")
    ttk.Separator(topbar, orient="vertical").pack(side="left", fill="y", padx=6)
    lbl_path.pack(side="left", padx=4)

    tree_frame = ttk.Frame(view_tab)
    tree_frame.pack(side="top", fill="both", expand=True, padx=6, pady=6)

    tv = ttk.Treeview(tree_frame)
    vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tv.yview)
    hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=tv.xview)
    tv.configure(yscroll=vsb.set, xscroll=hsb.set)
    tv.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")
    hsb.pack(side="bottom", fill="x")

    nofile_label = ttk.Label(
        tree_frame,
        text="No file loaded.\nClick 'Open DB…' to choose an Excel/CSV.",
        justify="center"
    )

    # -------- Add New Tab --------
    add_tab = ttk.Frame(sub)
    sub.add(add_tab, text="Add New")

    form = ttk.Frame(add_tab)
    form.pack(side="top", fill="x", padx=8, pady=10)

    e_genus = ttk.Entry(form, width=30)
    e_species = ttk.Entry(form, width=30)
    e_common = ttk.Entry(form, width=40)
    e_family = ttk.Entry(form, width=30)

    def _row(r, label, widget):
        ttk.Label(form, text=label, width=14, anchor="e").grid(row=r, column=0, padx=4, pady=4, sticky="e")
        widget.grid(row=r, column=1, padx=4, pady=4, sticky="w")

    _row(0, "Genus*", e_genus)
    _row(1, "Species*", e_species)
    _row(2, "Common Name", e_common)
    _row(3, "Family", e_family)

    btn_add = ttk.Button(add_tab, text="Add Species")
    btn_add.pack(side="top", pady=4)

    controller = SpeciesDBController(tv, status_var, nofile_label)

    btn_open.configure(command=lambda: (
        controller.select_file(),
        lbl_path.configure(text=os.path.basename(controller.file_path) if controller.file_path else "")
    ))
    ent_search.bind("<KeyRelease>", lambda e: controller.filter_rows(ent_search.get()))
    btn_add.configure(command=lambda: (
        controller.add_species(e_genus.get(), e_species.get(), e_common.get(), e_family.get()),
        e_genus.delete(0, "end"), e_species.delete(0, "end"),
        e_common.delete(0, "end"), e_family.delete(0, "end")
    ))

    if default_path and os.path.exists(default_path):
        try:
            controller.load_from_path(default_path)
            lbl_path.configure(text=os.path.basename(default_path))
        except Exception as e:
            messagebox.showwarning("Auto Load", f"Could not auto-load default file:\n{e}")
            controller._show_nofile(True)
    else:
        controller._show_nofile(True)

    return parent
