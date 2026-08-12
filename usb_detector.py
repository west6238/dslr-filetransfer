import os
import sys
import time
import json
import subprocess
import threading

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def is_ui_running():
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
                if "app.exe" in cmd and "--ui" in cmd:
                    return True
            else:
                cmd_lower = cmd.lower()
                if "python" in cmd_lower and "app.py" in cmd and "--ui" in cmd:
                    return True
    except Exception as e:
        print(f"Error checking processes: {e}")
    return False

def launch_app():
    if is_ui_running():
        return # Already running
        
    app_path = os.path.join(os.path.dirname(__file__), 'app.py')
    if getattr(sys, 'frozen', False):
        app_path = os.path.join(os.path.dirname(sys.executable), 'app.exe')
        subprocess.Popen([app_path, "--ui"])
    else:
        # Development mode
        subprocess.Popen([sys.executable, app_path, "--ui"])

def check_device_and_launch(device_id):
    if not device_id:
        return
        
    serial = device_id.split('\\')[-1]
    config = load_config()
    
    if not config.get("autorun_only_registered", True):
        if "VID_04B0" in device_id.upper():
            if config.get("restrict_to_nikon", True):
                launch_app()
            else:
                launch_app()
        return
        
    registered = config.get("registered_cameras", [])
    for cam in registered:
        if cam.get("serial") == serial:
            launch_app()
            break

def wmi_watcher_thread(stop_event):
    import win32com.client
    import pythoncom

    pythoncom.CoInitialize()
    wmi = win32com.client.GetObject("winmgmts:")
    
    # Watch for device creation events
    # We poll every 2 seconds for creation of Win32_PnPEntity
    watcher = wmi.ExecNotificationQuery(
        "SELECT * FROM __InstanceCreationEvent WITHIN 2 "
        "WHERE TargetInstance ISA 'Win32_PnPEntity' "
        "AND TargetInstance.PNPClass = 'WPD'"
    )
    
    print("Background USB detector started in thread...")
    
    while not stop_event.is_set():
        try:
            # NextEvent blocks, so we use a small timeout if possible, 
            # but win32com NextEvent doesn't easily support timeout.
            # We will just let it block and when the process exits, it gets killed.
            event = watcher.NextEvent(2000)
            instance = event.Properties_("TargetInstance").Value
            
            # WPD device connected
            device_id = instance.DeviceID
            if getattr(instance, 'PNPClass', '') == 'WPD' and device_id:
                check_device_and_launch(device_id)
                
        except Exception as e:
            # Exception can be timeout (wbemErrTimedout), which is normal.
            time.sleep(0.5)

def create_image():
    # Generate a simple icon image using PIL
    from PIL import Image, ImageDraw
    width = 64
    height = 64
    color1 = (41, 128, 185)
    color2 = (52, 152, 219)
    
    image = Image.new('RGB', (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle(
        (width // 4, height // 4, width * 3 // 4, height * 3 // 4),
        fill=color2
    )
    return image

def on_open_ui(icon, item):
    launch_app()

def on_exit(icon, item, stop_event):
    stop_event.set()
    icon.stop()

def main():
    import win32com.client
    import pythoncom
    import pystray
    from pystray import MenuItem as item
    
    pythoncom.CoInitialize()
    wmi = win32com.client.GetObject("winmgmts:")
    
    print("Checking for existing connected cameras...")
    pnp_devices = wmi.InstancesOf("Win32_PnPEntity")
    for instance in pnp_devices:
        try:
            if instance.PNPClass == 'WPD' and instance.DeviceID:
                check_device_and_launch(instance.DeviceID)
        except Exception:
            pass

    stop_event = threading.Event()
    
    # Start WMI watcher in a background thread
    t = threading.Thread(target=wmi_watcher_thread, args=(stop_event,), daemon=True)
    t.start()

    # Setup system tray icon
    menu = pystray.Menu(
        item('UI 열기', on_open_ui, default=True),
        item('종료', lambda icon, menu_item: on_exit(icon, menu_item, stop_event))
    )
    
    icon_image = create_image()
    icon = pystray.Icon("dslr_filetransfer_detector", icon_image, "DSLR USB 감시 중...", menu)
    
    print("Starting system tray icon...")
    icon.run()

if __name__ == "__main__":
    main()
