import os
import time
import json
import datetime
import subprocess
import win32com.client
import pythoncom
from PySide6.QtCore import QObject, Signal, QThread

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'config.json')

DEFAULT_MEDIA_EXTENSIONS = {
    '.jpg', '.jpeg', '.jpe', '.png', '.gif', '.bmp', '.webp', '.nef', '.cr2', '.arw', '.dng',
    '.mp4', '.mov', '.avi', '.wmv', '.mkv', '.m4v', '.3gp', '.3g2', '.mpg', '.mpeg', '.mts', '.m2ts'
}

def get_windows_pictures_folder():
    try:
        pythoncom.CoInitialize()
        shell = win32com.client.Dispatch("Shell.Application")
        path = shell.NameSpace(39).Self.Path
        pythoncom.CoUninitialize()
        return path
    except Exception:
        return os.path.expanduser("~\\Pictures")

class WorkerThread(QThread):
    def __init__(self, target, *args, **kwargs):
        super().__init__()
        self._target = target
        self._args = args
        self._kwargs = kwargs

    def run(self):
        self._target(*self._args, **self._kwargs)


class CameraHandler(QObject):
    connection_changed = Signal(bool, str, str) # connected, name, serial
    unregistered_device_connected = Signal(str, str) # name, serial
    scan_progress = Signal(int, str) # count, current_file
    scan_complete = Signal(list) # list of files
    scan_failed = Signal(str)
    auto_fetch_triggered = Signal()
    
    fetch_progress = Signal(int, int, str) # copied, total, current_file
    fetch_complete = Signal(int, str, bool) # copied_count, dest_path, is_deleted
    fetch_failed = Signal(str)

    delete_progress = Signal(int, int, str) # deleted, total, current_file
    delete_complete = Signal()
    delete_failed = Signal(str)

    def __init__(self):
        super().__init__()
        self.is_connected = False
        self.device_name = None
        self.device_serial = None
        self.device_item = None
        
        self.initial_connection_checked = False
        self._auto_fetch_pending = False
        self._scan_cancel_requested = False

        self.config = self._load_config()
        self.found_files = []
        self.dest_path = ""
        self._active_thread = None

    def _load_config(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    if "restrict_to_nikon" not in config: config["restrict_to_nikon"] = True
                    if "chkbox_tag" not in config: config["chkbox_tag"] = True
                    if "chkbox_delete_after" not in config: config["chkbox_delete_after"] = False
                    if not config.get("save_dir"): config["save_dir"] = get_windows_pictures_folder()
                    if "last_tag" not in config: config["last_tag"] = ""
                    if "taglist" not in config: config["taglist"] = ["제주도여행", "가족모임", "테스트"]
                    if "registered_cameras" not in config: config["registered_cameras"] = []
                    if "autorun_only_registered" not in config: config["autorun_only_registered"] = True
                    return config
            except Exception as e:
                print("Error loading config.json:", e)
        
        default_config = {
            "restrict_to_nikon": True,
            "chkbox_tag": True,
            "chkbox_autorun": False,
            "chkbox_explorer": True,
            "chkbox_delete_after": False,
            "save_dir": get_windows_pictures_folder(),
            "foldernaming": "가져온 날짜 + 태그",
            "taglist": ["제주도여행", "가족모임", "테스트"],
            "last_tag": "",
            "registered_cameras": [],
            "autorun_only_registered": True
        }
        self._save_config(default_config)
        return default_config

    def _save_config(self, config_data=None):
        if config_data is not None:
            self.config = config_data
        try:
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print("Error saving config.json:", e)

    def update_config(self, new_data):
        self.config.update(new_data)
        if not self.config.get("save_dir"):
            self.config["save_dir"] = get_windows_pictures_folder()
        self._save_config()
        return self.config

    def add_tag_to_history(self, tag_name):
        if not tag_name or not tag_name.strip():
            return
        tag_name = tag_name.strip()
        tags = self.config.get("taglist", [])
        if tag_name not in tags:
            tags.insert(0, tag_name)
            self.config["taglist"] = tags
            self._save_config()

    def _get_portable_devices(self):
        devices = []
        try:
            shell = win32com.client.Dispatch("Shell.Application")
            folder = shell.NameSpace(17)  # ssfDRIVES
            for item in folder.Items():
                path = item.Path
                name = item.Name
                if not (len(path) == 3 and path[1] == ':' and path[2] == '\\'):
                    if name not in ["네트워크", "제어판", "Network", "Control Panel"]:
                        devices.append((name, item))
        except Exception as e:
            print("Error accessing Shell COM:", e)
        return devices

    def check_connection(self):
        pythoncom.CoInitialize()
        devices = self._get_portable_devices()
        was_connected = self.is_connected
        if devices:
            self.is_connected = True
            self.device_name = devices[0][0]
            self.device_item = devices[0][1]
            self.device_serial = self._fetch_wmi_serial(self.device_name)
            
            if not was_connected:
                self.connection_changed.emit(True, self.device_name, self.device_serial or "")
                
            if not self.initial_connection_checked:
                self.initial_connection_checked = True
            else:
                if not was_connected:
                    is_registered = any(cam.get("serial") == self.device_serial for cam in self.config.get("registered_cameras", []))
                    if not is_registered:
                        self.unregistered_device_connected.emit(self.device_name, self.device_serial or "")
                    elif self.config.get("chkbox_autorun", False):
                        self._auto_fetch_pending = True
                        self.start_scan()
        else:
            self.initial_connection_checked = True
            self.is_connected = False
            self.device_name = None
            self.device_serial = None
            self.device_item = None
            if was_connected:
                self.cancel_scan()
                self._auto_fetch_pending = False
                self.connection_changed.emit(False, "", "")
        pythoncom.CoUninitialize()

    def _fetch_wmi_serial(self, target_name):
        try:
            wmi_obj = win32com.client.GetObject("winmgmts:")
            pnp_devices = wmi_obj.InstancesOf("Win32_PnPEntity")
            for pnp in pnp_devices:
                if pnp.PNPClass == 'WPD' and pnp.Caption and target_name in pnp.Caption:
                    if pnp.DeviceID:
                        return pnp.DeviceID.split('\\')[-1]
        except Exception as e:
            pass
        return None

    def start_scan(self):
        if self._active_thread and self._active_thread.isRunning():
            return False
        
        self._scan_cancel_requested = False
        self.found_files = []
        if self.config.get("chkbox_autorun"):
            self._auto_fetch_pending = True

        self._active_thread = WorkerThread(self._scan_worker)
        self._active_thread.finished.connect(self._on_scan_thread_finished)
        self._active_thread.start()
        return True

    def _on_scan_thread_finished(self):
        if self._auto_fetch_pending:
            self._auto_fetch_pending = False
            self.auto_fetch_triggered.emit()

    def cancel_scan(self):
        self._scan_cancel_requested = True
        self._auto_fetch_pending = False

    def _scan_worker(self):
        pythoncom.CoInitialize()
        try:
            devices = self._get_portable_devices()
            if not devices:
                self.scan_failed.emit("연결된 기기 없음")
                return

            device_item = devices[0][1]
            files_list = []

            def _traverse(folder_obj):
                if self._scan_cancel_requested or not folder_obj:
                    return
                try:
                    for item in folder_obj.Items():
                        if self._scan_cancel_requested:
                            break
                        name = item.Name
                        if item.IsFolder:
                            _traverse(item.GetFolder)
                        else:
                            ext = os.path.splitext(name)[1].lower()
                            if ext in DEFAULT_MEDIA_EXTENSIONS:
                                files_list.append(name)
                                self.scan_progress.emit(len(files_list), name)
                except Exception as e:
                    pass

            _traverse(device_item.GetFolder)

            if not self._scan_cancel_requested:
                self.found_files = files_list
                self.scan_complete.emit(files_list)
        except Exception as e:
            self.scan_failed.emit(str(e))
            self._auto_fetch_pending = False
        finally:
            pythoncom.CoUninitialize()

    def start_fetch(self, tag_name='', save_dir=None, delete_after=None):
        if self._active_thread and self._active_thread.isRunning():
            return False
        
        if not self.found_files:
            return False

        base_dir = save_dir if save_dir is not None else self.config.get("save_dir")
        if not base_dir:
            base_dir = get_windows_pictures_folder()
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")

        if tag_name and tag_name.strip():
            folder_name = f"{date_str}_{tag_name.strip()}"
            self.add_tag_to_history(tag_name.strip())
        else:
            folder_name = date_str

        self.dest_path = os.path.join(base_dir, folder_name)
        
        if delete_after is None:
            delete_after = self.config.get("chkbox_delete_after", False)

        self._active_thread = WorkerThread(self._fetch_worker, self.dest_path, delete_after)
        self._active_thread.start()
        return True

    def _fetch_worker(self, dest_path, delete_after=False):
        pythoncom.CoInitialize()
        try:
            dest_path = os.path.abspath(os.path.normpath(dest_path))
            os.makedirs(dest_path, exist_ok=True)
            
            temp_dir = os.path.join(dest_path, '.temp_fetch')
            os.makedirs(temp_dir, exist_ok=True)
            
            shell = win32com.client.Dispatch("Shell.Application")
            dest_shell_folder = shell.NameSpace(dest_path)
            temp_shell_folder = shell.NameSpace(temp_dir)

            devices = self._get_portable_devices()
            if not devices:
                self.fetch_failed.emit("장치 연결 끊김")
                return

            device_item = devices[0][1]
            copied_count = 0
            total_count = len(self.found_files)
            
            import shutil
            
            def get_unique_filename(directory, filename):
                base, ext = os.path.splitext(filename)
                counter = 1
                new_name = filename
                while os.path.exists(os.path.join(directory, new_name)):
                    new_name = f"{base} - ({counter}){ext}"
                    counter += 1
                return new_name
            
            def _traverse_and_copy(folder_obj):
                nonlocal copied_count
                if not folder_obj:
                    return
                try:
                    for item in folder_obj.Items():
                        if item.IsFolder:
                            _traverse_and_copy(item.GetFolder)
                        else:
                            name = item.Name
                            ext = os.path.splitext(name)[1].lower()
                            if ext in DEFAULT_MEDIA_EXTENSIONS:
                                if os.path.exists(os.path.join(dest_path, name)):
                                    target_temp_file = os.path.join(temp_dir, name)
                                    if os.path.exists(target_temp_file):
                                        os.remove(target_temp_file)
                                    
                                    temp_shell_folder.CopyHere(item, 4 | 16 | 512 | 1024)
                                    
                                    start_wait = time.time()
                                    copy_success = False
                                    while time.time() - start_wait < 30.0:
                                        pythoncom.PumpWaitingMessages()
                                        time.sleep(0.1)
                                        if os.path.exists(target_temp_file) and os.path.getsize(target_temp_file) > 0:
                                            try:
                                                with open(target_temp_file, 'rb'): pass
                                                copy_success = True
                                                break
                                            except IOError:
                                                pass
                                    
                                    if copy_success:
                                        unique_name = get_unique_filename(dest_path, name)
                                        shutil.move(target_temp_file, os.path.join(dest_path, unique_name))
                                        copied_count += 1
                                else:
                                    target_file = os.path.join(dest_path, name)
                                    dest_shell_folder.CopyHere(item, 4 | 16 | 512 | 1024)
                                    
                                    start_wait = time.time()
                                    copy_success = False
                                    while time.time() - start_wait < 30.0:
                                        pythoncom.PumpWaitingMessages()
                                        time.sleep(0.1)
                                        if os.path.exists(target_file) and os.path.getsize(target_file) > 0:
                                            try:
                                                with open(target_file, 'rb'): pass
                                                copy_success = True
                                                break
                                            except IOError:
                                                pass
                                    
                                    if copy_success:
                                        copied_count += 1
                                self.fetch_progress.emit(copied_count, total_count, name)
                except Exception as e:
                    pass

            _traverse_and_copy(device_item.GetFolder)

            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass
                
        except Exception as e:
            self.fetch_failed.emit(str(e))
            return
        finally:
            pythoncom.CoUninitialize()
            
        # Execute deletion after releasing COM resources
        is_deleted = False
        if delete_after:
            import sys
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
                deleter_exe = os.path.join(base_path, 'assets', 'WpdDeleter.exe')
            else:
                base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                deleter_exe = os.path.join(base_path, 'app', 'assets', 'WpdDeleter.exe')
            
            if os.path.exists(deleter_exe) and self.device_name:
                self.fetch_progress.emit(copied_count, total_count, '원본 파일 지우는 중...')
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                subprocess.run([deleter_exe, self.device_name], 
                            capture_output=True, text=True,
                            startupinfo=startupinfo,
                            creationflags=subprocess.CREATE_NO_WINDOW)
                is_deleted = True

        self.fetch_complete.emit(copied_count, dest_path, is_deleted)

    def start_delete_originals(self):
        if self._active_thread and self._active_thread.isRunning():
            return False
            
        self._active_thread = WorkerThread(self._delete_worker)
        self._active_thread.start()
        return True

    def _delete_worker(self):
        try:
            if not self.device_name:
                self.delete_failed.emit("장치 연결 끊김")
                return

            import sys
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
                deleter_exe = os.path.join(base_path, 'assets', 'WpdDeleter.exe')
            else:
                base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                deleter_exe = os.path.join(base_path, 'app', 'assets', 'WpdDeleter.exe')
            
            if not os.path.exists(deleter_exe):
                self.delete_failed.emit(f"삭제 모듈(WpdDeleter.exe)을 찾을 수 없습니다.")
                return

            total_count = len(self.found_files)
            self.delete_progress.emit(0, total_count, '백그라운드에서 원본 삭제 중...')
            
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            result = subprocess.run([deleter_exe, self.device_name], 
                                    capture_output=True, text=True,
                                    startupinfo=startupinfo,
                                    creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode == 0:
                self.delete_progress.emit(total_count, total_count, '삭제 완료')
                self.delete_complete.emit()
            else:
                self.delete_failed.emit(f"삭제 실패: {result.stderr or result.stdout}")
        except Exception as e:
            self.delete_failed.emit(str(e))
