# logger_tab.py — streamlined logger with split layout, filters, edit/delete, import/export
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import os
import re
from datetime import datetime
from shared_config import get_db_path

# --- Species DB header normalization helpers ---
HEADER_ALIASES = {
    "genus": "Genus",
    "species": "Species",
    "commonname": "Common Name",
    "common_name": "Common Name",
    "type": "Type",
    "group": "Group",
    "family": "Family",
}
def _normalize_headers(df: pd.DataFrame) -> pd.DataFrame:
    ren = {}
    for col in df.columns:
        key = str(col).strip().lower().replace(" ", "").replace("_", "")
        ren[col] = HEADER_ALIASES.get(key, str(col).strip())
    return df.rename(columns=ren)

def _read_any(path: str) -> pd.DataFrame:
    if path.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(path, dtype=str)
    return pd.read_csv(path, dtype=str)


from autocomplete import AutocompleteEntry
from utils import style_row_tags_for_treeview, register_theme_listener  # theme hooks

# ──────────────────────────────────────────────────────────────────────────────
# Paths & Schema
# ──────────────────────────────────────────────────────────────────────────────
LOG_PATH = "data/species_trait_logs.xlsx"   # photo/scan log
SPECIES_PATH = "data/species_list.xlsx"     # species reference

LOG_COLUMNS = [
    "Timestamp",
    "Record ID",
    "Genus", "Species", "Common Name", "Type", "Group",
    "Photo Path",
    "Has Leaf", "Has Bark", "Has Tree", "Has Other",
    "Scanned", "Archived",
    "Notes",
]

BOOL_COLUMNS = {"Has Leaf", "Has Bark", "Has Tree", "Has Other", "Scanned", "Archived"}

# ──────────────────────────────────────────────────────────────────────────────
# Utilities
# ──────────────────────────────────────────────────────────────────────────────
def ensure_dir_structure():
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(LOG_PATH):
        pd.DataFrame(columns=LOG_COLUMNS).to_excel(LOG_PATH, index=False)

def read_log_df() -> pd.DataFrame:
    ensure_dir_structure()
    try:
        df = pd.read_excel(LOG_PATH)
    except Exception:
        df = pd.DataFrame(columns=LOG_COLUMNS)
    # Backfill any missing columns and reorder strictly
    for c in LOG_COLUMNS:
        if c not in df.columns:
            df[c] = False if c in BOOL_COLUMNS else ""
    return df[LOG_COLUMNS]

def write_log_df(df: pd.DataFrame):
    out = df.copy()
    for c in LOG_COLUMNS:
        if c not in out.columns:
            out[c] = False if c in BOOL_COLUMNS else ""
    out = out[LOG_COLUMNS]
    out.to_excel(LOG_PATH, index=False)

def safe_slug(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_]+", "", s)
    return s

def next_record_id(genus: str, species: str) -> str:
    """Return next id like genus_species_01 for that species."""
    df = read_log_df()
    g = str(genus).strip()
    sp = str(species).strip()
    subset = df[(df["Genus"] == g) & (df["Species"] == sp)]
    n = 0
    for rid in subset.get("Record ID", pd.Series(dtype=str)).dropna().astype(str):
        m = re.search(r"_(\d+)$", rid)
        if m:
            n = max(n, int(m.group(1)))
    return f"{safe_slug(g)}_{safe_slug(sp)}_{(n + 1):02d}"


# Reference species list for autofill during CSV import
REFERENCE_CSV = "North_American_Tree_Database_Full.csv"


def load_reference_db(path: str = REFERENCE_CSV) -> pd.DataFrame:
    """Load the optional reference species database."""
    try:
        df = pd.read_csv(path, dtype=str).fillna("")
        cols = {c.strip().lower().replace(" ", "").replace("_", ""): c for c in df.columns}
        ren = {}
        if "commonname" in cols:
            ren[cols["commonname"]] = "Common Name"
        if "genus" in cols:
            ren[cols["genus"]] = "Genus"
        if "species" in cols:
            ren[cols["species"]] = "Species"
        return df.rename(columns=ren)
    except Exception:
        return pd.DataFrame(columns=["Common Name", "Genus", "Species"])


