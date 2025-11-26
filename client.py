import os
import sys
import subprocess
import socket
import threading
import tkinter as tk
from tkinter import ttk, filedialog
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
MESSAGE_TIMEOUT = 30  # seconds

# Handle for single instance
_singleton_handle = None

# ==========================
# System Control
# ==========================
class SystemControl:
    """Handles Waking the Monitor and Breaking Screensavers"""
    ES_CONTINUOUS = 0x80000000
    ES_SYSTEM_REQUIRED = 0x00000001
    ES_DISPLAY_REQUIRED = 0x00000002
    
    @staticmethod
    def wake_screen():
        if os.name == 'nt':
            try:
                ctypes.windll.kernel32.SetThreadExecutionState(
                    SystemControl.ES_CONTINUOUS | 
                    SystemControl.ES_SYSTEM_REQUIRED | 
                    SystemControl.ES_DISPLAY_REQUIRED
                )
                ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                time.sleep(0.05)
                ctypes.windll.user32.mouse_event(0x0001, 0, -1, 0, 0)
                ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, -1)
            except Exception as e:
                print(f"Error waking screen: {e}")

# ==========================
# Secure Message System (Setup Wizard)
# ==========================
class SecureMessageSystem:
    """Handles persistent key storage and decryption"""
    
    def __init__(self):
        # --- AMENDMENT: Aligning Path Logic with Fixed admin.py ---
        if os.name == 'nt':
            # Windows: APPDATA is typically used for roaming/shared configuration
            base_path = Path(os.getenv('APPDATA'))
        else:
            # Linux/Mac support (Optional, but good practice)
            base_path = Path.home() / ".config"

        # Client uses its own dedicated folder separate from the admin config folder
        self.app_data_dir = base_path / "ELM_Client_Config"
        self.key_file = self.app_data_dir / "security.secret"
        # -----------------------------------------------------------
        
        self.secret_key = None
        self.cipher = None
        
        # Ensure directory exists
        self.app_data_dir.mkdir(parents=True, exist_ok=True)
        # ... (rest of the __init__ remains the same)
        
        self.secret_key = None
        self.cipher = None
        
        # Ensure directory exists
        self.app_data_dir.mkdir(parents=True, exist_ok=True)
        
        # ALWAYS run setup wizard on first run or if key is missing
        if not self.key_file.exists():
            self._run_installation_wizard()
        else:
            self._load_key()

    def _run_installation_wizard(self):
        """GUI for First-Time Setup - ALWAYS prompt for secret key"""
        wizard = tb.Window(themename="cyborg")
        wizard.title("ELM Client Setup")
        
        # Center window
        w, h = 500, 350
        ws, hs = wizard.winfo_screenwidth(), wizard.winfo_screenheight()
        wizard.geometry(f"{w}x{h}+{(ws-w)//2}+{(hs-h)//2}")
        wizard.attributes("-topmost", True)
        
        # UI Elements
        lbl_header = ttk.Label(wizard, text="🔐 Security Configuration", font=("Segoe UI", 16, "bold"), bootstyle="info")
        lbl_header.pack(pady=20)
        
        lbl_instr = ttk.Label(wizard, text="Please enter the Admin Secret Key to authorize this computer.\nYou can paste the key text OR select the admin config file.", justify="center")
        lbl_instr.pack(pady=10)
        
        # Entry Field
        self.key_entry = ttk.Entry(wizard, width=50)
        self.key_entry.pack(pady=10)
        
        # Buttons Frame
        btn_frame = ttk.Frame(wizard)
        btn_frame.pack(pady=20)
        
        def browse_file():
            """Browse for admin_config.json file"""
            filename = filedialog.askopenfilename(
                title="Select Admin Config File",
                filetypes=[("JSON Config", "*.json"), ("All Files", "*.*")],
                parent=wizard
            )
            if filename:
                try:
                    with open(filename, 'r') as f:
                        data = json.load(f)
                        if 'secret_key' in data:
                            self.key_entry.delete(0, tk.END)
                            self.key_entry.insert(0, data['secret_key'])
                            print(f"[SECURE] Loaded key from {filename}")
                        else:
                            messagebox.showerror("Error", "Invalid config file - missing 'secret_key'", parent=wizard)
                except Exception as e:
                    messagebox.showerror("Error", f"Could not read file: {e}", parent=wizard)

        def install_key():
            """Validate and hardcode the key"""
            key_candidate = self.key_entry.get().strip()
            if not key_candidate:
                messagebox.showwarning("Input Required", "Please enter a key or select a file.", parent=wizard)
                return
                
            try:
                # Validate Key Format (must be valid Fernet key)
                Fernet(key_candidate.encode())
                
                # Save to hidden file (hardcoded persistence)
                with open(self.key_file, 'w') as f:
                    f.write(key_candidate)
                
                # Save to hidden file (hardcoded persistence)
                with open(self.key_file, 'w') as f:
                    f.write(key_candidate)

                # Set restrictive file permissions on Windows
                if os.name == 'nt':
                    try:
                        import stat
                        os.chmod(self.key_file, stat.S_IRUSR | stat.S_IWUSR)
                    except:
                        pass
                
                print(f"[SECURE] Key hardcoded to {self.key_file}")
                messagebox.showinfo("Success", "Security Key Installed Successfully!\nThe app will now start.", parent=wizard)
                wizard.destroy()
                
            except Exception as e:
                messagebox.showerror("Invalid Key", f"The key provided is invalid.\nError: {str(e)}", parent=wizard)

        btn_browse = ttk.Button(btn_frame, text="📂 Select Config File", bootstyle="secondary", command=browse_file)
        btn_browse.pack(side="left", padx=5)
        
        btn_save = ttk.Button(btn_frame, text="💾 Install Key", bootstyle="success", command=install_key)
        btn_save.pack(side="left", padx=5)
        
        wizard.protocol("WM_DELETE_WINDOW", sys.exit) # Exit app if closed
        wizard.mainloop()
        
        # Reload after wizard closes
        self._load_key()

    def _load_key(self):
        try:
            with open(self.key_file, 'r') as f:
                key_data = f.read().strip()
                self.secret_key = key_data.encode()
            self.cipher = Fernet(self.secret_key)
            print("[SECURE] Loaded hardcoded key from local storage")
        except Exception:
            # If file is corrupt, delete it and restart wizard
            try: os.remove(self.key_file) 
            except: pass
            self._run_installation_wizard()

    def decrypt_message(self, encrypted_payload):
        try:
            payload = json.loads(encrypted_payload)
            encrypted_data = payload['data'].encode()
            received_mac = payload['mac']
            
            expected_mac = hmac.new(
                self.secret_key, encrypted_data, hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(received_mac, expected_mac):
                return None, "Authentication failed"
            
            decrypted = self.cipher.decrypt(encrypted_data)
            message_data = json.loads(decrypted)
            
            message_age = time.time() - message_data['timestamp']
            if message_age > MESSAGE_TIMEOUT:
                return None, "Message expired"
            if message_age < -5:
                return None, "Timestamp future"
            
            message = message_data['message']
            if not self._validate_message(message):
                return None, "Invalid content"
            
            return message, None
            
        except Exception as e:
            return None, f"Decryption failed: {str(e)}"
    
    def _validate_message(self, message):
        if not message or not isinstance(message, str): return False
        if len(message) > MAX_MESSAGE_LENGTH: return False
        if any(c in message for c in ['\x00', '\r']): return False
        return True

# ==========================
# Safe Startup Task Helper
# ==========================
def ensure_startup_task_safe():
    if os.name != 'nt': return
    
    task_name = "ELMClientApp"
    exe_path = sys.executable
    if exe_path.lower().endswith("python.exe"):
        exe_path = os.path.abspath(sys.argv[0])
    
    if not os.path.exists(exe_path): return
    exe_path = os.path.normpath(exe_path)
    
    try:
        res = subprocess.run(['schtasks', '/query', '/tn', task_name], capture_output=True)
        if res.returncode == 0: return
    except: pass
    
    if messagebox.askyesno("ELM Startup", "Start ELM Client automatically when you log in?"):
        try:
            subprocess.run([
                'schtasks', '/create', '/f', '/tn', task_name,
                '/tr', exe_path, '/sc', 'onlogon', '/rl', 'LIMITED', '/it', '/z'
            ], check=True, capture_output=True)
            messagebox.showinfo("Success", "Startup configured.")
        except Exception as e:
            pass

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
        
        border = tk.Frame(self.top, background="red", padx=2, pady=2)
        border.pack(fill="both", expand=True)

        self.frame = ttk.Frame(border, padding=20, style="Glass.TFrame")
        self.frame.pack(fill="both", expand=True)

        ttk.Label(self.frame, text="🔒 ENCRYTED MESSAGE", font=("Segoe UI", 10, "bold"), 
                 foreground="#ff3333", background="#1a1a1a").pack(anchor="w", pady=(0, 10))

        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill="x", pady=(10, 0))
        ttk.Button(btn_frame, text="Close All", style="danger.TButton", 
                  command=self.close_all).pack(side="right", padx=2)
        ttk.Button(btn_frame, text="Dismiss", style="warning.TButton", 
                  command=self.close_latest).pack(side="right", padx=2)

        self.top.update_idletasks()
        w, h = self.top.winfo_width(), self.top.winfo_height()
        sw, sh = self.top.winfo_screenwidth(), self.top.winfo_screenheight()
        self.top.geometry(f"+{(sw-w)//2}+{(sh-h)//2}")
        self._keep_on_top()

    def _keep_on_top(self):
        if self.top and tk.Toplevel.winfo_exists(self.top):
            self.top.attributes("-topmost", True)
            self.top.lift()
            self.root.after(500, self._keep_on_top)

    def show(self, message):
        SystemControl.wake_screen()
        if self.top is None or not tk.Toplevel.winfo_exists(self.top):
            self._create_popup()
        else:
            self.top.attributes("-alpha", 0)
            self.top.update()
            time.sleep(0.1)
            self.top.attributes("-alpha", 0.95)

        message = self._sanitize(message)
        lbl = ttk.Label(self.frame, text=message, wraplength=500, justify="left",
                       font=("Segoe UI", 14, "bold"), foreground="white", background="#1a1a1a")
        lbl.pack(anchor="w", pady=5)
        self.messages.append(lbl)
        try: self.root.bell()
        except: pass
        
        if self.close_timer: self.top.after_cancel(self.close_timer)
        self.close_timer = self.top.after(POPUP_DURATION * 1000, self.close_all)

    def _sanitize(self, text):
        clean = ''.join(c for c in text if c in '\n\t' or (ord(c)>=32 and ord(c)!=127))
        return (clean[:MAX_MESSAGE_LENGTH] + "...") if len(clean) > MAX_MESSAGE_LENGTH else clean

    def close_latest(self):
        if self.messages:
            try: self.messages.pop().destroy()
            except: pass
        if not self.messages: self._destroy_popup()

    def close_all(self):
        if self.close_timer: self.top.after_cancel(self.close_timer)
        for lbl in self.messages: 
            try: lbl.destroy()
            except: pass
        self.messages.clear()
        self._destroy_popup()

    def _destroy_popup(self):
        if self.top:
            try: self.top.destroy()
            except: pass
            finally: self.top = None

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
                    data, addr = self.sock.recvfrom(8192)
                    if self.failed_auth_count > 10:
                        time.sleep(1)
                        continue
                    
                    msg, err = self.crypto_system.decrypt_message(data.decode("utf-8", "strict"))
                    if msg:
                        self.msg_queue.put(msg)
                        self.failed_auth_count = max(0, self.failed_auth_count - 1)
                    else:
                        self.failed_auth_count += 1
                        print(f"Rejected: {err}")
                except Exception as e:
                    print(f"Listener error: {e}")
        except Exception as e:
            sys.exit(1)

    def _check_queue(self):
        try:
            while not self.msg_queue.empty():
                self.popup.show(self.msg_queue.get_nowait())
        except queue.Empty: pass
        self.root.after(500, self._check_queue)

