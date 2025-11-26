import socket
import threading
import sys
import os
import json
import hmac
import hashlib
import secrets
import time
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.text import Text
from rich import box

BROADCAST_PORT = 50000
CONFIG_FILE = "admin_config.json"
MAX_MESSAGE_LENGTH = 1000
MESSAGE_TIMEOUT = 30  # seconds - reject messages older than this

console = Console()

# Attempt to import hotkey library (optional; gracefully degrade if not available)
HOTKEY_AVAILABLE = False
hotkey_listener = None  # Global reference to keep listener alive
try:
    from pynput import keyboard as kb
    HOTKEY_AVAILABLE = True
except ImportError:
    pass


class SecureMessageSystem:
    def __init__(self):
        # 1. Detect the correct system path for data
        if os.name == 'nt':
            # Windows: %APPDATA% (C:\Users\Name\AppData\Roaming)
            base_path = Path(os.getenv('APPDATA'))
        else:
            # Linux/Mac: ~/.config
            base_path = Path.home() / ".config"
            
        # 2. Define a dedicated folder for your app
        self.app_dir = base_path / "ELM_Secure_Admin"
        
        # 3. Create that folder if it doesn't exist
        try:
            self.app_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            console.print(f"[red]Error creating config directory: {e}[/red]")
            
        # 4. Set the final file path
        self.config_path = self.app_dir / "admin_config.json"
        
        self.secret_key = None
        self.cipher = None
        self.load_or_create_config()
    
    def load_or_create_config(self):
        """Load existing config or create new secure credentials"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    self.secret_key = config['secret_key'].encode()
                    console.print("[green]✓[/green] Loaded existing secure configuration", style="dim")
            except Exception as e:
                console.print(f"[red]Error loading config: {e}[/red]")
                self.create_new_config()
        else:
            self.create_new_config()
        
        # Initialize cipher with the secret key
        self.cipher = Fernet(self.secret_key)
    
    def create_new_config(self):
        """Generate cryptographically secure credentials with guaranteed randomness"""
        console.print("[yellow]Creating new secure configuration...[/yellow]")
        
        # Generate a cryptographically secure key using Fernet (uses os.urandom internally)
        # Guaranteed random key generation on every call
        self.secret_key = Fernet.generate_key()
        
        # Save to config file with restrictive permissions
        config = {
            'secret_key': self.secret_key.decode(),
            'created': time.time(),
            'version': '2.0'
        }
        
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)

            if os.name != 'nt': # Set file permissions (read/write for owner only)
                os.chmod(self.config_path, 0o600) # Unix-like systems
                
            console.print(f"[green]✓[/green] Config saved to: {self.config_path}")
        except Exception as e:
            # Added safety catch so the user sees why it failed
            console.print(f"[bold red]CRITICAL ERROR: Could not write config file![/bold red]")
            console.print(f"Path: {self.config_path}")
            console.print(f"Error: {e}")
        
        
        console.print(f"[green]✓[/green] Created secure configuration at: {self.config_path.absolute()}")
        console.print("[bold yellow]IMPORTANT:[/bold yellow] Share this config file securely with authorized receivers!")
        console.print("[yellow]Keep this file safe - it's required for authentication[/yellow]\n")
    
    def encrypt_message(self, message):
        """Encrypt message with timestamp and HMAC"""
        # Create payload with timestamp
        payload = {
            'message': message,
            'timestamp': time.time(),
            'nonce': secrets.token_hex(16)  # Prevent replay attacks
        }
        
        # Serialize and encrypt
        json_payload = json.dumps(payload).encode()
        encrypted = self.cipher.encrypt(json_payload)
        
        # Create HMAC for integrity verification
        mac = hmac.new(
            self.secret_key,
            encrypted,
            hashlib.sha256
        ).hexdigest()
        
        # Combine encrypted data with MAC
        return json.dumps({
            'data': encrypted.decode(),
            'mac': mac
        })
    
    def validate_message(self, encrypted_payload):
        """Validate and decrypt received message (for receiver side)"""
        try:
            payload = json.loads(encrypted_payload)
            encrypted_data = payload['data'].encode()
            received_mac = payload['mac']
            
            # Verify HMAC
            expected_mac = hmac.new(
                self.secret_key,
                encrypted_data,
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(received_mac, expected_mac):
                return None, "MAC verification failed"
            
            # Decrypt
            decrypted = self.cipher.decrypt(encrypted_data)
            message_data = json.loads(decrypted)
            
            # Check timestamp (prevent replay attacks)
            message_age = time.time() - message_data['timestamp']
            if message_age > MESSAGE_TIMEOUT:
                return None, "Message expired"
            
            return message_data['message'], None
            
        except Exception as e:
            return None, f"Decryption failed: {str(e)}"


def validate_input(message):
    """Validate message input"""
    if not message or not message.strip():
        return False, "Message cannot be empty"
    
    if len(message) > MAX_MESSAGE_LENGTH:
        return False, f"Message too long (max {MAX_MESSAGE_LENGTH} characters)"
    
    # Check for potentially dangerous characters (customize as needed)
    dangerous_chars = ['\x00', '\r']  # null bytes, carriage returns
    if any(char in message for char in dangerous_chars):
        return False, "Message contains invalid characters"
    
    return True, None


def send_message(msg, crypto_system):
    """Send encrypted message over LAN using UDP broadcast"""
    try:
        # Encrypt the message
        encrypted_payload = crypto_system.encrypt_message(msg)
        
        # Send over UDP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.sendto(encrypted_payload.encode("utf-8"), ("<broadcast>", BROADCAST_PORT))
        s.close()
        
        return True, None
    except Exception as e:
        return False, str(e)


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

    console.print(Panel.fit(logo_text, title="ELM SECURE", border_style="cyan", box=box.DOUBLE))


def setup_hotkey():
    """Setup global hotkey Alt+Ctrl+E to activate the admin console."""
    global hotkey_listener
    
    if not HOTKEY_AVAILABLE:
        console.print("[yellow][NOTE][/yellow] Global hotkey disabled (install 'pynput' package to enable)", style="dim")
        return
    
    try:
        def on_activate():
            """Callback when Alt+Ctrl+E is pressed."""
            console.print("\n[bold yellow]⚡ Alt+Ctrl+E triggered - Admin console is active[/bold yellow]\n")
        
        # Define hotkey combination
        hotkey = kb.HotKey(
            kb.HotKey.parse('<alt>+<ctrl>+e'),
            on_activate
        )
        
        # Start listener with global reference to prevent garbage collection
        def for_canonical(f):
            return lambda k: f(hotkey_listener.canonical(k))
        
        # Create and store listener globally so it stays alive
        hotkey_listener = kb.Listener(
            on_press=for_canonical(hotkey.press),
            on_release=for_canonical(hotkey.release)
        )
        hotkey_listener.start()
        
        console.print("[green]✓[/green] Global hotkey (Alt+Ctrl+E) registered", style="dim")
    except Exception as e:
        console.print(f"[yellow][WARNING][/yellow] Failed to register hotkey: {e}", style="dim")


def main():
    """Admin console loop with encryption and authentication"""
    console.clear()
    show_logo()
    
    # Initialize secure messaging system
    console.print("[cyan]Initializing secure messaging system...[/cyan]")
    crypto_system = SecureMessageSystem()
    
    # Setup global hotkey (Alt+Ctrl+E)
    setup_hotkey()
    
    console.print("\n[yellow]Welcome IT Officer[/]")
    console.print("[bold green]🔒 Secure Mode: All messages are encrypted[/bold green]")
    console.print("Type messages and press Enter to broadcast.\nType 'exit' to quit.", style="dim")
    console.print(f"[dim]Max message length: {MAX_MESSAGE_LENGTH} characters[/dim]\n")

    while True:
        try:
            msg = Prompt.ask("[bold cyan]Message[/]").strip()
            
            if msg.lower() == "exit":
                console.print("[red]Exiting Admin Console...[/]")
                break
            
            # Validate input
            is_valid, error = validate_input(msg)
            if not is_valid:
                console.print(f"[red][ERROR][/red] {error}")
                continue
            
            # Send encrypted message
            success, error = send_message(msg, crypto_system)
            
            if success:
                console.print(f"[green]✓ [Sent Encrypted][/green] {msg[:50]}{'...' if len(msg) > 50 else ''}\n")
            else:
                console.print(f"[red][ERROR][/red] Failed to send: {error}\n")
                
        except KeyboardInterrupt:
            console.print("\n[red]Interrupted. Exiting...[/]")
            break
        except Exception as e:
            console.print(f"[red][ERROR][/red] {e}", style="dim")


if __name__ == "__main__":
    main()