def autofill_species(df: pd.DataFrame, ref: pd.DataFrame) -> pd.DataFrame:
    """Fill missing Genus/Species using Common Name via reference table."""
    if ref.empty:
        return df
    lookup = {
        str(r.get("Common Name", "")).strip().lower(): (r.get("Genus", ""), r.get("Species", ""))
        for _, r in ref.iterrows()
    }
    for idx, row in df.iterrows():
        genus = str(row.get("Genus", "")).strip()
        species = str(row.get("Species", "")).strip()
        if genus and species:
            continue
        common = str(row.get("Common Name", "")).strip().lower()
        g, s = lookup.get(common, (genus, species))
        if not genus:
            df.at[idx, "Genus"] = g
        if not species:
            df.at[idx, "Species"] = s
    return df


def load_species_aliases():
    """
    Load species for autocomplete from the DB path saved by the Species tab.
    Accepts sheets with at least Genus/Species; Common Name optional.
    Type/Group/Family optional.
    """
    aliases = []
    alias_to_rec = {}
    records = []
    try:
        db_path = get_db_path("")
        if not db_path or not os.path.exists(db_path):
            raise FileNotFoundError("No species DB path set. Open a DB in the Species tab first.")

        sdf = _read_any(db_path)
        sdf = _normalize_headers(sdf).fillna("")

        # Ensure minimum columns
        if "Genus" not in sdf.columns or "Species" not in sdf.columns:
            raise ValueError("Species DB must have Genus and Species columns")

        # Fill optional columns
        for opt in ["Common Name", "Type", "Group", "Family"]:
            if opt not in sdf.columns:
                sdf[opt] = ""

        for _, r in sdf.iterrows():
            genus = str(r["Genus"]).strip()
            species = str(r["Species"]).strip()
            if not genus or not species:
                continue
            rec = {
                "Genus": genus,
                "Species": species,
                "Common Name": str(r["Common Name"]).strip(),
                "Type": str(r["Type"]).strip(),
                "Group": str(r["Group"]).strip(),
                "Family": str(r["Family"]).strip(),
            }
            records.append(rec)
            display_full = f"{rec['Genus']} {rec['Species']} ({rec['Common Name']})".strip()
            display_sci  = f"{rec['Genus']} {rec['Species']}".strip()
            common_only  = rec["Common Name"]
            for a in {display_full, display_sci, common_only, display_sci.lower(), common_only.lower()}:
                if a:
                    alias_to_rec.setdefault(a, rec)
                    aliases.append(a)
    except Exception as e:
        # Soft fallback list
        fallback = [
            {"Genus": "Quercus", "Species": "macrocarpa", "Type": "Deciduous", "Group": "White Oaks", "Family": "Fagaceae", "Common Name": "Bur Oak"},
            {"Genus": "Carya", "Species": "cordiformis", "Type": "Deciduous", "Group": "Hickories", "Family": "Juglandaceae", "Common Name": "Bitternut Hickory"},
        ]
        for rec in fallback:
            display_full = f"{rec['Genus']} {rec['Species']} ({rec['Common Name']})"
            display_sci  = f"{rec['Genus']} {rec['Species']}"
            common_only  = rec["Common Name"]
            for a in {display_full, display_sci, common_only, display_sci.lower(), common_only.lower()}:
                if a:
                    alias_to_rec.setdefault(a, rec)
                    aliases.append(a)
    aliases = sorted(set(aliases), key=str.lower)
    return aliases, alias_to_rec, records


def resolve_species(text: str, alias_to_rec: dict, records: list[dict]) -> dict | None:
    if not text:
        return None
    t = text.strip()
    if t in alias_to_rec:
        return alias_to_rec[t]
    if t.lower() in alias_to_rec:
        return alias_to_rec[t.lower()]
    # simple fuzzy contains
    tl = t.lower()
    toks = [x for x in tl.split() if x]
    for rec in records:
        disp = f"{rec['Genus']} {rec['Species']} ({rec['Common Name']})".lower()
        if all(tok in disp for tok in toks):
            return rec
    return None

