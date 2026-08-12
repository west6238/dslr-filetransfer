import os
import sys

# UAC 환경에서 무거운 COM 모듈(win32com 등) 로딩 시 발생하는 
# 오디날 380 (ordinal 380) 충돌을 방지하기 위해 최상단에서 --install / --uninstall 처리
if __name__ == '__main__':
    if "--install" in sys.argv:
        import autorun_setup
        autorun_setup.register_autoplay()
        sys.exit(0)
    elif "--uninstall" in sys.argv:
        import autorun_setup
        autorun_setup.unregister_autoplay()
        sys.exit(0)
    elif "--detector" in sys.argv:
        import usb_detector
        usb_detector.main()
        sys.exit(0)
    
    # We will handle --ui below, but it shouldn't exit early because it needs to run Flask.

import time
import subprocess
import webbrowser
import threading
from flask import Flask, render_template, jsonify, request
import requests
from camera_handler import camera_handler

CURRENT_VERSION = "v1.0.0"
download_progress = {"percent": 0, "status": "idle", "error": None}
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

app = Flask(__name__, 
            static_folder=resource_path('static'), 
            template_folder=resource_path('templates'))

# Start monitoring PTP/MPD devices in background
camera_handler.start_monitoring()

def is_detector_running():
    try:
        import win32com.client
        wmi = win32com.client.GetObject("winmgmts:")
        processes = wmi.InstancesOf("Win32_Process")
        
        current_pid = os.getpid()
        is_frozen = getattr(sys, 'frozen', False)
        
        for p in processes:
            if p.ProcessId == current_pid:
                continue
                
            cmd = p.CommandLine
            if not cmd:
                continue
                
            if is_frozen:
                if "app.exe" in cmd and "--detector" in cmd:
                    return True
            else:
                cmd_lower = cmd.lower()
                if "python" in cmd_lower and ("usb_detector.py" in cmd or ("app.py" in cmd and "--detector" in cmd)):
                    return True
    except Exception as e:
        print(f"Error checking processes: {e}")
    return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    return jsonify(camera_handler.get_status())

@app.route('/api/open-explorer', methods=['POST'])
def open_explorer():
    success = camera_handler.open_in_explorer()
    if success:
        print("[알림] 탐색기를 열었으므로 앱을 종료합니다...")
        def terminate_app():
            time.sleep(1.5)
            os._exit(0)
        threading.Thread(target=terminate_app, daemon=True).start()
    return jsonify({"success": success})

@app.route('/api/open-save-dir', methods=['POST'])
def open_save_dir():
    data = request.get_json(silent=True) or {}
    dest_path = data.get('dest_path')
    success = camera_handler.open_dest_explorer(dest_path)
    return jsonify({"success": success})

@app.route('/api/scan/start', methods=['POST'])
def start_scan():
    success = camera_handler.start_scan()
    return jsonify({"success": success})
@app.route('/api/scan/cancel', methods=['POST'])
def cancel_scan():
    camera_handler.cancel_scan()
    return jsonify({"success": True})

@app.route('/api/fetch/start', methods=['POST'])
def start_fetch():
    data = request.get_json(silent=True) or {}
    tag_name = data.get('tag', '')
    success = camera_handler.start_fetch(tag_name)
    return jsonify({"success": success})

@app.route('/api/fetch/delete-originals', methods=['POST'])
def delete_originals():
    success = camera_handler.start_delete_originals()
    return jsonify({"success": success})

@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    if request.method == 'POST':
        new_data = request.get_json(silent=True) or {}
        updated_config = camera_handler.update_config(new_data)
        return jsonify({"success": True, "config": updated_config})
    return jsonify(camera_handler.get_config())

@app.route('/api/select-dir', methods=['GET'])
def select_dir():
    import tkinter as tk
    from tkinter import filedialog
    
    root = tk.Tk()
    root.attributes('-topmost', True)
    root.withdraw()
    selected_path = filedialog.askdirectory(parent=root, title="저장 폴더 선택")
    root.destroy()
    
    return jsonify({"path": selected_path})

@app.route('/api/autorun/status', methods=['GET'])
def get_autorun_status():
    status = camera_handler.check_autoplay_status()
    return jsonify(status)

@app.route('/api/autorun/register', methods=['POST'])
def register_autorun():
    success = camera_handler.run_autorun_setup("install")
    return jsonify({"success": success})

@app.route('/api/autorun/unregister', methods=['POST'])
def unregister_autorun():
    success = camera_handler.run_autorun_setup("uninstall")
    return jsonify({"success": success})

@app.route('/api/cameras/list', methods=['GET'])
def list_cameras():
    config = camera_handler.get_config()
    return jsonify({
        "registered_cameras": config.get("registered_cameras", []),
        "autorun_only_registered": config.get("autorun_only_registered", True)
    })

