import tkinter as tk
from tkinter import ttk

class AutocompleteEntry(ttk.Entry):
    def __init__(self, autocomplete_list, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.autocomplete_list = sorted(autocomplete_list, key=str.lower)

        self.var = self["textvariable"] or tk.StringVar()
        self["textvariable"] = self.var
        self.var.trace_add("write", self.update_list)

        self.lb = None
        self.matches = []

        # Keyboard & focus behavior
        self.bind("<Right>", self.accept_current)
        self.bind("<Return>", self.accept_current)
        self.bind("<Down>", self.move_down)
        self.bind("<Up>", self.move_up)
        self.bind("<Escape>", lambda e: self.destroy_listbox())
        self.bind("<FocusOut>", lambda e: self.after(100, self.destroy_listbox))

    def update_list(self, *_):
        text = (self.var.get() or "").lower().strip()
        if not text:
            self.destroy_listbox()
            return

        # Prioritize prefix matches, then contains
        starts = [x for x in self.autocomplete_list if x.lower().startswith(text)]
        contains = [x for x in self.autocomplete_list if text in x.lower() and x not in starts]
        self.matches = starts + contains

        if not self.matches:
            self.destroy_listbox()
            return

        if not self.lb:
            self.lb = tk.Listbox(exportselection=False)
            self.lb.bind("<Double-Button-1>", self.accept_current)
            self.lb.bind("<Return>", self.accept_current)
            self.lb.bind("<Escape>", lambda e: self.destroy_listbox())
            self.lb.place(in_=self, relx=0, rely=1, relwidth=1)

        self.lb.delete(0, tk.END)
        for item in self.matches:
            self.lb.insert(tk.END, item)
        self.lb.selection_clear(0, tk.END)
        self.lb.selection_set(0)

    def destroy_listbox(self):
        if self.lb:
            self.lb.destroy()
            self.lb = None

    def accept_current(self, event=None):
        if self.lb:
            idxs = self.lb.curselection()
            if idxs:
                self.var.set(self.lb.get(idxs[0]))
                self.icursor(tk.END)
            self.destroy_listbox()

    def move_down(self, event=None):
        if not self.lb:
            self.update_list()
            return "break"
        idxs = self.lb.curselection()
        n = (idxs[0] + 1) if idxs else 0
        n = min(n, self.lb.size() - 1)
        self.lb.selection_clear(0, tk.END)
        self.lb.selection_set(n)
        self.lb.see(n)
        return "break"

    def move_up(self, event=None):
        if not self.lb:
            return "break"
        idxs = self.lb.curselection()
        n = (idxs[0] - 1) if idxs else 0
        n = max(n, 0)
        self.lb.selection_clear(0, tk.END)
        self.lb.selection_set(n)
        self.lb.see(n)
        return "break"
