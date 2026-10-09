from __future__ import annotations

import json
import os
import tkinter as tk
import urllib.request
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

from automation_controller import AutomationController

BASE_DIR = Path(__file__).resolve().parent
CONFIG = json.loads((BASE_DIR / "config.json").read_text(encoding="utf-8"))
LOG_FILE = BASE_DIR / CONFIG["folders"]["logs"] / "automation.log"

COLORS = {
    "window": "#0d1117",
    "panel": "#161b22",
    "panel_alt": "#1c2128",
    "border": "#30363d",
    "text": "#e6edf3",
    "muted": "#8b949e",
    "blue": "#2f81f7",
    "blue_hover": "#388bfd",
    "green": "#238636",
    "green_hover": "#2ea043",
    "red": "#da3633",
    "input": "#0d1117",
    "terminal": "#010409",
}


class Dashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("WhatsApp Video Sender")
        self.geometry("1060x740")
        self.minsize(880, 640)
        self.configure(bg=COLORS["window"])
        self.controller = AutomationController(BASE_DIR)
        self._last_log_size = 0
        self.recipient_var = tk.StringVar(value=str(CONFIG.get("recipient", "")))
        self.active_view = tk.StringVar(value="Dashboard")
        self._configure_styles()
        self._build_ui()
        self._refresh()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _configure_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=COLORS["window"])
        style.configure("Panel.TFrame", background=COLORS["panel"])
        style.configure("PanelAlt.TFrame", background=COLORS["panel_alt"])
        style.configure("TLabel", background=COLORS["window"], foreground=COLORS["text"], font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=COLORS["window"], foreground=COLORS["muted"], font=("Segoe UI", 9))
        style.configure("Panel.TLabel", background=COLORS["panel"], foreground=COLORS["text"], font=("Segoe UI", 10))
        style.configure("PanelMuted.TLabel", background=COLORS["panel"], foreground=COLORS["muted"], font=("Segoe UI", 9))
        style.configure("Header.TLabel", background=COLORS["window"], foreground=COLORS["text"], font=("Segoe UI", 19, "bold"))
        style.configure("Section.TLabel", background=COLORS["window"], foreground=COLORS["text"], font=("Segoe UI", 13, "bold"))
        style.configure("CardTitle.TLabel", background=COLORS["panel"], foreground=COLORS["muted"], font=("Segoe UI", 9))
        style.configure("CardValue.TLabel", background=COLORS["panel"], foreground=COLORS["text"], font=("Segoe UI", 17, "bold"))
        style.configure("TButton", background=COLORS["panel_alt"], foreground=COLORS["text"], bordercolor=COLORS["border"], padding=(12, 8), font=("Segoe UI", 9, "bold"), focusthickness=0)
        style.map("TButton", background=[("active", "#30363d"), ("disabled", COLORS["panel"])], foreground=[("disabled", COLORS["muted"])])
        style.configure("Primary.TButton", background=COLORS["green"], foreground="#ffffff", bordercolor=COLORS["green"], padding=(15, 9), font=("Segoe UI", 9, "bold"))
        style.map("Primary.TButton", background=[("active", COLORS["green_hover"]), ("disabled", COLORS["panel_alt"])], bordercolor=[("active", COLORS["green_hover"])])
        style.configure("Stop.TButton", background=COLORS["panel_alt"], foreground="#ff7b72", bordercolor=COLORS["border"], padding=(12, 9), font=("Segoe UI", 9, "bold"))
        style.map("Stop.TButton", background=[("active", "#3d2024"), ("disabled", COLORS["panel"])])
        style.configure("Nav.TButton", background=COLORS["window"], foreground=COLORS["muted"], bordercolor=COLORS["window"], padding=(12, 10), anchor="w", font=("Segoe UI", 10))
        style.map("Nav.TButton", background=[("active", COLORS["panel_alt"])], foreground=[("active", COLORS["text"])])
        style.configure("ActiveNav.TButton", background="#1f2d3d", foreground="#79c0ff", bordercolor="#1f6feb", padding=(12, 10), anchor="w", font=("Segoe UI", 10, "bold"))
        style.map("ActiveNav.TButton", background=[("active", "#263b50")])
        style.configure("TEntry", fieldbackground=COLORS["input"], foreground=COLORS["text"], insertcolor=COLORS["text"], bordercolor=COLORS["border"], padding=9)
        style.map("TEntry", bordercolor=[("focus", COLORS["blue"])])
        style.configure("TNotebook", background=COLORS["window"], borderwidth=0, tabmargins=0)
        style.configure("TNotebook.Tab", background=COLORS["panel"], foreground=COLORS["muted"], padding=(13, 8), bordercolor=COLORS["border"], font=("Segoe UI", 9, "bold"))
        style.map("TNotebook.Tab", background=[("selected", COLORS["panel_alt"])], foreground=[("selected", COLORS["text"])])
        style.configure("TLabelframe", background=COLORS["panel"], foreground=COLORS["text"], bordercolor=COLORS["border"], relief="solid")
        style.configure("TLabelframe.Label", background=COLORS["panel"], foreground=COLORS["muted"], font=("Segoe UI", 9, "bold"))
        style.configure("TScrollbar", background=COLORS["panel_alt"], troughcolor=COLORS["window"], bordercolor=COLORS["window"], arrowcolor=COLORS["muted"])

    def _build_ui(self):
        shell = ttk.Frame(self, padding=0)
        shell.pack(fill="both", expand=True)

        header = ttk.Frame(shell, padding=(24, 20, 24, 16))
        header.pack(fill="x")
        brand = tk.Frame(header, bg=COLORS["blue"], width=38, height=38, highlightthickness=0)
        brand.pack(side="left", padx=(0, 12))
        brand.pack_propagate(False)
        tk.Label(brand, text="▶", bg=COLORS["blue"], fg="#ffffff", font=("Segoe UI", 15, "bold")).pack(expand=True)
        heading = ttk.Frame(header)
        heading.pack(side="left", fill="x", expand=True)
        ttk.Label(heading, text="WhatsApp Video Sender", style="Header.TLabel").pack(anchor="w")
        ttk.Label(heading, text="A quiet place to manage your video queue", style="Muted.TLabel").pack(anchor="w", pady=(3, 0))
        self.header_status = tk.Label(header, text="●  Checking status", bg=COLORS["window"], fg=COLORS["muted"], font=("Segoe UI", 9, "bold"))
        self.header_status.pack(side="right", anchor="center", padx=(10, 0))

        body = ttk.Frame(shell)
        body.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        sidebar = ttk.Frame(body, style="Panel.TFrame", padding=(10, 12))
        sidebar.pack(side="left", fill="y", padx=(0, 14))
        ttk.Label(sidebar, text="WORKSPACE", style="PanelMuted.TLabel").pack(anchor="w", padx=9, pady=(7, 10))
        self.nav_buttons = {}
        for name, symbol in (("Dashboard", "▦"), ("Chrome View", "◉"), ("Activity Logs", "≡")):
            button = ttk.Button(sidebar, text=f"{symbol}   {name}", style="ActiveNav.TButton" if name == "Dashboard" else "Nav.TButton", command=lambda item=name: self._show_view(item))
            button.pack(fill="x", pady=2)
            self.nav_buttons[name] = button
        ttk.Separator(sidebar, orient="horizontal").pack(fill="x", padx=8, pady=14)
        ttk.Label(sidebar, text="QUICK ACCESS", style="PanelMuted.TLabel").pack(anchor="w", padx=9, pady=(0, 8))
        ttk.Button(sidebar, text="Open ToSend folder", command=lambda: self._open_folder("to_send")).pack(fill="x", padx=2, pady=3)
        ttk.Button(sidebar, text="Open Sent folder", command=lambda: self._open_folder("sent")).pack(fill="x", padx=2, pady=3)
        ttk.Label(sidebar, text="LOCAL AUTOMATION", style="PanelMuted.TLabel").pack(side="bottom", anchor="w", padx=9, pady=(16, 3))
        ttk.Label(sidebar, text="Runs on this computer", style="PanelMuted.TLabel").pack(side="bottom", anchor="w", padx=9)

        content = ttk.Frame(body)
        content.pack(side="left", fill="both", expand=True)
        self.views = {}
        self.dashboard_tab = ttk.Frame(content)
        self.chrome_tab = ttk.Frame(content)
        self.logs_tab = ttk.Frame(content)
        self.views["Dashboard"] = self.dashboard_tab
        self.views["Chrome View"] = self.chrome_tab
        self.views["Activity Logs"] = self.logs_tab
        for view in self.views.values():
            view.grid(row=0, column=0, sticky="nsew")
        content.rowconfigure(0, weight=1)
        content.columnconfigure(0, weight=1)
        self._build_dashboard_tab()
        self._build_chrome_tab()
        self._build_logs_tab()
        self._show_view("Dashboard")

    def _show_view(self, name):
        self.active_view.set(name)
        self.views[name].tkraise()
        for item, button in self.nav_buttons.items():
            button.configure(style="ActiveNav.TButton" if item == name else "Nav.TButton")
        if name == "Chrome View":
            self._update_chrome_view()

    def _build_dashboard_tab(self):
        ttk.Label(self.dashboard_tab, text="Overview", style="Section.TLabel").pack(anchor="w", pady=(3, 3))
        ttk.Label(self.dashboard_tab, text="Manage the destination and keep an eye on the send queue.", style="Muted.TLabel").pack(anchor="w", pady=(0, 16))

        recipient_frame = ttk.LabelFrame(self.dashboard_tab, text="  RECIPIENT  ", padding=14)
        recipient_frame.pack(fill="x", pady=(0, 14))
        ttk.Label(recipient_frame, text="WhatsApp contact name", style="Panel.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 12))
        self.recipient_entry = ttk.Entry(recipient_frame, textvariable=self.recipient_var)
        self.recipient_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        self.save_recipient_button = ttk.Button(recipient_frame, text="Save recipient", command=lambda: self._save_recipient(show_message=True))
        self.save_recipient_button.grid(row=0, column=2, sticky="e")
        recipient_frame.columnconfigure(1, weight=1)

        cards = ttk.Frame(self.dashboard_tab)
        cards.pack(fill="x")
        self.status_card = self._make_card(cards, "AUTOMATION", "Stopped", 0)
        self.chrome_card = self._make_card(cards, "CHROME CONNECTION", "Checking…", 1)
        self.queue_card = self._make_card(cards, "VIDEOS WAITING", "0", 2)

        current = ttk.LabelFrame(self.dashboard_tab, text="  CURRENT OPERATION  ", padding=16)
        current.pack(fill="x", pady=(16, 14))
        self.current_file = ttk.Label(current, text="No video currently sending", style="Panel.TLabel", font=("Segoe UI", 12, "bold"))
        self.current_file.pack(anchor="w")
        self.current_stage = ttk.Label(current, text="Start the automation to monitor the queue.", style="PanelMuted.TLabel", wraplength=660)
        self.current_stage.pack(anchor="w", pady=(6, 0))
        self.recipient_label = ttk.Label(current, text=f"Recipient: {CONFIG.get('recipient', 'Not configured')}", style="PanelMuted.TLabel")
        self.recipient_label.pack(anchor="w", pady=(13, 0))

        actions = ttk.Frame(self.dashboard_tab)
        actions.pack(fill="x", pady=(0, 10))
        self.start_button = ttk.Button(actions, text="▶  Start automation", style="Primary.TButton", command=self._start)
        self.start_button.pack(side="left", padx=(0, 8))
        self.stop_button = ttk.Button(actions, text="■  Stop automation", style="Stop.TButton", command=self._stop)
        self.stop_button.pack(side="left")

        note = tk.Frame(self.dashboard_tab, bg=COLORS["panel_alt"], highlightbackground=COLORS["border"], highlightthickness=1)
        note.pack(fill="x", pady=(5, 0))
        tk.Label(note, text="ⓘ", bg=COLORS["panel_alt"], fg="#79c0ff", font=("Segoe UI", 12, "bold")).pack(side="left", padx=(12, 8), pady=10)
        tk.Label(note, text="Stopping is graceful. The current video operation can finish, but the next queued video will not start.", bg=COLORS["panel_alt"], fg=COLORS["muted"], font=("Segoe UI", 9), anchor="w", justify="left", wraplength=650).pack(side="left", fill="x", expand=True, padx=(0, 12), pady=10)

    def _make_card(self, parent, title, value, column):
        card = ttk.Frame(parent, style="Panel.TFrame", padding=(14, 13))
        card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 9, 0))
        parent.columnconfigure(column, weight=1, uniform="status_cards")
        ttk.Label(card, text=title, style="CardTitle.TLabel").pack(anchor="w")
        label = ttk.Label(card, text=value, style="CardValue.TLabel")
        label.pack(anchor="w", pady=(9, 0))
        return label

    def _build_chrome_tab(self):
        ttk.Label(self.chrome_tab, text="Chrome connection", style="Section.TLabel").pack(anchor="w", pady=(3, 3))
        ttk.Label(self.chrome_tab, text="Connection details for your existing Chrome session.", style="Muted.TLabel").pack(anchor="w", pady=(0, 16))
        panel = ttk.Frame(self.chrome_tab, style="Panel.TFrame", padding=16)
        panel.pack(fill="x")
        self.chrome_connection_badge = tk.Label(panel, text="●  Checking connection", bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 10, "bold"), anchor="w")
        self.chrome_connection_badge.pack(anchor="w", pady=(0, 12))
        self.chrome_details = tk.Text(panel, height=7, wrap="word", font=("Consolas", 10), bg=COLORS["terminal"], fg=COLORS["text"], insertbackground=COLORS["text"], relief="flat", padx=12, pady=12, highlightthickness=1, highlightbackground=COLORS["border"], state="disabled")
        self.chrome_details.pack(fill="x", pady=(0, 14))
        actions = ttk.Frame(panel, style="Panel.TFrame")
        actions.pack(anchor="w")
        ttk.Button(actions, text="Check connection", command=self._update_chrome_view).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Bring Chrome to front", command=self._bring_chrome_forward).pack(side="left")
        ttk.Label(self.chrome_tab, text="The live WhatsApp page stays in its own Chrome window; this panel does not embed the browser.", style="Muted.TLabel", wraplength=680).pack(anchor="w", pady=(13, 0))
        self._update_chrome_view()

    def _build_logs_tab(self):
        bar = ttk.Frame(self.logs_tab)
        bar.pack(fill="x", pady=(3, 12))
        title_area = ttk.Frame(bar)
        title_area.pack(side="left", fill="x", expand=True)
        ttk.Label(title_area, text="Activity logs", style="Section.TLabel").pack(anchor="w")
        ttk.Label(title_area, text="Live output from the automation process.", style="Muted.TLabel").pack(anchor="w", pady=(3, 0))
        ttk.Button(bar, text="Open log file", command=self._open_log_file).pack(side="right", anchor="center")
        log_panel = ttk.Frame(self.logs_tab, style="Panel.TFrame", padding=1)
        log_panel.pack(fill="both", expand=True)
        self.log_text = tk.Text(log_panel, wrap="none", font=("Cascadia Mono", 9), bg=COLORS["terminal"], fg="#c9d1d9", insertbackground=COLORS["text"], selectbackground="#1f6feb", relief="flat", padx=13, pady=12)
        yscroll = ttk.Scrollbar(log_panel, orient="vertical", command=self.log_text.yview)
        xscroll = ttk.Scrollbar(log_panel, orient="horizontal", command=self.log_text.xview)
        self.log_text.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        log_panel.rowconfigure(0, weight=1)
        log_panel.columnconfigure(0, weight=1)
        self.log_text.configure(state="disabled")

    def _save_recipient(self, show_message: bool = True) -> bool:
        recipient = self.recipient_var.get().strip()
        if not recipient:
            messagebox.showwarning("Recipient required", "Enter the WhatsApp contact name before saving or starting.")
            self.recipient_entry.focus_set()
            return False
        if self.controller.is_running():
            messagebox.showinfo("Automation running", "Stop the automation before changing the recipient.")
            return False
        CONFIG["recipient"] = recipient
        config_path = BASE_DIR / "config.json"
        temp_path = config_path.with_suffix(".tmp")
        try:
            temp_path.write_text(json.dumps(CONFIG, indent=4) + "\n", encoding="utf-8")
            temp_path.replace(config_path)
        except Exception as exc:
            messagebox.showerror("Save failed", f"Could not save the recipient to config.json:\n{exc}")
            return False
        self.recipient_label.configure(text=f"Recipient: {recipient}")
        if show_message:
            messagebox.showinfo("Recipient saved", f"The automation will send videos to: {recipient}")
        return True

    def _start(self):
        if not self._save_recipient(show_message=False):
            return
        ok, message = self.controller.start()
        if ok:
            self._append_log_line(f"{datetime.now():%Y-%m-%d %H:%M:%S} | DASHBOARD | {message}")
        else:
            messagebox.showinfo("Automation", message)
        self._refresh()

    def _stop(self):
        if not messagebox.askyesno("Stop automation", "Request a safe stop after the current video operation finishes?"):
            return
        ok, message = self.controller.stop()
        if ok:
            self._append_log_line(f"{datetime.now():%Y-%m-%d %H:%M:%S} | DASHBOARD | {message}")
            messagebox.showinfo("Stop requested", message)
        else:
            messagebox.showinfo("Automation", message)
        self._refresh()

    def _open_folder(self, key):
        path = BASE_DIR / CONFIG["folders"][key]
        path.mkdir(parents=True, exist_ok=True)
        os.startfile(str(path))

    def _open_log_file(self):
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        LOG_FILE.touch(exist_ok=True)
        os.startfile(str(LOG_FILE))

    def _append_log_line(self, line):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", line.rstrip() + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _read_new_logs(self):
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not LOG_FILE.exists():
            return
        try:
            size = LOG_FILE.stat().st_size
            if size < self._last_log_size:
                self._last_log_size = 0
            if size == self._last_log_size:
                return
            with LOG_FILE.open("r", encoding="utf-8", errors="replace") as file:
                file.seek(self._last_log_size)
                chunk = file.read()
                self._last_log_size = file.tell()
            if chunk:
                self.log_text.configure(state="normal")
                self.log_text.insert("end", chunk)
                self.log_text.see("end")
                self.log_text.configure(state="disabled")
        except OSError:
            pass

    def _connection_info(self):
        port = CONFIG["chrome"]["debug_port"]
        url = f"http://127.0.0.1:{port}/json/version"
        try:
            with urllib.request.urlopen(url, timeout=0.7) as response:
                data = json.loads(response.read().decode("utf-8", errors="replace"))
            browser = data.get("Browser", "Chrome")
            return True, f"Connected to Chrome remote debugging on port {port}.\nBrowser: {browser}\nWebSocket endpoint available."
        except Exception:
            return False, f"Chrome is not reachable on port {port}.\nStart Chrome using start_chrome.bat, then make sure WhatsApp Web is open."

    def _update_chrome_view(self):
        connected, detail = self._connection_info()
        self.chrome_card.configure(text="Connected" if connected else "Disconnected")
        self.chrome_connection_badge.configure(text="●  Connected" if connected else "●  Disconnected", fg="#3fb950" if connected else "#f85149")
        self.chrome_details.configure(state="normal")
        self.chrome_details.delete("1.0", "end")
        self.chrome_details.insert("1.0", detail)
        self.chrome_details.configure(state="disabled")

    def _bring_chrome_forward(self):
        if os.name != "nt":
            messagebox.showinfo("Chrome", "Bringing Chrome forward is supported on Windows.")
            return
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            found = []
            EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

            def callback(hwnd, _):
                if not user32.IsWindowVisible(hwnd):
                    return True
                length = user32.GetWindowTextLengthW(hwnd)
                if length <= 0:
                    return True
                buffer = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buffer, length + 1)
                if "chrome" in buffer.value.lower():
                    found.append(hwnd)
                return True

            user32.EnumWindows(EnumWindowsProc(callback), 0)
            if not found:
                messagebox.showwarning("Chrome not found", "No visible Chrome window was found. Start it with start_chrome.bat.")
                return
            user32.ShowWindow(found[0], 9)
            user32.SetForegroundWindow(found[0])
        except Exception as exc:
            messagebox.showerror("Chrome", f"Could not bring Chrome to front:\n{exc}")

    def _refresh(self):
        status = self.controller.read_status()
        process_running = self.controller.is_running()
        current_status = status.get("status", "Stopped")
        self.status_card.configure(text=current_status)
        self.current_file.configure(text=status.get("current_file") or "No video currently sending")
        self.current_stage.configure(text=status.get("stage", "Waiting"))
        self.recipient_label.configure(text=f"Recipient: {CONFIG.get('recipient', 'Not configured')}")
        self.header_status.configure(text=f"●  {current_status}", fg="#3fb950" if process_running else COLORS["muted"])

        to_send = BASE_DIR / CONFIG["folders"]["to_send"]
        to_send.mkdir(parents=True, exist_ok=True)
        extensions = {extension.lower() for extension in CONFIG["video_extensions"]}
        count = sum(1 for path in to_send.iterdir() if path.is_file() and path.suffix.lower() in extensions)
        self.queue_card.configure(text=str(count))
        connected, _ = self._connection_info()
        self.chrome_card.configure(text="Connected" if connected else "Disconnected")

        if process_running:
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
            self.recipient_entry.configure(state="disabled")
            self.save_recipient_button.configure(state="disabled")
        else:
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
            self.recipient_entry.configure(state="normal")
            self.save_recipient_button.configure(state="normal")

        self._read_new_logs()
        self.after(1000, self._refresh)

    def _on_close(self):
        if self.controller.is_running():
            if not messagebox.askyesno("Close dashboard", "Automation is running. Close only the dashboard and leave automation running?"):
                return
        self.destroy()


if __name__ == "__main__":
    Dashboard().mainloop()