@app.route('/api/cameras/register', methods=['POST'])
def register_camera():
    data = request.get_json(silent=True) or {}
    serial = data.get('serial')
    model = data.get('model')
    name = data.get('name', f"{model} ({serial})")
    
    if not serial or not model:
        return jsonify({"success": False, "error": "Missing serial or model"})
        
    config = camera_handler.get_config()
    registered = config.get("registered_cameras", [])
    
    # Check if already registered
    for cam in registered:
        if cam.get('serial') == serial:
            cam['name'] = name # Update name if already exists
            camera_handler.update_config({"registered_cameras": registered})
            return jsonify({"success": True})
            
    registered.append({
        "model": model,
        "serial": serial,
        "name": name
    })
    camera_handler.update_config({"registered_cameras": registered})
    return jsonify({"success": True})

@app.route('/api/cameras/delete', methods=['POST'])
def delete_camera():
    data = request.get_json(silent=True) or {}
    serial = data.get('serial')
    
    if not serial:
        return jsonify({"success": False, "error": "Missing serial"})
        
    config = camera_handler.get_config()
    registered = config.get("registered_cameras", [])
    
    new_registered = [cam for cam in registered if cam.get('serial') != serial]
    
    if len(new_registered) != len(registered):
        camera_handler.update_config({"registered_cameras": new_registered})
        return jsonify({"success": True})
        
    return jsonify({"success": False, "error": "Camera not found"})

@app.route('/api/check-update', methods=['GET'])
def check_update():
    try:
        url = "https://api.github.com/repos/west6238/dslr-filetransfer/releases/latest"
        resp = requests.get(url, timeout=5)
        
        if resp.status_code == 404:
            # 릴리즈가 아직 등록되지 않은 경우
            return jsonify({
                "has_update": False,
                "current_version": CURRENT_VERSION
            })
            
        resp.raise_for_status()
        data = resp.json()
        latest_version = data.get("tag_name", "")
        # Remove 'v' prefix if present for simple string comparison, though string comparison works fine for v1.0.0 vs v1.0.1
        has_update = latest_version and latest_version != CURRENT_VERSION
        return jsonify({
            "has_update": has_update,
            "latest_version": latest_version,
            "current_version": CURRENT_VERSION,
            "release_notes": data.get("body", ""),
            "assets": data.get("assets", [])
        })
    except Exception as e:
        print(f"[업데이트] 버전 확인 실패: {e}")
        return jsonify({"has_update": False, "error": str(e)})