# ──────────────────────────────────────────────────────────────────────────────
# Main UI
# ──────────────────────────────────────────────────────────────────────────────
def build_logger_tab(notebook: ttk.Notebook):
    frame = ttk.Frame(notebook)
    notebook.add(frame, text="📷 Logger")

    ensure_dir_structure()

    # ========== TOP TOOLBAR (single row, left-aligned) ==========
    toolbar = ttk.Frame(frame)
    toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=(8, 4))
    toolbar.columnconfigure(10, weight=1)  # flex spacer if needed

    btn_new     = ttk.Button(toolbar, text="New Entry")
    btn_save    = ttk.Button(toolbar, text="Save Entry")
    btn_edit    = ttk.Button(toolbar, text="Edit Selected")
    btn_delete  = ttk.Button(toolbar, text="Delete Selected")
    btn_import  = ttk.Button(toolbar, text="Import CSV")
    btn_exportc = ttk.Button(toolbar, text="Export CSV")
    btn_exportx = ttk.Button(toolbar, text="Export Excel")

    for i, w in enumerate([btn_new, btn_save, btn_edit, btn_delete, btn_import, btn_exportc, btn_exportx]):
        w.grid(row=0, column=i, padx=4)

    # ========== SPLIT: LEFT (Quick Entry) | RIGHT (Filters + Table) ==========
    form_panel = ttk.Frame(frame, style="Card.TFrame", padding=10)
    form_panel.grid(row=1, column=0, sticky="nsew", padx=(8, 4), pady=(0, 8))
    right_panel = ttk.Frame(frame, style="Card.TFrame", padding=10)
    right_panel.grid(row=1, column=1, sticky="nsew", padx=(4, 8), pady=(0, 8))

    frame.columnconfigure(0, weight=1, minsize=460)
    frame.columnconfigure(1, weight=2, minsize=640)
    frame.rowconfigure(1, weight=1)

    # ---------- Quick Entry (LEFT) ----------
    ttk.Label(form_panel, text="Species").grid(row=0, column=0, sticky="e", padx=6, pady=6)
    aliases, alias_to_rec, records = load_species_aliases()
    species_entry = AutocompleteEntry(aliases, form_panel, width=36)
    species_entry.grid(row=0, column=1, sticky="w", pady=6)
    auto_btn = ttk.Button(form_panel, text="Auto-Fill")
    auto_btn.grid(row=0, column=2, sticky="w", padx=4)

    preview = {k: tk.StringVar() for k in ["Genus", "Species", "Common Name", "Type", "Group"]}

    def update_preview(*_):
        rec = resolve_species(species_entry.get(), alias_to_rec, records)
        for k in preview:
            preview[k].set(rec.get(k, "") if rec else "")

    r = 1
    for label_key in ["Genus", "Species", "Common Name", "Type", "Group"]:
        ttk.Label(form_panel, text=label_key, style="Muted.TLabel").grid(row=r, column=0, sticky="e", padx=6)
        ttk.Label(form_panel, textvariable=preview[label_key]).grid(row=r, column=1, sticky="w", pady=1)
        r += 1

    ttk.Label(form_panel, text="Photo Path").grid(row=r, column=0, sticky="e", padx=6, pady=(8, 4))
    photo_var = tk.StringVar()
    ttk.Entry(form_panel, textvariable=photo_var, width=38).grid(row=r, column=1, sticky="w", pady=(8, 4))

    def browse_photo():
        path = filedialog.askopenfilename(
            title="Select photo",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.tif *.tiff *.heic *.webp"), ("All files", "*.*")]
        )
        if path:
            photo_var.set(path)

    ttk.Button(form_panel, text="Browse…", command=browse_photo).grid(row=r, column=2, sticky="w", padx=4)
    r += 1

    ttk.Label(form_panel, text="Photo Types").grid(row=r, column=0, sticky="e", padx=6, pady=(6, 2))
    has_leaf  = tk.BooleanVar(value=False)
    has_bark  = tk.BooleanVar(value=False)
    has_tree  = tk.BooleanVar(value=False)
    has_other = tk.BooleanVar(value=False)
    ttk.Checkbutton(form_panel, text="Leaf",  variable=has_leaf).grid(row=r, column=1, sticky="w")
    ttk.Checkbutton(form_panel, text="Bark",  variable=has_bark).grid(row=r, column=2, sticky="w")
    r += 1
    ttk.Checkbutton(form_panel, text="Tree",  variable=has_tree).grid(row=r, column=1, sticky="w")
    ttk.Checkbutton(form_panel, text="Other", variable=has_other).grid(row=r, column=2, sticky="w")

    def preset_all():
        has_leaf.set(True); has_bark.set(True); has_tree.set(True); has_other.set(True)
    def preset_none():
        has_leaf.set(False); has_bark.set(False); has_tree.set(False); has_other.set(False)
    def preset_leaf_bark():
        has_leaf.set(True); has_bark.set(True); has_tree.set(False); has_other.set(False)

    preset_row = r + 1
    ttk.Button(form_panel, text="All",  command=preset_all).grid(row=preset_row, column=1, sticky="w", pady=(2, 6))
    ttk.Button(form_panel, text="None", command=preset_none).grid(row=preset_row, column=2, sticky="w", pady=(2, 6))
    ttk.Button(form_panel, text="Leaf + Bark", command=preset_leaf_bark).grid(row=preset_row, column=3, sticky="w", padx=4, pady=(2, 6))
    r = preset_row + 1

    ttk.Label(form_panel, text="Status").grid(row=r, column=0, sticky="e", padx=6, pady=(4, 2))
    scanned  = tk.BooleanVar(value=False)
    archived = tk.BooleanVar(value=False)
    ttk.Checkbutton(form_panel, text="Scanned",  variable=scanned).grid(row=r, column=1, sticky="w")
    ttk.Checkbutton(form_panel, text="Archived", variable=archived).grid(row=r, column=2, sticky="w")
    r += 1

    ttk.Label(form_panel, text="Notes").grid(row=r, column=0, sticky="ne", padx=6, pady=(6, 2))
    notes_txt = tk.Text(form_panel, width=40, height=3)
    notes_txt.grid(row=r, column=1, columnspan=3, sticky="w", pady=(6, 2))
    r += 1

    form_btns = ttk.Frame(form_panel)
    form_btns.grid(row=r, column=1, columnspan=3, sticky="w", pady=(6, 2))
    fbtn_save = ttk.Button(form_btns, text="Save Entry")
    fbtn_clear = ttk.Button(form_btns, text="Clear")
    fbtn_save.pack(side="left", padx=(0, 6))
    fbtn_clear.pack(side="left")

    form_panel.columnconfigure(1, weight=1)

    # ---------- Right: Filters + Table ----------
    controls = ttk.Frame(right_panel)
    controls.pack(side="top", fill="x")

    ttk.Label(controls, text="Type").pack(side="left", padx=(0, 6))
    type_cb = ttk.Combobox(controls, values=["All"], width=16, state="readonly")
    type_cb.set("All"); type_cb.pack(side="left")

    ttk.Label(controls, text="Group").pack(side="left", padx=(10, 6))
    group_cb = ttk.Combobox(controls, values=["All"], width=16, state="readonly")
    group_cb.set("All"); group_cb.pack(side="left")

    ttk.Label(controls, text="Status").pack(side="left", padx=(10, 6))
    status_cb = ttk.Combobox(controls, values=["All", "Scanned", "Unscanned", "Archived", "Unarchived"], width=16, state="readonly")
    status_cb.set("All"); status_cb.pack(side="left")

    only_missing = tk.BooleanVar(value=False)
    ttk.Checkbutton(controls, text="Only Missing Parts", variable=only_missing, command=lambda: reload_table()).pack(side="left", padx=10)

    controls.pack_propagate(False)
    controls.update_idletasks()
    spacer = ttk.Frame(controls); spacer.pack(side="left", expand=True, fill="x")
    ttk.Label(controls, text="Search").pack(side="left", padx=(0, 6))
    search_var = tk.StringVar()
    search_entry = ttk.Entry(controls, textvariable=search_var, width=28)
    search_entry.pack(side="left")

    table_cols = LOG_COLUMNS
    table_frame = ttk.Frame(right_panel)
    table_frame.pack(side="top", fill="both", expand=True, pady=(8, 0))
    tree = ttk.Treeview(table_frame, columns=table_cols, show="headings", height=16, selectmode="extended")
    for c in table_cols:
        width = 120
        if c in ("Notes", "Photo Path"): width = 220
        if c in ("Genus", "Species", "Common Name"): width = 140
        tree.heading(c, text=c); tree.column(c, width=width, anchor="w")

    vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    table_frame.grid_rowconfigure(0, weight=1)
    table_frame.grid_columnconfigure(0, weight=1)

    # THEME-ADAPTIVE TAG COLORS
    def _apply_row_tag_styles():
        style_row_tags_for_treeview(tree)
    _apply_row_tag_styles()
    register_theme_listener(_apply_row_tag_styles)  # re-apply on theme switch

    # Status line (count of rows)
    status = ttk.Label(right_panel, text="", style="Muted.TLabel")
    status.pack(side="bottom", anchor="w", pady=(6, 0))

    # ───────── Core actions ─────────
    def clear_form():
        species_entry.delete(0, tk.END)
        for v in preview.values(): v.set("")
        photo_var.set("")
        for b in (has_leaf, has_bark, has_tree, has_other): b.set(False)
        scanned.set(False); archived.set(False)
        notes_txt.delete("1.0", "end")
        species_entry.focus_set()

    def save_new():
        rec = resolve_species(species_entry.get(), alias_to_rec, records)
        if not rec:
            messagebox.showwarning("Species Required", "Enter a valid common or scientific name (then Auto-Fill).")
            species_entry.focus_set(); return
        row = {
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "Record ID": next_record_id(rec["Genus"], rec["Species"]),
            "Genus": rec["Genus"], "Species": rec["Species"],
            "Common Name": rec["Common Name"], "Type": rec["Type"], "Group": rec["Group"],
            "Photo Path": photo_var.get().strip(),
            "Has Leaf": bool(has_leaf.get()), "Has Bark": bool(has_bark.get()),
            "Has Tree": bool(has_tree.get()), "Has Other": bool(has_other.get()),
            "Scanned": bool(scanned.get()), "Archived": bool(archived.get()),
            "Notes": notes_txt.get("1.0", "end").strip(),
        }

        # prevent duplicate Record ID collision (rare, but safe)
        df = read_log_df()
        if (df["Record ID"].astype(str) == row["Record ID"]).any():
            row["Record ID"] = next_record_id(rec["Genus"], rec["Species"])
            if (df["Record ID"].astype(str) == row["Record ID"]).any():
                messagebox.showerror("Duplicate", "Record ID collision; please try again.")
                return

        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        write_log_df(df)
        clear_form(); reload_table()
        messagebox.showinfo("Saved", f"Logged {row['Record ID']}")

    def edit_selected():
        sel = tree.selection()
        if not sel:
            messagebox.showinfo("Edit", "Select a row to edit."); return
        values = tree.item(sel[0], "values")
        row_dict = dict(zip(table_cols, values))
        open_edit_dialog(row_dict)

    def delete_selected():
        sel = tree.selection()
        if not sel:
            messagebox.showinfo("Delete", "Select at least one row."); return
        if not messagebox.askyesno("Confirm", "Delete selected row(s) from the log? This cannot be undone."):
            return
        df = read_log_df()
        keys = []
        for item in sel:
            vals = tree.item(item, "values")
            d = dict(zip(table_cols, vals))
            keys.append((d["Timestamp"], d["Record ID"]))
        for ts, rid in keys:
            df = df[~((df["Timestamp"].astype(str) == str(ts)) & (df["Record ID"].astype(str) == str(rid)))]
        write_log_df(df)
        reload_table()

    def import_csv():
        path = filedialog.askopenfilename(
            title="Import CSV and append to log",
            filetypes=[("CSV", "*.csv")]
        )
        if not path:
            return
        try:
            inc = pd.read_csv(path, dtype=str).fillna("")
            for c in LOG_COLUMNS:
                if c not in inc.columns:
                    inc[c] = False if c in BOOL_COLUMNS else ""
            for c in BOOL_COLUMNS:
                inc[c] = inc[c].astype(str).str.lower().isin(["1", "true", "yes", "y"])
            inc = inc[LOG_COLUMNS]

            ref = load_reference_db()
            inc = autofill_species(inc, ref)

            df = read_log_df()
            existing = df[["Genus", "Species", "Record ID"]].copy()
            for idx, row in inc.iterrows():
                rid = str(row.get("Record ID", "")).strip()
                if not rid:
                    g = row.get("Genus", "")
                    s = row.get("Species", "")
                    subset = existing[(existing["Genus"] == g) & (existing["Species"] == s)]
                    n = 0
                    for ridx in subset.get("Record ID", pd.Series(dtype=str)).dropna().astype(str):
                        m = re.search(r"_(\d+)$", ridx)
                        if m:
                            n = max(n, int(m.group(1)))
                    rid = f"{safe_slug(g)}_{safe_slug(s)}_{(n + 1):02d}"
                    inc.at[idx, "Record ID"] = rid
                    existing = pd.concat([existing, pd.DataFrame([{ "Genus": g, "Species": s, "Record ID": rid }])], ignore_index=True)

            df = pd.concat([df, inc], ignore_index=True)
            write_log_df(df)
            messagebox.showinfo("Import", f"Imported {len(inc)} rows.")
            reload_table()
        except Exception as e:
            messagebox.showerror("Import Error", str(e))

    def export_csv():
        df = filtered_df()
        if df.empty:
            messagebox.showinfo("Export", "No rows to export."); return
        path = filedialog.asksaveasfilename(
            title="Export filtered view (CSV)",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")]
        )
        if not path:
            return
        try:
            df.to_csv(path, index=False)
            messagebox.showinfo("Export", f"Saved: {path}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    def export_excel():
        df = filtered_df()
        if df.empty:
            messagebox.showinfo("Export", "No rows to export."); return
        path = filedialog.asksaveasfilename(
            title="Export filtered view (Excel)",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")]
        )
        if not path:
            return
        try:
            df.to_excel(path, index=False)
            messagebox.showinfo("Export", f"Saved: {path}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    # Wire toolbar + form buttons
    btn_new.configure(command=clear_form)
    btn_save.configure(command=save_new)
    btn_edit.configure(command=edit_selected)
    btn_delete.configure(command=delete_selected)
    btn_import.configure(command=import_csv)
    btn_exportc.configure(command=export_csv)
    btn_exportx.configure(command=export_excel)

    fbtn_save.configure(command=save_new)
    fbtn_clear.configure(command=clear_form)
    auto_btn.configure(command=update_preview)

    # ---------- Filtering / Rendering ----------
    def filtered_df() -> pd.DataFrame:
        df = read_log_df()
        # populate dropdowns dynamically
        types = sorted([t for t in df["Type"].dropna().astype(str).unique().tolist() if t.strip()])
        groups = sorted([g for g in df["Group"].dropna().astype(str).unique().tolist() if g.strip()])
        t_vals = ["All"] + types
        g_vals = ["All"] + groups
        if tuple(type_cb["values"]) != tuple(t_vals):
            type_cb["values"] = t_vals
        if tuple(group_cb["values"]) != tuple(g_vals):
            group_cb["values"] = g_vals

        # work on a copy & normalize boolean-ish columns
        out = df.copy()
        for col in ["Has Leaf","Has Bark","Has Tree","Has Other","Scanned","Archived"]:
            out[col] = out[col].astype(str).str.lower().isin({"true","1","yes"}).fillna(False)

        tsel = type_cb.get()
        gsel = group_cb.get()
        ssel = status_cb.get()
        term = search_var.get().strip().lower()

        if tsel and tsel != "All":
            out = out[out["Type"].astype(str) == tsel]
        if gsel and gsel != "All":
            out = out[out["Group"].astype(str) == gsel]

        if ssel == "Scanned":
            out = out[out["Scanned"]]
        elif ssel == "Unscanned":
            out = out[~out["Scanned"]]
        elif ssel == "Archived":
            out = out[out["Archived"]]
        elif ssel == "Unarchived":
            out = out[~out["Archived"]]

        if only_missing.get():
            out = out[~(out["Has Leaf"] & out["Has Bark"] & out["Has Tree"] & out["Has Other"])]

        if term:
            term_cols = ["Genus", "Species", "Common Name", "Record ID", "Notes"]
            mask = False
            for c in term_cols:
                mask = mask | out[c].astype(str).str.lower().str.contains(term, na=False)
            out = out[mask]

        return out

    def _row_tags_from_dict(d: dict):
        def as_bool(x): return str(x).lower() in {"true","1","yes"}
        tags = []
        if not (as_bool(d.get("Has Leaf")) and as_bool(d.get("Has Bark"))
                and as_bool(d.get("Has Tree")) and as_bool(d.get("Has Other"))):
            tags.append("missing")
        if as_bool(d.get("Archived")):
            tags.append("archived")
        return tags

    def reload_table():
        df = filtered_df()
        tree.delete(*tree.get_children())
        for i, r in df.iterrows():
            vals = [r.get(c, "") for c in table_cols]
            tags = _row_tags_from_dict(r.to_dict())
            if i % 2 == 0:
                tags.append("zebra_even")
            tree.insert("", "end", values=vals, tags=tuple(tags))
        status.configure(text=f"{len(df):,} row(s) shown")

    # ---------- Edit dialog ----------
    def open_edit_dialog(row: dict):
        win = tk.Toplevel(frame)
        win.title(f"Edit: {row.get('Record ID','')}")
        win.grab_set()

        grid = ttk.Frame(win, padding=10)
        grid.pack(fill="both", expand=True)

        def mk_row(label, default="", width=40):
            r = len(fields)
            ttk.Label(grid, text=label).grid(row=r, column=0, sticky="e", padx=6, pady=4)
            e = ttk.Entry(grid, width=width)
            e.insert(0, str(default))
            e.grid(row=r, column=1, sticky="w", padx=6, pady=4)
            fields[label] = e

        fields: dict[str, ttk.Entry] = {}
        for label in ["Genus", "Species", "Common Name", "Type", "Group", "Photo Path", "Notes"]:
            mk_row(label, row.get(label, ""))

        checks = {}
        def mk_check(text, key):
            v = tk.BooleanVar(value=str(row.get(key, "")).lower() in {"true", "1", "yes"})
            checks[key] = v
            ttk.Checkbutton(grid, text=text, variable=v).grid(row=len(fields)+len(checks), column=1, sticky="w", padx=6)

        for key in ["Has Leaf", "Has Bark", "Has Tree", "Has Other", "Scanned", "Archived"]:
            mk_check(key, key)

        btns = ttk.Frame(grid)
        btns.grid(row=len(fields)+len(checks)+1, column=0, columnspan=2, sticky="e", pady=(8, 2))
        ttk.Button(btns, text="Cancel", command=win.destroy).pack(side="right", padx=4)

        def save_edit():
            df = read_log_df()
            ts_key, rid_key = row["Timestamp"], row["Record ID"]
            mask = (df["Timestamp"].astype(str) == str(ts_key)) & (df["Record ID"].astype(str) == str(rid_key))
            if not mask.any():
                messagebox.showerror("Not Found", "Original row not found. It may have been changed or deleted.")
                return
            for k, e in fields.items():
                df.loc[mask, k] = e.get().strip()
            for k, v in checks.items():
                df.loc[mask, k] = bool(v.get())
            write_log_df(df)
            win.destroy()
            reload_table()

        ttk.Button(btns, text="Save", command=save_edit).pack(side="right", padx=4)

    # ---------- Events / Shortcuts ----------
    def on_change(*_): reload_table()
    type_cb.bind("<<ComboboxSelected>>", on_change)
    group_cb.bind("<<ComboboxSelected>>", on_change)
    status_cb.bind("<<ComboboxSelected>>", on_change)
    search_var.trace_add("write", on_change)
    species_entry.bind("<Return>", lambda e: update_preview())
    tree.bind("<Double-1>", lambda e: edit_selected())

    # Keyboard shortcuts (bind to toplevel)
    top = frame.winfo_toplevel()
    top.bind_all("<Control-s>", lambda e: save_new())
    top.bind_all("<Control-f>", lambda e: (search_entry.focus_set(), search_entry.select_range(0, 'end')))
    top.bind_all("<Control-e>", lambda e: edit_selected())
    top.bind_all("<Delete>",   lambda e: delete_selected())

    def show_shortcuts():
        messagebox.showinfo("Shortcuts", 
            "Ctrl+S: Save entry\n"
            "Ctrl+F: Focus search\n"
            "Ctrl+E: Edit selected\n"
            "Delete: Delete selected\n"
            "Enter (Species box): Auto-Fill"
        )
    top.bind_all("<F1>", lambda e: show_shortcuts())

    # Initial state
    update_preview()
    reload_table()
    species_entry.focus_set()
