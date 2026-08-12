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

def main():
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
    
    print("Checking for existing connected cameras...")
    pnp_devices = wmi.InstancesOf("Win32_PnPEntity")
    for instance in pnp_devices:
        try:
            if instance.PNPClass == 'WPD' and instance.DeviceID:
                check_device_and_launch(instance.DeviceID)
        except Exception:
            pass
            
    print("Background USB detector started...")
    
    while True:
        try:
            event = watcher.NextEvent()
            instance = event.Properties_("TargetInstance").Value
            
            # WPD device connected
            device_id = instance.DeviceID
            if getattr(instance, 'PNPClass', '') == 'WPD' and device_id:
                check_device_and_launch(device_id)
                
        except Exception as e:
            time.sleep(1)

if __name__ == "__main__":
    main()
