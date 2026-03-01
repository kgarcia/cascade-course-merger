#!/usr/bin/env python3
"""
Cascade Course Merger — GUI
============================
Tkinter front-end for cascade_merge.py.
Works on macOS and Windows with zero extra dependencies.

Launch:  python3 cascade_merge_gui.py
"""
from __future__ import annotations

import os
import platform
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser
import zipfile

from cascade_merge import merge_from_zip, peek_module_name

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
APP_TITLE = "Cascade Course Merger"
WIN_WIDTH, WIN_HEIGHT = 720, 480
PAD = 10


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry(f"{WIN_WIDTH}x{WIN_HEIGHT}")
        self.minsize(600, 400)

        self._msg_queue: queue.Queue = queue.Queue()
        self._rows: dict[str, dict] = {}
        self._merging = False

        self._build_ui()
        self._poll_queue()

    # ---- UI construction --------------------------------------------------

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        self._build_toolbar(row=0)
        self._build_treeview(row=2)
        self._build_progress(row=3)
        self._build_actions(row=4)
        self._build_status(row=5)

    def _build_toolbar(self, row):
        bar = ttk.Frame(self, padding=PAD)
        bar.grid(row=row, column=0, sticky="ew")

        ttk.Button(bar, text="+ Add Zip Files", command=self._add_files).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(bar, text="Clear List", command=self._clear_list).pack(side="left")

        ttk.Label(bar, text="Drop .zip exports here", foreground="gray").pack(
            side="right"
        )

    def _build_treeview(self, row):
        frame = ttk.Frame(self, padding=(PAD, 0, PAD, 0))
        frame.grid(row=row, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        cols = ("module", "status")
        self.tree = ttk.Treeview(
            frame,
            columns=cols,
            show="headings tree",
            selectmode="browse",
        )
        self.tree.heading("#0", text="Zip File", anchor="w")
        self.tree.heading("module", text="Module", anchor="w")
        self.tree.heading("status", text="Status", anchor="w")

        self.tree.column("#0", width=340, stretch=True)
        self.tree.column("module", width=120, stretch=False)
        self.tree.column("status", width=180, stretch=True)

        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")

        self.tree.bind("<Double-1>", self._on_double_click)

    def _build_progress(self, row):
        frame = ttk.Frame(self, padding=(PAD, 6, PAD, 0))
        frame.grid(row=row, column=0, sticky="ew")
        frame.columnconfigure(0, weight=1)

        self.progress = ttk.Progressbar(frame, mode="determinate")
        self.progress.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.progress_label = ttk.Label(frame, text="")
        self.progress_label.grid(row=0, column=1)

    def _build_actions(self, row):
        bar = ttk.Frame(self, padding=(PAD, 8, PAD, 0))
        bar.grid(row=row, column=0, sticky="ew")

        self.merge_btn = ttk.Button(
            bar, text="Merge All", command=self._start_merge
        )
        self.merge_btn.pack(side="left", padx=(0, 6))

        ttk.Button(bar, text="Preview in Browser", command=self._preview).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(bar, text="Open Folder", command=self._open_folder).pack(
            side="left"
        )

    def _build_status(self, row):
        self.status_var = tk.StringVar(value="Ready.")
        lbl = ttk.Label(
            self, textvariable=self.status_var, padding=(PAD, 4, PAD, PAD),
            foreground="gray",
        )
        lbl.grid(row=row, column=0, sticky="ew")

    # ---- Add / clear files ------------------------------------------------

    def _add_files(self):
        paths = filedialog.askopenfilenames(
            title="Select Cascade zip exports",
            filetypes=[("Zip files", "*.zip")],
        )
        for p in paths:
            if p in self._rows:
                continue
            if not zipfile.is_zipfile(p):
                continue
            try:
                mod = peek_module_name(p)
            except (ValueError, Exception) as e:
                mod = "?"
            iid = self.tree.insert(
                "", "end",
                text=os.path.basename(p),
                values=(mod, "Ready"),
            )
            self._rows[p] = {"iid": iid, "module": mod, "output": None}

        total = len(self._rows)
        self.status_var.set(f"{total} file{'s' if total != 1 else ''} in queue.")

    def _clear_list(self):
        if self._merging:
            return
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._rows.clear()
        self.progress["value"] = 0
        self.progress_label.config(text="")
        self.status_var.set("Ready.")

    # ---- Merge logic (threaded) -------------------------------------------

    def _start_merge(self):
        if self._merging:
            return
        pending = [
            p for p, info in self._rows.items()
            if self.tree.set(info["iid"], "status") in ("Ready", "Error")
        ]
        if not pending:
            messagebox.showinfo(APP_TITLE, "Nothing to merge. Add zip files first.")
            return

        self._merging = True
        self.merge_btn.state(["disabled"])
        self.progress["maximum"] = len(pending)
        self.progress["value"] = 0
        self.progress_label.config(text=f"0 / {len(pending)}")

        t = threading.Thread(target=self._merge_worker, args=(pending,), daemon=True)
        t.start()

    def _merge_worker(self, paths: list[str]):
        done = 0
        total = len(paths)
        for path in paths:
            info = self._rows[path]
            iid = info["iid"]
            self._msg_queue.put(("status", iid, "Merging..."))
            self._msg_queue.put(("log", f"Processing: {os.path.basename(path)}"))
            try:
                html_path = merge_from_zip(
                    path,
                    progress_callback=lambda msg: self._msg_queue.put(("log", msg)),
                )
                info["output"] = html_path
                self._msg_queue.put(("status", iid, "Done"))
            except Exception as e:
                self._msg_queue.put(("status", iid, f"Error: {e}"))

            done += 1
            self._msg_queue.put(("progress", done, total))

        self._msg_queue.put(("finished", done, total))

    # ---- Queue polling (runs on main thread) ------------------------------

    def _poll_queue(self):
        try:
            while True:
                msg = self._msg_queue.get_nowait()
                kind = msg[0]

                if kind == "status":
                    _, iid, text = msg
                    self.tree.set(iid, "status", text)

                elif kind == "progress":
                    _, done, total = msg
                    self.progress["value"] = done
                    self.progress_label.config(text=f"{done} / {total}")

                elif kind == "log":
                    self.status_var.set(msg[1])

                elif kind == "finished":
                    _, done, total = msg
                    self._merging = False
                    self.merge_btn.state(["!disabled"])
                    self.status_var.set(
                        f"Done — merged {done} of {total} file{'s' if total != 1 else ''}."
                    )
        except queue.Empty:
            pass

        self.after(80, self._poll_queue)

    # ---- Preview / Open folder --------------------------------------------

    def _selected_output(self) -> str | None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo(APP_TITLE, "Select a row first.")
            return None
        iid = sel[0]
        for info in self._rows.values():
            if info["iid"] == iid:
                if not info["output"]:
                    messagebox.showinfo(APP_TITLE, "This file hasn't been merged yet.")
                    return None
                return info["output"]
        return None

    def _preview(self):
        path = self._selected_output()
        if path and os.path.isfile(path):
            webbrowser.open(f"file://{path}")

    def _open_folder(self):
        path = self._selected_output()
        if not path:
            return
        folder = os.path.dirname(path)
        if not os.path.isdir(folder):
            return
        system = platform.system()
        if system == "Darwin":
            subprocess.Popen(["open", folder])
        elif system == "Windows":
            subprocess.Popen(["explorer", folder])
        else:
            subprocess.Popen(["xdg-open", folder])

    def _on_double_click(self, _event):
        self._preview()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
