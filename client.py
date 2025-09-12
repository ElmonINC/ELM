import socket
import threading
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import ttkbootstrap as tb
import time
import queue

from update import run_update_check   # ✅ correct import


APP_VERSION = "1.0"
BROADCAST_PORT = 50000
DEFAULT_TOKEN = "SgiVeDLUQsZ9PnY4ERxkLWjBmLfuA5"
POPUP_DURATION = 60  # seconds

def main():
    run_update_check(APP_VERSION)
    print("Running ELM Client...")

class GlassPopup:
    def __init__(self, message):
        self.root = tb.Window(themename="cyborg")  # dark modern theme
        self.root.withdraw()

        # Popup window
        top = tb.Toplevel(self.root)
        top.title("Message")
        top.overrideredirect(True)  # remove default borders
        top.attributes("-topmost", True)
        top.configure(bg="#1a1a1a")  # fallback color
        top.wm_attributes("-alpha", 0.9)  # transparency (glass-like)

        # Rounded frame simulation
        frame = ttk.Frame(top, padding=20, style="Glass.TFrame")
        frame.pack(fill="both", expand=True)

        # Logo
        try:
            img = Image.open("assets/logo.png").resize((80, 80))
            logo = ImageTk.PhotoImage(img)
            logo_label = ttk.Label(frame, image=logo, background="#1a1a1a")
            logo_label.image = logo
            logo_label.pack(pady=(10, 5))
        except:
            pass

        # Message
        msg_label = ttk.Label(
            frame,
            text=message,
            wraplength=400,
            justify="center",
            font=("Segoe UI", 12, "bold"),
            foreground="white",
            background="#1a1a1a"
        )
        msg_label.pack(pady=(5, 15))

        # Close button
        close_btn = ttk.Button(frame, text="✖ Close", style="danger.TButton", command=top.destroy)
        close_btn.pack(pady=(0, 10))

        # Position center
        top.update_idletasks()
        w = top.winfo_width()
        h = top.winfo_height()
        sw = top.winfo_screenwidth()
        sh = top.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        top.geometry(f"{w}x{h}+{x}+{y}")

        # Auto close
        top.after(POPUP_DURATION * 1000, top.destroy)

        self.root.mainloop()

class ClientListener:
    def __init__(self, token=DEFAULT_TOKEN, port=BROADCAST_PORT):
        self.token = token
        self.port = port
        self.sock = None
        self.running = False
        self.msg_queue = queue.Queue()

    def start(self):
        threading.Thread(target=self._listen_loop, daemon=True).start()
        threading.Thread(target=self._popup_consumer, daemon=True).start()

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
            except:
                pass

    def _popup_consumer(self):
        while True:
            msg = self.msg_queue.get()
            try:
                GlassPopup(msg)
            except:
                pass

if __name__ == "__main__":
    main()
    listener = ClientListener()
    listener.start()
    while True:
        time.sleep(1)
