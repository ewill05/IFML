import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
import os

from utils import style_row_tags_for_treeview, register_theme_listener

LOG_PATH = "data/species_trait_logs.xlsx"

TABLE_COLUMNS = [
    "Genus", "Species", "Common Name", "Type", "Group",
    "Entries", "Leaf", "Bark", "Tree", "Other",
    "Scanned", "Archived", "Missing"
]

def ensure_log_file():
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(LOG_PATH):
        cols = [
            "Timestamp","Record ID","Genus","Species","Common Name","Type","Group",
            "Photo Path","Has Leaf","Has Bark","Has Tree","Has Other","Scanned","Archived","Notes"
        ]
        pd.DataFrame(columns=cols).to_excel(LOG_PATH, index=False)

def read_log_df() -> pd.DataFrame:
    ensure_log_file()
    try:
        df = pd.read_excel(LOG_PATH)
    except Exception:
        df = pd.DataFrame(columns=[c for c in TABLE_COLUMNS if c not in ("Entries","Leaf","Bark","Tree","Other","Scanned","Archived","Missing")])
    needed = [
        "Timestamp","Record ID","Genus","Species","Common Name","Type","Group",
        "Photo Path","Has Leaf","Has Bark","Has Tree","Has Other","Scanned","Archived","Notes"
    ]
    for c in needed:
        if c not in df.columns:
            df[c] = "" if c not in {"Has Leaf","Has Bark","Has Tree","Has Other","Scanned","Archived"} else False
    return df[needed]

