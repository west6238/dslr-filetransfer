import os
import time
import json
import threading
import datetime
import subprocess
import win32com.client
import pythoncom

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')

DEFAULT_MEDIA_EXTENSIONS = {
    '.jpg', '.jpeg', '.jpe', '.png', '.gif', '.bmp', '.webp', '.nef', '.cr2', '.arw', '.dng',
    '.mp4', '.mov', '.avi', '.wmv', '.mkv', '.m4v', '.3gp', '.3g2', '.mpg', '.mpeg', '.mts', '.m2ts'
}

class CameraHandler:
    def __init__(self):
        self.is_connected = False
        self.device_name = None
        self.device_serial = None
        self.device_item = None
        
        self.initial_connection_checked = False
        self._auto_fetch_pending = False

        # Config management
        self.config = self._load_config()

        # Scan state
        self.scan_state = {
            'status': 'idle',  # 'idle', 'scanning', 'complete', 'cancelled'
            'count': 0,
            'current_file': '',
            'files': []  # list of (file_name, shell_item)
        }

        # Fetch state
        self.fetch_state = {
            'status': 'idle',  # 'idle', 'fetching', 'complete', 'failed'
            'total': 0,
            'copied': 0,
            'current_file': '',
            'dest_path': '',
            'copied_files': []
        }

        self.delete_state = {
            'status': 'idle',
            'total': 0,
            'deleted': 0,
            'current_file': ''
        }

        self._scan_cancel_requested = False

    def _load_config(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # Merge new defaults if missing
                    if "restrict_to_nikon" not in config:
                        config["restrict_to_nikon"] = True
                    if "chkbox_tag" not in config:
                        config["chkbox_tag"] = True
                    if "chkbox_delete_after" not in config:
                        config["chkbox_delete_after"] = False
                    if not config.get("save_dir"):
                        config["save_dir"] = os.path.expanduser("~\\Pictures")
                    if "last_tag" not in config:
                        config["last_tag"] = ""
                    if "taglist" not in config:
                        config["taglist"] = ["제주도여행", "가족모임", "테스트"]
                    if "registered_cameras" not in config:
                        config["registered_cameras"] = []
                    if "autorun_only_registered" not in config:
                        config["autorun_only_registered"] = True
                    return config
            except Exception as e:
                print("Error loading config.json:", e)
        
        default_config = {
            "restrict_to_nikon": True,
            "chkbox_tag": True,
            "chkbox_autorun": False,
            "chkbox_explorer": True,
            "chkbox_delete_after": False,
            "save_dir": os.path.expanduser("~\\Pictures"),
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

    def get_config(self):
        return self.config

    def update_config(self, new_data):
        self.config.update(new_data)
        if not self.config.get("save_dir"):
            self.config["save_dir"] = os.path.expanduser("~\\Pictures")
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
                # Exclude standard local drive letters (e.g., C:\)
                if not (len(path) == 3 and path[1] == ':' and path[2] == '\\'):
                    if name not in ["네트워크", "제어판", "Network", "Control Panel"]:
                        devices.append((name, item))
        except Exception as e:
            print("Error accessing Shell COM:", e)
        return devices

    def check_connection(self):
        devices = self._get_portable_devices()
        was_connected = self.is_connected
        if devices:
            self.is_connected = True
            self.device_name = devices[0][0]
            self.device_item = devices[0][1]
            self.device_serial = self._fetch_wmi_serial(self.device_name)
            
            if not self.initial_connection_checked:
                # App started with camera already connected -> Do nothing but wait
                self.initial_connection_checked = True
            else:
                if not was_connected:
                    # Plugged in after app started
                    if self.config.get("chkbox_autorun", False):
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

    def _fetch_wmi_serial(self, target_name):
        try:
            wmi_obj = win32com.client.GetObject("winmgmts:")
            pnp_devices = wmi_obj.InstancesOf("Win32_PnPEntity")
            for pnp in pnp_devices:
                if pnp.PNPClass == 'WPD' and pnp.Caption and target_name in pnp.Caption:
                    if pnp.DeviceID:
                        # DeviceID format: USB\VID_04B0&PID_0412\000002090218
                        return pnp.DeviceID.split('\\')[-1]
        except Exception as e:
            print(f"Error fetching WMI serial: {e}")
        return None

    def open_in_explorer(self):
        """Opens the camera device in Windows Explorer."""
        try:
            pythoncom.CoInitialize()
            devices = self._get_portable_devices()
            if devices:
                item = devices[0][1]
                path = item.Path
                try:
                    import ctypes
                    # 1 = SW_SHOWNORMAL
                    res = ctypes.windll.shell32.ShellExecuteW(None, "open", "explorer.exe", path, None, 1)
                    if res > 32:
                        return True
                except Exception as ex:
                    print("ShellExecuteW failed:", ex)
                
                try:
                    # Fallback to detached Popen
                    subprocess.Popen(['explorer.exe', path], creationflags=0x00000008)
                    return True
                except Exception as ex:
                    print("Subprocess explorer failed:", ex)
                
                # Final fallback
                item.InvokeVerb("open")
                return True
        except Exception as e:
            print("Error opening camera in explorer:", e)
        finally:
            pythoncom.CoUninitialize()
        return False

    def open_dest_explorer(self, dest_path=None):
        """Opens the target local save directory in Windows Explorer."""
        if not dest_path:
            dest_path = self.config.get("save_dir")
            if not dest_path:
                dest_path = os.path.expanduser("~\\Pictures")
        
        os.makedirs(dest_path, exist_ok=True)
        try:
            os.startfile(dest_path)
            return True
        except Exception as e:
            print("Error opening dest explorer:", e)
            try:
                subprocess.Popen(["explorer.exe", dest_path])
                return True
            except Exception as e2:
                print("Error opening explorer via subprocess:", e2)
        return False

    def get_status(self):
        return {
            "connected": self.is_connected,
            "model": self.device_name,
            "serial": self.device_serial,
            "scan": {
                "status": self.scan_state['status'],
                "count": self.scan_state['count'],
                "current_file": self.scan_state['current_file']
            },
            "fetch": {
                "status": self.fetch_state['status'],
                "total": self.fetch_state['total'],
                "copied": self.fetch_state['copied'],
                "current_file": self.fetch_state['current_file'],
                "dest_path": self.fetch_state['dest_path']
            },
            "delete": {
                "status": self.delete_state['status'],
                "total": self.delete_state['total'],
                "deleted": self.delete_state['deleted'],
                "current_file": self.delete_state['current_file']
            },
            "config": self.config
        }

    def start_scan(self):
        if self.scan_state['status'] == 'scanning':
            return False
        
        self.scan_state = {
            'status': 'scanning',
            'count': 0,
            'current_file': '스캔 시작 중...',
            'files': []
        }
        self.fetch_state['status'] = 'idle'
        self.delete_state['status'] = 'idle'
        self._scan_cancel_requested = False
        
        # 만약 자동 가져오기 설정이 켜져 있다면, 수동 스캔 버튼을 눌러도 자동으로 가져오기까지 연쇄 실행되도록 처리
        if self.config.get("chkbox_autorun"):
            self._auto_fetch_pending = True

        thread = threading.Thread(target=self._scan_worker, daemon=True)
        thread.start()
        return True

    def cancel_scan(self):
        self._scan_cancel_requested = True
        self.scan_state['status'] = 'cancelled'
        self.scan_state['current_file'] = '스캔 취소됨'
        self.fetch_state['status'] = 'idle'
        self.delete_state['status'] = 'idle'
        self._auto_fetch_pending = False

    def _scan_worker(self):
        pythoncom.CoInitialize()
        try:
            devices = self._get_portable_devices()
            if not devices:
                self.scan_state['status'] = 'complete'
                self.scan_state['current_file'] = '연결된 기기 없음'
                return

            device_item = devices[0][1]
            found_files = []

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
                                found_files.append(name) # Only string to avoid cross-thread COM errors
                                self.scan_state['count'] = len(found_files)
                                self.scan_state['current_file'] = name
                except Exception as e:
                    print("Error traversing WPD folder:", e)

            _traverse(device_item.GetFolder)

            if not self._scan_cancel_requested:
                self.scan_state['files'] = found_files
                self.scan_state['status'] = 'complete'
                self.scan_state['current_file'] = '스캔 완료'
                
                if getattr(self, '_auto_fetch_pending', False):
                    self._auto_fetch_pending = False
                    tag_name = self.config.get("autorun_tag", "")
                    self.start_fetch(tag_name=tag_name)
        except Exception as e:
            print("Error in _scan_worker:", e)
            self.scan_state['status'] = 'cancelled'
        finally:
            pythoncom.CoUninitialize()

    def start_fetch(self, tag_name=''):
        if self.fetch_state['status'] == 'fetching':
            return False
        
        if not self.scan_state['files']:
            return False

        # Build destination directory path
        base_dir = self.config.get("save_dir")
        if not base_dir:
            base_dir = os.path.expanduser("~\\Pictures")
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")

        if tag_name and tag_name.strip():
            folder_name = f"{date_str}_{tag_name.strip()}"
            self.add_tag_to_history(tag_name.strip())
        else:
            folder_name = date_str

        self.config["last_tag"] = tag_name.strip() if tag_name else ""
        self._save_config()

        dest_path = os.path.join(base_dir, folder_name)

        self.fetch_state = {
            'status': 'fetching',
            'total': len(self.scan_state['files']),
            'copied': 0,
            'current_file': '가져오기 준비 중...',
            'dest_path': dest_path,
            'copied_files': []
        }

        self.delete_state = {
            'status': 'idle',
            'total': 0,
            'deleted': 0,
            'current_file': ''
        }

        thread = threading.Thread(target=self._fetch_worker, args=(dest_path,), daemon=True)
        thread.start()
        return True

    def _fetch_worker(self, dest_path):
        pythoncom.CoInitialize()
        try:
            # Normalize path to backslashes for COM Shell.NameSpace
            dest_path = os.path.abspath(os.path.normpath(dest_path))
            os.makedirs(dest_path, exist_ok=True)
            shell = win32com.client.Dispatch("Shell.Application")
            dest_shell_folder = shell.NameSpace(dest_path)

            devices = self._get_portable_devices()
            if not devices:
                self.fetch_state['status'] = 'failed'
                self.fetch_state['current_file'] = '장치 연결 끊김'
                return

            device_item = devices[0][1]
            copied_count = 0
            
            # Re-traverse and copy (since COM objects from _scan_worker are dead)
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
                                self.fetch_state['current_file'] = name
                                target_file = os.path.join(dest_path, name)
                                
                                if os.path.exists(target_file):
                                    os.remove(target_file)
                                    
                                # 4: 숨김, 16: 모두 예, 512: 확인 안함, 1024: 에러 UI 숨김
                                dest_shell_folder.CopyHere(item, 4 | 16 | 512 | 1024)
                                
                                # 윈도우 메시지 펌핑을 통한 비동기 복사 대기
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
                                    self.fetch_state['copied_files'].append(name)
                                            
                                    copied_count += 1
                                self.fetch_state['copied'] = copied_count
                except Exception as e:
                    print("Error traversing during fetch:", e)

            _traverse_and_copy(device_item.GetFolder)

            self.fetch_state['status'] = 'complete'
            self.fetch_state['current_file'] = '가져오기 완료'

            # Auto open Explorer if enabled in config
            if self.config.get("chkbox_explorer", True):
                self.open_dest_explorer(dest_path)

        except Exception as e:
            print("Error in _fetch_worker:", e)
            self.fetch_state['status'] = 'failed'
        finally:
            pythoncom.CoUninitialize()

    def start_delete_originals(self):
        if self.fetch_state['status'] != 'complete':
            return False
        
        self.delete_state = {
            'status': 'deleting',
            'total': len(self.fetch_state.get('copied_files', [])),
            'deleted': 0,
            'current_file': '삭제 준비 중...'
        }
        
        thread = threading.Thread(target=self._delete_worker, daemon=True)
        thread.start()
        return True

    def _delete_worker(self):
        pythoncom.CoInitialize()
        try:
            devices = self._get_portable_devices()
            if not devices:
                self.delete_state['status'] = 'failed'
                self.delete_state['current_file'] = '장치 연결 끊김'
                return

            device_item = devices[0][1]
            deleted_count = 0

            def _traverse_and_delete(folder_obj):
                nonlocal deleted_count
                if not folder_obj:
                    return
                try:
                    items = folder_obj.Items()
                    has_files = False
                    for item in items:
                        if item.IsFolder:
                            _traverse_and_delete(item.GetFolder)
                        else:
                            has_files = True

                    if has_files:
                        self.delete_state['current_file'] = '카메라 폴더 파일 일괄 삭제 중...'
                        try:
                            items.InvokeVerbEx('delete')
                            deleted_count += items.Count
                            self.delete_state['deleted'] = deleted_count
                        except Exception as e_del:
                            print("Error bulk deleting items in folder:", e_del)
                except Exception as e:
                    print("Error traversing during delete:", e)

            _traverse_and_delete(device_item.GetFolder)

            self.delete_state['status'] = 'complete'
            self.delete_state['current_file'] = '삭제 완료'

        except Exception as e:
            print("Error in _delete_worker:", e)
            self.delete_state['status'] = 'failed'
        finally:
            pythoncom.CoUninitialize()

    def check_autoplay_status(self):
        import winreg
        import autorun_setup
        import sys
        
        is_frozen = getattr(sys, 'frozen', False)
        
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
            val, _ = winreg.QueryValueEx(key, autorun_setup.APP_RUN_KEY)
            winreg.CloseKey(key)
            
            expected_cmd = autorun_setup.get_detector_command()
            path_mismatch = (val != expected_cmd)
            
            return {"registered": True, "path_mismatch": path_mismatch, "is_frozen": is_frozen}
        except FileNotFoundError:
            return {"registered": False, "path_mismatch": False, "is_frozen": is_frozen}
        except Exception as e:
            print("Error checking registry:", e)
            return {"registered": False, "path_mismatch": False, "is_frozen": is_frozen}
            
    def run_autorun_setup(self, action):
        import sys
        
        arg = "--install" if action == "install" else "--uninstall"
        
        try:
            if getattr(sys, 'frozen', False):
                lpFile = sys.executable
                lpParameters = arg
            else:
                lpFile = sys.executable
                lpParameters = f'"{os.path.abspath(sys.argv[0])}" {arg}'
            
            # Using PowerShell to trigger UAC completely isolates the child process 
            # from the parent's PyInstaller SxS manifest context, 
            # fixing the "ordinal 380" (LoadIconMetric) bug in comctl32.dll on Windows.
            import subprocess
            ps_command = f"Start-Process -FilePath '{lpFile}' -ArgumentList '{lpParameters}' -Verb RunAs -Wait -WindowStyle Hidden"
            
            # CREATE_NO_WINDOW = 0x08000000
            subprocess.run(["powershell", "-Command", ps_command], creationflags=0x08000000)
            return True
        except Exception as e:
            print("Error running autorun_setup:", e)
            return False

    def start_monitoring(self, interval=2.0):
        def monitor_loop():
            pythoncom.CoInitialize()
            while True:
                self.check_connection()
                time.sleep(interval)
            pythoncom.CoUninitialize()

        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()

camera_handler = CameraHandler()
