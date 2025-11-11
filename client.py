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
import tkinter.messagebox as messagebox
import ctypes
import atexit

from update import run_update_check

APP_VERSION = "1.1"
try:
    import schedule
except ImportError:
    schedule = None  # handle later: check `if schedule is None` before using

try:
    import git  # from GitPython
except ImportError:
    git = None
    
BROADCAST_PORT = 50000
DEFAULT_TOKEN = "SgiVeDLUQsZ9PnY4ERxkLWjBmLfuA5" # simple authentication key
POPUP_DURATION = 60  # seconds

# single-instance handle (Windows mutex handle or POSIX lock fd)
_singleton_handle = None


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
        close_latest.pack(side="left", expand=True, padx=2)

        close_all = ttk.Button(
            btn_frame, text="🗑", style="danger.TButton", command=self.close_all
        )
        close_all.pack(side="right", expand=True, padx=2)

        # Position center
        self.top.update_idletasks()
        w, h = self.top.winfo_width(), self.top.winfo_height()
        sw, sh = self.top.winfo_screenwidth(), self.top.winfo_screenheight()
        x, y = (sw - w) // 2, (sh - h) // 2
        self.top.geometry(f"+{x}+{y}")

    def show(self, message):
        # try to wake the system/display when a message arrives
        try:
            self._wake_system()
        except Exception:
            pass
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

        # allow clicking a message to remove it immediately
        label.bind("<Button-1>", lambda e, lbl=label: self._remove_label(lbl))

        # Reset timer → only latest message’s timer counts
        if self.close_timer:
            try:
                self.top.after_cancel(self.close_timer)
            except Exception:
                pass
        self.close_timer = self.top.after(POPUP_DURATION * 1000, self.close_all)

    def _wake_system(self):
        """Attempt to wake the system/display on Windows.

        This function uses a conservative approach:
        - Calls SetThreadExecutionState to request the display/system stay awake.
        - Simulates a tiny cursor move (move and restore) to wake the display.

        Note: waking from deep sleep (S3) may not be possible from user apps.
        """
        if os.name != 'nt':
            # macOS: touch the display using 'caffeinate' if available
            try:
                if sys.platform == 'darwin':
                    subprocess.Popen(['caffeinate', '-u', '-t', '1'])
            except Exception:
                pass
            return

        # Windows
        try:
            ES_CONTINUOUS = 0x80000000
            ES_SYSTEM_REQUIRED = 0x00000001
            ES_DISPLAY_REQUIRED = 0x00000002
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)

            # Try to gently move the mouse by 1 pixel and back to wake the display
            class POINT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

            pt = POINT()
            if ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
                x, y = pt.x, pt.y
                # move then restore
                ctypes.windll.user32.SetCursorPos(x + 1, y)
                time.sleep(0.01)
                ctypes.windll.user32.SetCursorPos(x, y)
        except Exception:
            # best-effort only
            pass

    def close_latest(self):
        if self.messages:
            latest = self.messages.pop()
            try:
                latest.destroy()
            except Exception:
                pass
        if not self.messages and self.top:
            self._destroy_popup()
        else:
            # ensure UI updates immediately
            if self.top:
                try:
                    self.top.update_idletasks()
                except Exception:
                    pass

    def _remove_label(self, lbl):
        """Remove a specific label safely and destroy popup if no messages remain."""
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
        # Terminate timer instantly
        if self.close_timer:
            try:
                self.top.after_cancel(self.close_timer)
            except Exception:
                pass
            self.close_timer = None

        # Remove all messages
        for lbl in self.messages:
            lbl.destroy()
        self.messages.clear()

        self._destroy_popup()

    def _destroy_popup(self):
        if self.top:
            try:
                # ensure any pending timer is cancelled
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
# Listener
# =====================================
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

def is_already_installed():
    """Return True if ELM appears already installed on this system.
    This is a best-effort check looking for known installation directories and files.
    """
    try:
        pf = os.environ.get('ProgramFiles', r"C:\Program Files")
        pd = os.environ.get('ProgramData', r"C:\ProgramData")
        candidates = [
            os.path.join(pf, 'ELM'),
            os.path.join(pd, 'ELM'),
        ]
        for base in candidates:
            if os.path.isdir(base):
                # check for known executables
                if os.path.exists(os.path.join(base, 'client.exe')) or os.path.exists(os.path.join(base, 'admin.exe')):
                    return True
                # or any files present
                if any(os.scandir(base)):
                    return True
    except Exception:
        pass
    return False


def abort_if_installed():
    """Show a message and exit if ELM is already installed.

    This is a best-effort guard for installer scenarios. The proper place for
    install-time checks is the installer script (Inno/NSIS) but this prevents
    accidental re-install when the client exe is used as an installer entrypoint.
    """
    if is_already_installed():
        # Prefer a GUI message when possible
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showinfo('ELM', 'ELM appears to be already installed on this system. Installation will be stopped.')
            root.destroy()
        except Exception:
            # Fallback to console message
            print('ELM appears to be already installed on this system. Installation will be stopped.')
        # Exit with non-zero code to indicate installer should stop
        sys.exit(1)


def acquire_single_instance():
    """Acquire a system-wide single-instance lock.

    Returns (True, None) when lock acquired, (False, reason) when another
    instance is running.
    """
    global _singleton_handle
    if os.name == 'nt':
        try:
            kernel32 = ctypes.windll.kernel32
            mutex_name = "Global\\ELMClientSingleton"
            # Create an unnamed security attributes pointer (NULL), initially not owned, with name
            handle = kernel32.CreateMutexW(None, False, mutex_name)
            if not handle:
                return False, 'CreateMutexW failed'
            last = kernel32.GetLastError()
            ERROR_ALREADY_EXISTS = 183
            if last == ERROR_ALREADY_EXISTS:
                # Close handle and indicate another instance
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
        except Exception:
            return True, None

    # POSIX fallback: use a lockfile in ProgramData or /var/run
    try:
        lockdir = os.path.join(os.environ.get('ProgramData', '/var'), 'ELM')
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
    except Exception:
        return True, None

# ==========================
# Main
# ==========================
def main():
    # Prevent multiple running instances (listeners) — acquire singleton first
    ok, reason = acquire_single_instance()
    if not ok:
        # Show info then exit silently
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showinfo('ELM', 'Another instance of ELM is already running. This instance will exit.')
            root.destroy()
        except Exception:
            print('Another instance of ELM is already running. Exiting.')
        sys.exit(0)

    # If running as an installer/extractor, prevent double-install: abort if already installed
    abort_if_installed()

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