def compute_audit(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:
    if df.empty:
        return pd.DataFrame(columns=TABLE_COLUMNS), [], []
    # Normalize boolean-ish columns for safety
    for col in ["Has Leaf","Has Bark","Has Tree","Has Other","Scanned","Archived"]:
        df[col] = df[col].astype(str).str.lower().isin({"true","1","yes"}).fillna(False)

    grouped = df.groupby(["Genus","Species","Common Name","Type","Group"], dropna=False)
    rows = []
    for (g, s, cn, typ, grp), grp_df in grouped:
        entries   = len(grp_df)
        leaf_ct   = int(grp_df["Has Leaf"].sum())
        bark_ct   = int(grp_df["Has Bark"].sum())
        tree_ct   = int(grp_df["Has Tree"].sum())
        other_ct  = int(grp_df["Has Other"].sum())
        scanned_ct= int(grp_df["Scanned"].sum())
        archived_ct=int(grp_df["Archived"].sum())
        missing = []
        if leaf_ct == 0:  missing.append("Leaf")
        if bark_ct == 0:  missing.append("Bark")
        if tree_ct == 0:  missing.append("Tree")
        if other_ct == 0: missing.append("Other")
        rows.append({
            "Genus": g or "", "Species": s or "", "Common Name": cn or "",
            "Type": typ or "", "Group": grp or "",
            "Entries": entries, "Leaf": leaf_ct, "Bark": bark_ct, "Tree": tree_ct, "Other": other_ct,
            "Scanned": scanned_ct, "Archived": archived_ct,
            "Missing": ", ".join(missing)
        })
    audit_df = pd.DataFrame(rows, columns=TABLE_COLUMNS)
    types = sorted([t for t in df["Type"].dropna().astype(str).unique().tolist() if t.strip()])
    groups = sorted([g for g in df["Group"].dropna().astype(str).unique().tolist() if g.strip()])
    return audit_df, types, groups

def build_audit_tab(notebook: ttk.Notebook):
    frame = ttk.Frame(notebook)
    notebook.add(frame, text="📊 Audit")

    # ───────── Controls card ─────────
    card = ttk.Frame(frame, style="Card.TFrame", padding=10)
    card.pack(side="top", fill="x", padx=8, pady=8)

    ttk.Label(card, text="Type").pack(side="left", padx=(0,6))
    type_cb = ttk.Combobox(card, values=["All"], width=16, state="readonly"); type_cb.set("All")
    type_cb.pack(side="left")

    ttk.Label(card, text="Group").pack(side="left", padx=(10,6))
    group_cb = ttk.Combobox(card, values=["All"], width=16, state="readonly"); group_cb.set("All")
    group_cb.pack(side="left")

    only_missing = tk.BooleanVar(value=False)
    ttk.Checkbutton(card, text="Only Missing Parts", variable=only_missing).pack(side="left", padx=10)

    card.pack_propagate(False); card.update_idletasks()
    spacer = ttk.Frame(card); spacer.pack(side="left", expand=True, fill="x")

    ttk.Label(card, text="Search").pack(side="left", padx=(0,6))
    search_var = tk.StringVar()
    search_entry = ttk.Entry(card, textvariable=search_var, width=28); search_entry.pack(side="left")

    ttk.Button(card, text="Export CSV", command=lambda: export_csv()).pack(side="left", padx=8)
    ttk.Button(card, text="Export Excel", command=lambda: export_excel()).pack(side="left")

    # ───────── Table ─────────
    table_cols = TABLE_COLUMNS
    tree = ttk.Treeview(frame, columns=table_cols, show="headings", height=18, selectmode="extended")
    for c in table_cols:
        w = 120
        if c in ("Genus","Species","Common Name"): w = 140
        if c in ("Missing",): w = 220
        tree.heading(c, text=c); tree.column(c, width=w, anchor="w")
    tree.pack(fill="both", expand=True, padx=8, pady=(0,8))

    # Theme-adaptive zebra + missing highlight
    def _apply_row_tag_styles():
        style_row_tags_for_treeview(tree)
    _apply_row_tag_styles()
    register_theme_listener(_apply_row_tag_styles)

    yscroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=yscroll.set); yscroll.place(in_=tree, relx=1, rely=0, relheight=1, x=-1)

    def load_and_render():
        df = read_log_df()
        audit_df, types, groups = compute_audit(df)

        # refresh filter options
        tv = ["All"] + types; gv = ["All"] + groups
        if tuple(type_cb["values"]) != tuple(tv): type_cb["values"] = tv
        if tuple(group_cb["values"]) != tuple(gv): group_cb["values"] = gv

        out = audit_df
        if type_cb.get() != "All":
            out = out[out["Type"].astype(str) == type_cb.get()]
        if group_cb.get() != "All":
            out = out[out["Group"].astype(str) == group_cb.get()]

        if only_missing.get():
            out = out[out["Missing"].astype(str).str.len() > 0]

        term = search_var.get().strip().lower()
        if term:
            m = False
            for c in ["Genus","Species","Common Name","Group","Type","Missing"]:
                m = m | out[c].astype(str).str.lower().str.contains(term, na=False)
            out = out[m]

        tree.delete(*tree.get_children())
        for i, r in out.iterrows():
            tags = []
            if i % 2 == 0: tags.append("zebra_even")
            if str(r.get("Missing","")).strip(): tags.append("missing")
            tree.insert("", "end", values=[r.get(c, "") for c in table_cols], tags=tuple(tags))

    def export_csv():
        out = tree_to_df()
        if out.empty:
            messagebox.showinfo("Export", "No rows to export."); return
        path = filedialog.asksaveasfilename(title="Export Audit (CSV)", defaultextension=".csv",
                                            filetypes=[("CSV","*.csv")])
        if not path: return
        try:
            out.to_csv(path, index=False); messagebox.showinfo("Export", f"Saved: {path}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    def export_excel():
        out = tree_to_df()
        if out.empty:
            messagebox.showinfo("Export", "No rows to export."); return
        path = filedialog.asksaveasfilename(title="Export Audit (Excel)", defaultextension=".xlsx",
                                            filetypes=[("Excel","*.xlsx")])
        if not path: return
        try:
            out.to_excel(path, index=False); messagebox.showinfo("Export", f"Saved: {path}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    def tree_to_df() -> pd.DataFrame:
        rows = []
        for iid in tree.get_children():
            vals = tree.item(iid, "values")
            rows.append(dict(zip(table_cols, vals)))
        return pd.DataFrame(rows, columns=table_cols)

    # Events
    type_cb.bind("<<ComboboxSelected>>", lambda e: load_and_render())
    group_cb.bind("<<ComboboxSelected>>", lambda e: load_and_render())
    search_var.trace_add("write", lambda *_: load_and_render())
    # (Removed redundant hidden tk.Checkbutton)

    # Shortcuts
    top = frame.winfo_toplevel()
    top.bind_all("<Control-f>", lambda e: (search_entry.focus_set(), search_entry.select_range(0,'end')))

    load_and_render()
