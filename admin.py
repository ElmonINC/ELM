import os
import sys
import socket
import winshell
from win32com.client import Dispatch
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.text import Text
from rich import box

APP_NAME = "Admin App"
APP_VERSION = "1.0"
BROADCAST_PORT = 50000
DEFAULT_TOKEN = "SgiVeDLUQsZ9PnY4ERxkLWjBmLfuA5"   # simple authentication key

console = Console()

# ==========================
# Shortcut Creator
# ==========================
def create_shortcut():
    """Create a desktop shortcut for this app if not already present."""
    desktop = winshell.desktop()
    shortcut_path = os.path.join(desktop, f"{APP_NAME}.lnk")

    if not os.path.exists(shortcut_path):
        exe_path = sys.argv[0]
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortcut(shortcut_path)
        shortcut.Targetpath = exe_path
        shortcut.WorkingDirectory = os.path.dirname(exe_path)
        shortcut.IconLocation = exe_path
        shortcut.save()
        console.print(f"[green]Shortcut created on Desktop: {shortcut_path}[/]")

# ==========================
# Networking
# ==========================
def send_message(msg):
    """Send message via UDP broadcast."""
    data = f"TOKEN:{DEFAULT_TOKEN}\n{msg}".encode("utf-8")
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.sendto(data, ("<broadcast>", BROADCAST_PORT))
    s.close()

def show_logo():
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
    create_shortcut()
    show_logo()

    console.print("[yellow]Welcome IT Officer[/]")
    console.print("Type messages and press Enter to broadcast.\nType 'exit' to quit.\n", style="dim")

    while True:
        msg = Prompt.ask("[bold cyan]Message[/]").strip()
        if msg.lower() == "exit":
            break
        if msg:
            send_message(msg)
            console.print(f"[green][Sent][/green] {msg}\n")

if __name__ == "__main__":
    main()
