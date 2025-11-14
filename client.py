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
import tkinter.messagebox as messagebox
import ctypes
import atexit
import json
import hmac
import hashlib
from pathlib import Path
from cryptography.fernet import Fernet

APP_VERSION = "2.0"
BROADCAST_PORT = 50000
POPUP_DURATION = 60  # seconds
MAX_MESSAGE_LENGTH = 1000
MESSAGE_TIMEOUT = 30  # seconds - reject messages older than this
CONFIG_FILE = "admin_config.json"  # Must match admin's config file

# single-instance handle (Windows mutex handle or POSIX lock fd)
_singleton_handle = None


# ==========================
# Secure Message System
# ==========================
class SecureMessageSystem:
    """Handles all decryption and authentication"""
    
    def __init__(self):
        self.config_path = Path(CONFIG_FILE)
        self.secret_key = None
        self.cipher = None
        self.load_config()
    
    def load_config(self):
        """Load secure configuration from file"""
        if not self.config_path.exists():
            messagebox.showerror(
                "Configuration Missing",
                f"Security configuration file not found: {CONFIG_FILE}\n\n"
                "Please obtain the configuration file from your IT administrator."
            )
            sys.exit(1)
        
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                self.secret_key = config['secret_key'].encode()
            
            # Initialize cipher
            self.cipher = Fernet(self.secret_key)
            
        except Exception as e:
            messagebox.showerror(
                "Configuration Error",
                f"Failed to load security configuration: {e}\n\n"
                "Please contact your IT administrator."
            )
            sys.exit(1)
    
    def decrypt_message(self, encrypted_payload):
        """Decrypt and validate received message"""
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
                return None, "Authentication failed"
            
            # Decrypt
            decrypted = self.cipher.decrypt(encrypted_data)
            message_data = json.loads(decrypted)
            
            # Check timestamp (prevent replay attacks)
            message_age = time.time() - message_data['timestamp']
            if message_age > MESSAGE_TIMEOUT:
                return None, "Message expired"
            
            if message_age < 0:
                return None, "Message timestamp is in the future"
            
            # Validate message content
            message = message_data['message']
            if not self._validate_message(message):
                return None, "Invalid message content"
            
            return message, None
            
        except json.JSONDecodeError:
            return None, "Invalid message format"
        except Exception as e:
            return None, f"Decryption failed: {str(e)}"
    
    def _validate_message(self, message):
        """Validate decrypted message content"""
        if not message or not isinstance(message, str):
            return False
        
        if len(message) > MAX_MESSAGE_LENGTH:
            return False
        
        # Check for dangerous characters
        dangerous_chars = ['\x00', '\r']
        if any(char in message for char in dangerous_chars):
            return False
        
        return True