@app.route('/api/download-update', methods=['POST'])
def download_update():
    global download_progress
    data = request.get_json(silent=True) or {}
    download_url = data.get("url")
    if not download_url:
        return jsonify({"success": False, "error": "다운로드 URL이 없습니다."})

    download_progress = {"percent": 0, "status": "downloading", "error": None}

    def do_download():
        global download_progress
        try:
            exe_dir = os.path.dirname(sys.executable)
            parent_dir = os.path.dirname(exe_dir)
            temp_zip_path = os.path.join(parent_dir, "update_temp.zip")
            
            resp = requests.get(download_url, stream=True, timeout=10)
            resp.raise_for_status()
            total_size = int(resp.headers.get('content-length', 0))
            downloaded = 0
            with open(temp_zip_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            download_progress["percent"] = int((downloaded / total_size) * 100)
            download_progress["status"] = "completed"
            download_progress["percent"] = 100
        except Exception as e:
            print(f"[업데이트] 다운로드 실패: {e}")
            download_progress["status"] = "error"
            download_progress["error"] = str(e)

    threading.Thread(target=do_download, daemon=True).start()
    return jsonify({"success": True})

@app.route('/api/download-progress', methods=['GET'])
def get_download_progress():
    global download_progress
    return jsonify(download_progress)

@app.route('/api/apply-update', methods=['POST'])
def apply_update():
    exe_path = sys.executable
    exe_dir = os.path.dirname(exe_path)
    exe_name = os.path.basename(exe_path)
    parent_dir = os.path.dirname(exe_dir)
    
    temp_zip_path = os.path.join(parent_dir, "update_temp.zip")
    temp_extract_dir = os.path.join(parent_dir, "update_temp")
    bat_path = os.path.join(parent_dir, "update.bat")
    
    import zipfile
    import shutil
    
    if os.path.exists(temp_extract_dir):
        shutil.rmtree(temp_extract_dir, ignore_errors=True)
    os.makedirs(temp_extract_dir, exist_ok=True)
    
    try:
        with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_extract_dir)
    except Exception as e:
        print(f"[업데이트] 압축 해제 실패: {e}")
        return jsonify({"success": False, "error": f"압축 해제 실패: {str(e)}"})
        
    exe_found_dir = temp_extract_dir
    items = os.listdir(temp_extract_dir)
    if len(items) == 1 and os.path.isdir(os.path.join(temp_extract_dir, items[0])):
        exe_found_dir = os.path.join(temp_extract_dir, items[0])
        
    if not os.path.exists(os.path.join(exe_found_dir, exe_name)):
        return jsonify({"success": False, "error": "압축 파일 내에 실행 파일이 없습니다."})

    bat_content = f"""@echo off
title DSLR File Transfer Update
echo [Update] Waiting for app to close...
timeout /t 2 /nobreak > nul
:loop
tasklist | find /i "{exe_name}" > nul
if not errorlevel 1 (
    timeout /t 1 /nobreak > nul
    goto loop
)
echo [Update] Replacing application folder...
rmdir /s /q "{exe_dir}"
if exist "{exe_dir}" (
    timeout /t 1 /nobreak > nul
    goto loop
)
move /y "{exe_found_dir}" "{exe_dir}" > nul
rmdir /s /q "{temp_extract_dir}" > nul 2>&1
del "{temp_zip_path}" > nul 2>&1
echo [Update] Starting app...
cd /d "{exe_dir}"
start "" "{exe_name}"
del "%~f0"
"""
    try:
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)
            
        # PyInstaller 환경 변수 제거 (새 앱이 기존 임시 폴더를 재사용하려다 DLL 로드 실패하는 현상 방지)
        env = os.environ.copy()
        
        # PyInstaller가 설정한 내부 환경변수를 모두 제거하여 자식 프로세스(새 앱)가 완전히 깨끗한 상태로 실행되도록 함
        for key in list(env.keys()):
            if key.startswith('_PYI_') or key.startswith('_MEI'):
                env.pop(key, None)
                
        # PATH 환경 변수에서 현재 _MEIPASS 경로를 제거
        mei_path = getattr(sys, '_MEIPASS', None)
        if mei_path and 'PATH' in env:
            paths = env['PATH'].split(os.pathsep)
            paths = [p for p in paths if mei_path.lower() not in p.lower()]
            env['PATH'] = os.pathsep.join(paths)

        # 백그라운드로 스크립트 실행
        subprocess.Popen(["cmd.exe", "/c", bat_path], creationflags=subprocess.CREATE_NO_WINDOW, env=env, cwd=parent_dir)
        # 앱 종료 예약
        threading.Thread(target=lambda: (time.sleep(1.0), os._exit(0)), daemon=True).start()
        return jsonify({"success": True})
    except Exception as e:
        print(f"[업데이트] 적용 스크립트 생성 실패: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/shutdown', methods=['POST'])
def shutdown_app():
    # Delay termination slightly to allow the HTTP response to be sent and external processes to launch
    threading.Thread(target=lambda: (time.sleep(2.0), os._exit(0)), daemon=True).start()
    return jsonify({"success": True})

last_ping_time = time.time()

@app.route('/api/ping', methods=['POST'])
def ping():
    global last_ping_time
    last_ping_time = time.time()
    return jsonify({"success": True})

def launch_app_window():
    time.sleep(1.2)  # Wait for Flask server startup
    url = "http://127.0.0.1:5000"
    
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    
    edge_bin = next((p for p in edge_paths if os.path.exists(p)), None)
    
    if edge_bin:
        print("[알림] Edge 데스크톱 앱 모드로 창을 띄웁니다...")
        # URL에 파라미터를 추가하여 Edge가 이전 창 크기 캐시를 무시하고 새 사이즈를 적용하도록 유도
        subprocess.Popen([edge_bin, f"--app={url}?size=800x800", "--window-size=800,800"])
    else:
        print("[알림] 기본 웹 브라우저로 엽니다...")
        webbrowser.open(url)

if __name__ == '__main__':

    if "--ui" in sys.argv:
        # Detector spawned us, so we just run the UI natively
        pass
    else:
        # User double-clicked app.exe or ran python app.py manually
        if not is_detector_running():
            print("[INFO] 첫 번째 실행: 백그라운드 에이전트(detector) 모드로 숨어 들어갑니다.")
            if getattr(sys, 'frozen', False):
                subprocess.Popen([sys.executable, "--detector"])
            else:
                subprocess.Popen([sys.executable, "app.py", "--detector"])
            
            # 개발 모드(터미널)일 때는 바로 UI를 띄워주는 것이 테스트에 유리하지만,
            # 시나리오의 완벽한 일치를 위해 배포판과 동일하게 detector만 띄우고 종료합니다.
            sys.exit(0)
        else:
            print("[INFO] 이미 detector가 동작 중입니다. UI 화면(브라우저)을 띄웁니다.")
            # 이미 detector가 동작 중이므로 아래 Flask 런 루틴을 타서 UI가 열리게 됩니다.
            pass

    def heartbeat_monitor():
        global last_ping_time
        time.sleep(15) # wait for startup
        while True:
            time.sleep(2)
            if time.time() - last_ping_time > 10:
                print("[알림] 브라우저(UI)와 연결이 끊겨 앱을 자동 종료합니다.")
                os._exit(0)

    threading.Thread(target=heartbeat_monitor, daemon=True).start()

    print("DSLR 사진 가져오기 카메라 앱 UI를 시작합니다 (http://127.0.0.1:5000)...")
    threading.Thread(target=launch_app_window, daemon=True).start()
    app.run(host='127.0.0.1', port=5000, debug=False)