def acquire_single_instance():
    global _singleton_handle
    if os.name == 'nt':
        try:
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.CreateMutexW(None, False, "Global\\ELMClientSingleton")
            if not handle: return False, 'Error'
            if kernel32.GetLastError() == 183: return False, 'Already running'
            _singleton_handle = handle
            return True, None
        except Exception as e: return False, str(e)
    return True, None

# ==========================
# Main
# ==========================
def main():
    # Prevent multiple instances
    ok, reason = acquire_single_instance()
    if not ok: 
        print(f"Startup blocked: {reason}")
        sys.exit(0)

    # Init Theme and Hide Main Window
    root = tb.Window(themename="cyborg")
    root.withdraw()

    # 1. Initialize Secure System (RUNS INSTALLER WIZARD IF KEY IS MISSING)
    crypto_system = SecureMessageSystem()
    
    # --- CRITICAL CHECK: ONLY START LISTENER IF KEY IS VALID ---
    if crypto_system.secret_key is None:
        # This should only happen if the key load/install failed and the wizard 
        # unexpectedly closed without providing a key.
        messagebox.showerror("Security Error", "Cannot start client: Security key is missing or invalid.")
        sys.exit(1)
    
    # 2. Setup Auto-Start
    ensure_startup_task_safe()
    
    print(f"[SECURE] Running ELM Client v{APP_VERSION}")

    # 3. Start Listener ONLY after key is confirmed
    popup = GlassPopup(root)
    listener = SecureClientListener(root, popup, crypto_system)
    listener.start()

    root.mainloop()

if __name__ == "__main__":
    main()