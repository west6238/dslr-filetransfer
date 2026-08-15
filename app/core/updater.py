import os
import sys
import json
import time
import zipfile
import urllib.request
import subprocess
from PySide6.QtCore import QObject, Signal, QThread

GITHUB_API_URL = "https://api.github.com/repos/west6238/dslr-filetransfer/releases/latest"

class UpdaterWorker(QThread):
    def __init__(self, current_version):
        super().__init__()
        self.current_version = current_version
        self.download_url = None
        self.new_version = None

    def run(self):
        try:
            req = urllib.request.Request(GITHUB_API_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                
            tag_name = data.get("tag_name", "").lstrip("v")
            if not tag_name:
                return

            if self._is_newer(tag_name, self.current_version):
                assets = data.get("assets", [])
                for asset in assets:
                    if asset.get("name", "").endswith(".zip"):
                        self.new_version = tag_name
                        self.download_url = asset.get("browser_download_url")
                        break
        except Exception as e:
            print("Update check failed:", e)

    def _is_newer(self, remote, local):
        def parse_version(v):
            return tuple(map(int, (v.split("."))))
        try:
            return parse_version(remote) > parse_version(local)
        except:
            return False

class DownloaderWorker(QThread):
    progress = Signal(int, int) # current, total
    finished = Signal(str, str) # new_version, zip_path
    failed = Signal(str)

    def __init__(self, download_url, new_version):
        super().__init__()
        self.download_url = download_url
        self.new_version = new_version

    def run(self):
        try:
            temp_dir = os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__), '.temp')
            os.makedirs(temp_dir, exist_ok=True)
            zip_path = os.path.join(temp_dir, f"update_{self.new_version}.zip")

            req = urllib.request.Request(self.download_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as response, open(zip_path, 'wb') as out_file:
                total_length = response.getheader('content-length')
                if total_length is None: # no content length header
                    out_file.write(response.read())
                    self.progress.emit(100, 100)
                else:
                    total_length = int(total_length)
                    downloaded = 0
                    chunk_size = 8192
                    while True:
                        buffer = response.read(chunk_size)
                        if not buffer:
                            break
                        downloaded += len(buffer)
                        out_file.write(buffer)
                        self.progress.emit(downloaded, total_length)

            self.finished.emit(self.new_version, zip_path)
        except Exception as e:
            self.failed.emit(str(e))


class AppUpdater(QObject):
    update_available = Signal(str, str) # version, download_url
    download_progress = Signal(int, int) # current, total
    download_complete = Signal()
    error_occurred = Signal(str)

    def __init__(self, current_version):
        super().__init__()
        self.current_version = current_version
        self._check_worker = None
        self._download_worker = None

    def check_for_updates(self):
        if self._check_worker and self._check_worker.isRunning():
            return
        self._check_worker = UpdaterWorker(self.current_version)
        self._check_worker.finished.connect(self._on_check_finished)
        self._check_worker.start()

    def _on_check_finished(self):
        if self._check_worker.new_version and self._check_worker.download_url:
            self.update_available.emit(self._check_worker.new_version, self._check_worker.download_url)

    def start_update(self, new_version, download_url):
        if self._download_worker and self._download_worker.isRunning():
            return
        self._download_worker = DownloaderWorker(download_url, new_version)
        self._download_worker.progress.connect(self.download_progress.emit)
        self._download_worker.finished.connect(self._on_download_finished)
        self._download_worker.failed.connect(self.error_occurred.emit)
        self._download_worker.start()

    def _on_download_finished(self, new_version, zip_path):
        self.download_complete.emit()
        self._apply_update(zip_path)

    def _apply_update(self, zip_path):
        try:
            is_frozen = getattr(sys, 'frozen', False)
            if is_frozen:
                base_dir = os.path.dirname(sys.executable)
                exe_name = os.path.basename(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                exe_name = "main.py"

            temp_dir = os.path.dirname(zip_path)
            extract_dir = os.path.join(temp_dir, "extracted")
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            bat_path = os.path.join(temp_dir, "updater.bat")
            
            bat_script = f"""@echo off
echo Updating DSLR File Transfer... Please wait.
ping 127.0.0.1 -n 3 > nul

xcopy "{extract_dir}\\*" "{base_dir}\\" /S /Y /C /F /H /R

if exist "{os.path.join(base_dir, exe_name)}" (
    start "" "{os.path.join(base_dir, exe_name)}"
) else (
    if "{exe_name}" == "main.py" (
        start "" "python" "{os.path.join(base_dir, exe_name)}"
    )
)

ping 127.0.0.1 -n 2 > nul
rd /s /q "{temp_dir}"
exit
"""
            with open(bat_path, "w", encoding="utf-8") as f:
                f.write(bat_script)

            subprocess.Popen(
                bat_path,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                cwd=temp_dir
            )
            
            sys.exit(0)
            
        except Exception as e:
            self.error_occurred.emit(f"Failed to apply update: {str(e)}")