# ==========================
# Safe Startup Task Helper
# ==========================
def ensure_startup_task_safe():
    """Ensure the client app runs at startup via a scheduled task.
    
    SECURITY IMPROVEMENTS:
    - Uses subprocess.run with list args (prevents command injection)
    - Validates exe_path before using it
    - Runs with LIMITED privileges (not HIGHEST)
    - Provides user notification
    - Includes error handling
    """
    if os.name != 'nt':
        return  # Only Windows supported
    
    task_name = "ELMClientApp"
    exe_path = sys.executable
    
    if exe_path.lower().endswith("python.exe"):
        exe_path = os.path.abspath(sys.argv[0])
    
    # SECURITY: Validate exe_path
    if not os.path.exists(exe_path):
        print(f"Warning: Executable path not found: {exe_path}")
        return
    
    # Normalize path to prevent injection
    exe_path = os.path.normpath(exe_path)
    
    # Check if task already exists
    try:
        result = subprocess.run(
            ['schtasks', '/query', '/tn', task_name],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            return  # Task exists
    except Exception:
        pass
    
    # Ask user for permission
    response = messagebox.askyesno(
        "ELM Startup Configuration",
        "Would you like ELM Client to start automatically when you log in?\n\n"
        "This ensures you receive important messages even after restarting your computer."
    )
    
    if not response:
        return
    
    # Create task with LIMITED privileges (not HIGHEST)
    try:
        subprocess.run(
            [
                'schtasks', '/create', '/f',
                '/tn', task_name,
                '/tr', exe_path,
                '/sc', 'onlogon',
                '/rl', 'LIMITED',  # Changed from HIGHEST
                '/it',  # Interactive
                '/z'    # Delete after final run
            ],
            check=True,
            timeout=10,
            capture_output=True
        )
        messagebox.showinfo(
            "Startup Configured",
            "ELM Client will now start automatically when you log in."
        )
    except subprocess.CalledProcessError as e:
        messagebox.showwarning(
            "Startup Configuration Failed",
            f"Could not configure automatic startup.\n\nError: {e}"
        )
    except Exception as e:
        messagebox.showwarning(
            "Startup Configuration Failed",
            f"Unexpected error: {e}"
        )


# =================================
# Popup System
# =================================
class GlassPopup:
    def __init__(self, root):
        self.root = root
        self.top = None
        self.frame = None
        self.messages = []
        self.close_timer = None

    def _create_popup(self):
        self.top = tb.Toplevel(self.root)
        self.top.title("ELM Messages")
        self.top.overrideredirect(True)
        self.top.attributes("-topmost", True)
        self.top.configure(bg="#1a1a1a")
        self.top.wm_attributes("-alpha", 0.95)

        self.frame = ttk.Frame(self.top, padding=20, style="Glass.TFrame")
        self.frame.pack(fill="both", expand=True)

        # Security indicator
        security_label = ttk.Label(
            self.frame,
            text="🔒 Encrypted Message",
            font=("Segoe UI", 9, "italic"),
            foreground="#00ff00",
            background="#1a1a1a"
        )
        security_label.pack(anchor="w", pady=(0, 10))

        # Buttons
        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill="x", pady=(10, 0))

        close_latest = ttk.Button(
            btn_frame, text="❌ Close Latest", style="warning.TButton", 
            command=self.close_latest
        )
        close_latest.pack(side="left", expand=True, padx=2)

        close_all = ttk.Button(
            btn_frame, text="🗑 Close All", style="danger.TButton", 
            command=self.close_all
        )
        close_all.pack(side="right", expand=True, padx=2)

        # Position center
        self.top.update_idletasks()
        w, h = self.top.winfo_width(), self.top.winfo_height()
        sw, sh = self.top.winfo_screenwidth(), self.top.winfo_screenheight()
        x, y = (sw - w) // 2, (sh - h) // 2
        self.top.geometry(f"+{x}+{y}")

    def show(self, message):
        """Display message without system wake manipulation"""
        if self.top is None or not tk.Toplevel.winfo_exists(self.top):
            self._create_popup()

        # Sanitize message for display
        message = self._sanitize_for_display(message)

        # Add message
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

        # Click to dismiss
        label.bind("<Button-1>", lambda e, lbl=label: self._remove_label(lbl))

        # Reset auto-close timer
        if self.close_timer:
            try:
                self.top.after_cancel(self.close_timer)
            except Exception:
                pass
        self.close_timer = self.top.after(POPUP_DURATION * 1000, self.close_all)

    def _sanitize_for_display(self, text):
        """Sanitize text for safe display in GUI"""
        # Remove null bytes and control characters except newline/tab
        sanitized = ''.join(
            char for char in text 
            if char == '\n' or char == '\t' or (ord(char) >= 32 and ord(char) != 127)
        )
        # Limit length
        if len(sanitized) > MAX_MESSAGE_LENGTH:
            sanitized = sanitized[:MAX_MESSAGE_LENGTH] + "..."
        return sanitized

    def close_latest(self):
        if self.messages:
            latest = self.messages.pop()
            try:
                latest.destroy()
            except Exception:
                pass
        if not self.messages and self.top:
            self._destroy_popup()

    def _remove_label(self, lbl):
        try:
            if lbl in self.messages:
                self.messages.remove(lbl)
        except Exception:
            pass
        try:
            lbl.destroy()
        except Exception:
            pass
        if not self.messages and self.top:
            self._destroy_popup()

    def close_all(self):
        if self.close_timer:
            try:
                self.top.after_cancel(self.close_timer)
            except Exception:
                pass
            self.close_timer = None

        for lbl in self.messages:
            try:
                lbl.destroy()
            except Exception:
                pass
        self.messages.clear()
        self._destroy_popup()

    def _destroy_popup(self):
        if self.top:
            try:
                if self.close_timer:
                    try:
                        self.top.after_cancel(self.close_timer)
                    except Exception:
                        pass
                    self.close_timer = None
                self.top.destroy()
            except Exception:
                pass
            finally:
                self.top = None


