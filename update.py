# updater.py
import requests
import os
import sys
import subprocess
from datetime import datetime, timedelta

LAST_CHECK_FILE = "last_update_check.txt"
REPO = "ElmonINC/ELM"  # format: username/reponame

def should_check():
    if not os.path.exists(LAST_CHECK_FILE):
        return True
    try:
        with open(LAST_CHECK_FILE, "r") as f:
            last_check = datetime.fromisoformat(f.read().strip())
        return datetime.now() - last_check > timedelta(days=1)
    except:
        return True

def check_for_update(current_version: str):
    url = f"https://api.github.com/repos/{REPO}/releases/latest"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()

        latest_version = data["tag_name"].lstrip("v")  # e.g. "v1.1.0" → "1.1.0"
        assets = data.get("assets", [])

        if latest_version != current_version and assets:
            # Pick first asset (you can filter for .exe installer)
            download_url = assets[0]["browser_download_url"]
            print(f"Updating to {latest_version} from {download_url}")

            installer = "update_setup.exe"
            with open(installer, "wb") as f:
                f.write(requests.get(download_url, stream=True).content)

            # Run silent installer
            subprocess.Popen([installer, "/VERYSILENT", "/NORESTART"])
            sys.exit(0)  # exit app so installer can replace files

    except Exception as e:
        print("Update check failed:", e)

def run_update_check(app_version: str):
    if should_check():
        check_for_update(app_version)
        with open(LAST_CHECK_FILE, "w") as f:
            f.write(datetime.now().isoformat())
