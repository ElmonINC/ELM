import requests
import os
import sys
import subprocess
from datetime import datetime, timedelta

REPO = "ElmonINC/ELM"  # format: username/reponame

def get_update_file():
    """Return a writable path for last_update_check.txt"""
    base_dir = os.path.join(os.getenv("APPDATA"), "ELM") # use APPDATA for user-specific data
    os.makedirs(base_dir, exist_ok=True)  # make sure folder exists
    return os.path.join(base_dir, "last_update_check.txt")  # path to file

def should_check():
    update_file = get_update_file()    # last update check timestamp
    if not os.path.exists(update_file):  # file missing → first run
        return True   # need to check
    try:
        with open(update_file, "r") as f:   # read timestamp
            last_check = datetime.fromisoformat(f.read().strip())   # read timestamp
        return datetime.now() - last_check > timedelta(days=1)   # check if >1 day
    except Exception: # on error, force check
        return True # exit gracefully

def check_for_update(current_version: str):
    url = f"https://api.github.com/repos/{REPO}/releases/latest"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()

        if "tag_name" not in data:
            print("⚠️ No release found or bad response:", data.get("message", "Unknown error"))
            return  # exit gracefully

        latest_version = data["tag_name"].lstrip("v")  # e.g. "v1.1.0" → "1.1.0"
        assets = data.get("assets", [])

        if latest_version != current_version and assets:
            # Pick first asset (you can filter for .exe installer if needed)
            download_url = assets[0]["browser_download_url"]
            print(f"Updating to {latest_version} from {download_url}")

            installer = os.path.join(os.getenv("TEMP"), "update_setup.exe")
            with open(installer, "wb") as f:
                f.write(requests.get(download_url, stream=True).content)

            # Run silent installer
            subprocess.Popen([installer, "/VERYSILENT", "/NORESTART"])
            sys.exit(0)  # exit app so installer can replace files

    except Exception as e:
        print("Update check failed:", e)


def run_update_check(app_version: str):
    update_file = get_update_file()
    if should_check():
        check_for_update(app_version)
        with open(update_file, "w") as f:
            f.write(datetime.now().isoformat())
