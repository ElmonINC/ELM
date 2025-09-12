import socket
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.text import Text
from rich import box
from update import run_update_check   # update check module


APP_VERSION = "1.0"
BROADCAST_PORT = 50000
DEFAULT_TOKEN = "SgiVeDLUQsZ9PnY4ERxkLWjBmLfuA5"  # simple authentication key

def main():
    run_update_check(APP_VERSION)
    print("Running ELM Admin...")

console = Console()

def send_message(msg):
    """Send message over LAN using UDP broadcast"""
    data = f"TOKEN:{DEFAULT_TOKEN}\n{msg}".encode("utf-8")
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.sendto(data, ("<broadcast>", BROADCAST_PORT))
    s.close()

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



def main():
    """Admin console loop"""
    console.clear()
    show_logo()
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
