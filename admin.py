import socket
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.text import Text
from rich import box
import ctypes
import ctypes.wintypes
import threading

from update import run_update_check   # update check module


APP_VERSION = "1.0"
BROADCAST_PORT = 50000
DEFAULT_TOKEN = "SgiVeDLUQsZ9PnY4ERxkLWjBmLfuA5"  # simple authentication key

console = Console()

# ==========================
# Windows Hotkey Integration
# ==========================
HOTKEY_ID = 1  # unique ID for the hotkey
MOD_CONTROL = 0x0002
MOD_ALT = 0x0001
VK_A = 0x41   # virtual key code for "A"

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


def bring_to_front():
    """Force the console window on top"""
    hWnd = kernel32.GetConsoleWindow()
    if hWnd:
        user32.ShowWindow(hWnd, 5)   # SW_SHOW
        user32.SetForegroundWindow(hWnd)


def register_hotkey():
    """Register Ctrl+Alt+A as global hotkey"""
    if not user32.RegisterHotKey(None, HOTKEY_ID, MOD_CONTROL | MOD_ALT, VK_A):
        console.print("[red]Failed to register hotkey![/]")
    else:
        console.print("[green]Hotkey registered: Ctrl+Alt+A[/]")

    # Run a loop to listen for WM_HOTKEY messages
    def hotkey_listener():
        msg = ctypes.wintypes.MSG()
        while True:
            if user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                if msg.message == 0x0312:  # WM_HOTKEY
                    bring_to_front()
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))

    threading.Thread(target=hotkey_listener, daemon=True).start()


# ==========================
# Networking
# ==========================
def send_message(msg):
    """Send message over LAN using UDP broadcast"""
    data = f"TOKEN:{DEFAULT_TOKEN}\n{msg}".encode("utf-8")
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.sendto(data, ("<broadcast>", BROADCAST_PORT))
    s.close()


# ==========================
# UI
# ==========================
def show_logo():
    """Display ASCII art logo"""
    logo_text = Text(r"""
 ______ _     __  __  ___  _   _ 
|  ____| |   |  \/  |/ _ \| \ | |
| |__  | |   | \  / | | | |  \| |
|  __| | |   | |\/| | | | | . ` |
| |____| |___| |  | | |_| | |\  |
|______|_____|_|  |_|\___/|_| \_|
    """, style="bold green")

    console.print(Panel.fit(logo_text, title="ELM", border_style="cyan", box=box.DOUBLE))


# ==========================
# Main
# ==========================
def main():
    run_update_check(APP_VERSION)
    console.clear()
    show_logo()
    register_hotkey()   # ✅ setup Ctrl+Alt+A

    console.print("[yellow]Welcome IT Officer[/]")
    console.print("Type messages and press Enter to broadcast.\nType 'exit' to quit.\n", style="dim")

    while True:
        msg = Prompt.ask("[bold cyan]Message[/]").strip()
        if msg.lower() == "exit":
            console.print("[red]Exiting Admin Console...[/]")
            break
        if msg:
            send_message(msg)
            console.print(f"[green][Sent][/green] {msg}\n")


if __name__ == "__main__":
    main()
