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

import time
import subprocess
import webbrowser
import threading
from flask import Flask, render_template, jsonify, request
from camera_handler import camera_handler
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

app = Flask(__name__, 
            static_folder=resource_path('static'), 
            template_folder=resource_path('templates'))

# Start monitoring PTP/MPD devices in background
camera_handler.start_monitoring()

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

    # 1. Nikon 기기 연결 검사 (AutoRun 시 타사 기기나 폰 연결 무시)
    if "--autoplay" in sys.argv:
        config = camera_handler.get_config()
        if config.get("restrict_to_nikon", True):
            is_nikon_connected = False
            try:
                import win32com.client
                wmi = win32com.client.GetObject("winmgmts:")
                
                # USB 연결 직후 WMI에 반영되기까지 시간이 걸릴 수 있으므로 최대 5초 대기하며 재시도
                for attempt in range(5):
                    pnp_devices = wmi.InstancesOf("Win32_PnPEntity")
                    for pnp in pnp_devices:
                        if pnp.DeviceID and "VID_04B0" in pnp.DeviceID.upper():
                            is_nikon_connected = True
                            break
                    
                    if is_nikon_connected:
                        break
                        
                    time.sleep(1.0)
                    
            except Exception as e:
                print(f"[경고] WMI 기기 검사 실패: {e}")
                # WMI 실패 시 기본 이름 기반 검사로 폴백 (약 1.5초 대기 후 장치 탐색)
                time.sleep(1.5)
                camera_handler.check_connection()
                if camera_handler.device_name and "NIKON" in camera_handler.device_name.upper():
                    is_nikon_connected = True

            if not is_nikon_connected:
                print("[알림] Nikon 카메라가 발견되지 않아 조용히 종료합니다.")
                sys.exit(0)

    def heartbeat_monitor():
        global last_ping_time
        time.sleep(15) # wait for startup
        while True:
            time.sleep(2)
            if time.time() - last_ping_time > 10:
                print("[알림] 브라우저(UI)와 연결이 끊겨 앱을 자동 종료합니다.")
                os._exit(0)

    threading.Thread(target=heartbeat_monitor, daemon=True).start()

    print("DSLR 사진 가져오기 카메라 AutoRun 앱을 시작합니다 (http://127.0.0.1:5000)...")
    threading.Thread(target=launch_app_window, daemon=True).start()
    app.run(host='127.0.0.1', port=5000, debug=False)