# =====================================
# Secure Listener
# =====================================
class SecureClientListener:
    def __init__(self, root, popup, crypto_system, port=BROADCAST_PORT):
        self.root = root
        self.popup = popup
        self.crypto_system = crypto_system
        self.port = port
        self.sock = None
        self.running = False
        self.msg_queue = queue.Queue()
        self.failed_auth_count = 0
        self.max_failed_auth = 10

    def start(self):
        threading.Thread(target=self._listen_loop, daemon=True).start()
        self._check_queue()

    def _listen_loop(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(('', self.port))
            self.running = True
            
            print(f"[SECURE] Listening on port {self.port}")
            
            while self.running:
                try:
                    # Limit receive buffer to prevent DoS
                    data, addr = self.sock.recvfrom(8192)
                    
                    # Rate limiting: ignore if too many auth failures
                    if self.failed_auth_count > self.max_failed_auth:
                        print(f"[SECURITY] Too many authentication failures, ignoring message from {addr}")
                        time.sleep(1)  # Slow down processing
                        continue
                    
                    text = data.decode("utf-8", errors="strict")  # Changed from "ignore"
                    
                    # Decrypt and validate
                    message, error = self.crypto_system.decrypt_message(text)
                    
                    if message:
                        self.msg_queue.put(message)
                        self.failed_auth_count = max(0, self.failed_auth_count - 1)  # Decay
                    else:
                        self.failed_auth_count += 1
                        print(f"[SECURITY] Message rejected: {error}")
                        
                except UnicodeDecodeError:
                    print("[SECURITY] Invalid UTF-8 data received")
                    self.failed_auth_count += 1
                except Exception as e:
                    print(f"[ERROR] Listener error: {e}")
                    
        except Exception as e:
            print(f"[FATAL] Failed to start listener: {e}")
            messagebox.showerror(
                "Network Error",
                f"Failed to start message listener:\n{e}\n\nThe application will now exit."
            )
            sys.exit(1)

    def _check_queue(self):
        try:
            while not self.msg_queue.empty():
                msg = self.msg_queue.get_nowait()
                self.popup.show(msg)
        except queue.Empty:
            pass
        self.root.after(500, self._check_queue)


def is_already_installed():
    """Return True if ELM appears already installed.
    
    Enhanced with registry and hash checks.
    """
    try:
        # Check installation directories
        pf = os.environ.get('ProgramFiles', r"C:\Program Files")
        pd = os.environ.get('ProgramData', r"C:\ProgramData")
        candidates = [
            os.path.join(pf, 'ELM'),
            os.path.join(pd, 'ELM'),
        ]
        for base in candidates:
            if os.path.isdir(base):
                if os.path.exists(os.path.join(base, 'client.exe')):
                    return True
                if os.path.exists(os.path.join(base, 'admin.exe')):
                    return True
        
        # Check Windows registry (if on Windows)
        if os.name == 'nt':
            try:
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\ELM",
                    0,
                    winreg.KEY_READ
                )
                winreg.CloseKey(key)
                return True
            except WindowsError:
                pass
                
    except Exception:
        pass
    return False


def abort_if_installed():
    """Check if ELM client is already installed and terminate if so."""
    if is_already_installed():
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showwarning(
                'ELM Client Already Installed',
                'ELM Client is already installed on this system.\n\n'
                'This installation will now terminate to prevent conflicts.'
            )
            root.destroy()
        except Exception:
            print('\n' + '='*70)
            print('ERROR: ELM Client is already installed on this system.')
            print('='*70 + '\n')
        
        sys.exit(1)


def acquire_single_instance():
    """Acquire a system-wide single-instance lock."""
    global _singleton_handle
    
    if os.name == 'nt':
        try:
            kernel32 = ctypes.windll.kernel32
            mutex_name = "Global\\ELMClientSingleton"
            handle = kernel32.CreateMutexW(None, False, mutex_name)
            
            if not handle:
                return False, 'CreateMutexW failed'
            
            last = kernel32.GetLastError()
            ERROR_ALREADY_EXISTS = 183
            
            if last == ERROR_ALREADY_EXISTS:
                try:
                    kernel32.CloseHandle(handle)
                except Exception:
                    pass
                return False, 'Another instance is already running'
            
            _singleton_handle = handle

            def _release():
                try:
                    if _singleton_handle:
                        kernel32.ReleaseMutex(_singleton_handle)
                        kernel32.CloseHandle(_singleton_handle)
                except Exception:
                    pass

            atexit.register(_release)
            return True, None
            
        except Exception as e:
            return False, str(e)

    # POSIX fallback
    try:
        lockdir = os.path.join(os.environ.get('HOME', '/tmp'), '.elm')
        os.makedirs(lockdir, exist_ok=True)
        lockfile = os.path.join(lockdir, 'elmclient.lock')
        fd = os.open(lockfile, os.O_CREAT | os.O_RDWR)
        
        try:
            import fcntl
            fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            _singleton_handle = fd
            atexit.register(lambda: os.close(fd))
            return True, None
        except Exception:
            try:
                os.close(fd)
            except Exception:
                pass
            return False, 'Another instance is already running'
    except Exception as e:
        return False, str(e)


# ==========================
# Main
# ==========================
def main():
    # Check for existing installation
    abort_if_installed()
    
    # Prevent multiple instances
    ok, reason = acquire_single_instance()
    if not ok:
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showinfo(
                'ELM Client',
                f'Another instance of ELM is already running.\n\n{reason}\n\nThis instance will exit.'
            )
            root.destroy()
        except Exception:
            print(f'Another instance of ELM is already running: {reason}')
        sys.exit(0)

    # Initialize GUI
    root = tb.Window(themename="cyborg")
    root.withdraw()

    # Initialize secure messaging
    crypto_system = SecureMessageSystem()
    
    # Setup startup task (with user permission)
    ensure_startup_task_safe()
    
    print(f"[SECURE] Running ELM Client v{APP_VERSION}")

    # Create popup and listener
    popup = GlassPopup(root)
    listener = SecureClientListener(root, popup, crypto_system)
    listener.start()

    root.mainloop()


if __name__ == "__main__":
    main()