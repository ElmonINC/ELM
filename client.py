# ELM Client Application
import os
import sys
import subprocess
import socket
import threading
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import ttkbootstrap as tb
import time
import queue

from update import run_update_check

APP_VERSION = "1.1"
BROADCAST_PORT = 50000
DEFAULT_TOKEN = "SgiVeDLUQsZ9"  # simple authentication key
POPUP_DURATION = 60  # seconds


# ==========================
# Hidden Startup Task Helper
# ==========================
def ensure_startup_task_hidden():
    """Ensure the client app runs at startup via a hidden scheduled task."""
    task_name = "ELMClientApp"
    exe_path = sys.executable  # Path to exe when frozen with PyInstaller

    if exe_path.lower().endswith("python.exe"):
        # Running as script, use script path
        exe_path = os.path.abspath(sys.argv[0])

    # Check if task already exists
    check_cmd = f'schtasks /query /tn "{task_name}"'
    try:
        subprocess.check_output(check_cmd, shell=True, stderr=subprocess.DEVNULL)
        return  # Task exists
    except subprocess.CalledProcessError:
        pass  # Not found → create it

    # Create hidden task on logon
    create_cmd = (
        f'schtasks /create /f /tn "{task_name}" '
        f'/tr "{exe_path}" /sc onlogon /rl HIGHEST /it /np /z'
    )
    os.system(create_cmd)


# ==========================
# Popup System
# ==========================
class GlassPopup:
    def __init__(self, root):
        self.root = root
        self.top = None
        self.frame = None
        self.messages = []
        self.close_timer = None  # track auto-close timer

    def _create_popup(self):
        self.top = tb.Toplevel(self.root)
        self.top.title("Messages")
        self.top.overrideredirect(True)
        self.top.attributes("-topmost", True)
        self.top.configure(bg="#1a1a1a")
        self.top.wm_attributes("-alpha", 0.95)

        self.frame = ttk.Frame(self.top, padding=20, style="Glass.TFrame")
        self.frame.pack(fill="both", expand=True)

        # Buttons
        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill="x", pady=(10, 0))

        close_latest = ttk.Button(
            btn_frame, text="❌", style="warning.TButton", command=self.close_latest
        )
        close_latest.pack(side="left", expand=True, padx=5)

        close_all = ttk.Button(
            btn_frame, text="🗑", style="danger.TButton", command=self.close_all
        )
        close_all.pack(side="right", expand=True, padx=5)

        # Position center
        self.top.update_idletasks()
        w, h = self.top.winfo_width(), self.top.winfo_height()
        sw, sh = self.top.winfo_screenwidth(), self.top.winfo_screenheight()
        x, y = (sw - w) // 2, (sh - h) // 2
        self.top.geometry(f"+{x}+{y}")

    def show(self, message):
        if self.top is None or not tk.Toplevel.winfo_exists(self.top):
            self._create_popup()

        # Add message under previous ones
        label = ttk.Label(
            self.frame,
            text=message,
            wraplength=400,
            justify="left",
            font=("Segoe UI", 11),
            foreground="white",
            background="#1a1a1a"
        )
        label.pack(anchor="w", pady=2)
        self.messages.append(label)

        # Reset timer → only latest message’s timer counts
        if self.close_timer:
            self.top.after_cancel(self.close_timer)
        self.close_timer = self.top.after(POPUP_DURATION * 1000, self.close_all)

    def close_latest(self):
        if self.messages:
            latest = self.messages.pop()
            latest.destroy()
        if not self.messages and self.top:
            self._destroy_popup()

    def close_all(self):
        # Terminate timer instantly
        if self.close_timer:
            self.top.after_cancel(self.close_timer)
            self.close_timer = None

        # Remove all messages
        for lbl in self.messages:
            lbl.destroy()
        self.messages.clear()

        self._destroy_popup()

    def _destroy_popup(self):
        if self.top:
            self.top.destroy()
            self.top = None


# ==========================
# Listener
# ==========================
class ClientListener:
    def __init__(self, root, popup, token=DEFAULT_TOKEN, port=BROADCAST_PORT):
        self.root = root
        self.popup = popup
        self.token = token
        self.port = port
        self.sock = None
        self.running = False
        self.msg_queue = queue.Queue()

    def start(self):
        threading.Thread(target=self._listen_loop, daemon=True).start()
        self._check_queue()

    def _listen_loop(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('', self.port))
        self.running = True
        while self.running:
            try:
                data, _ = self.sock.recvfrom(8192)
                text = data.decode("utf-8", errors="ignore")
                if text.startswith("TOKEN:"):
                    token, msg = text.split("\n", 1)
                    token = token.split("TOKEN:", 1)[1].strip()
                    if token == self.token:
                        self.msg_queue.put(msg.strip())
            except Exception as e:
                print("Listener error:", e)

    def _check_queue(self):
        try:
            while not self.msg_queue.empty():
                msg = self.msg_queue.get_nowait()
                self.popup.show(msg)
        except queue.Empty:
            pass
        self.root.after(500, self._check_queue)


# ==========================
# Main
# ==========================
def main():
    run_update_check(APP_VERSION)
    ensure_startup_task_hidden()  # ✅ silently ensure hidden startup task
    print("Running ELM Client...")

    root = tb.Window(themename="cyborg")
    root.withdraw()  # hide base window

    popup = GlassPopup(root)
    listener = ClientListener(root, popup)
    listener.start()

    root.mainloop()


if __name__ == "__main__":
    main()
