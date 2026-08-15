import win32com.client
import pythoncom
import sys

def check_camera():
    pythoncom.CoInitialize()
    wmi = win32com.client.GetObject("winmgmts:")
    devices = wmi.InstancesOf("Win32_PnPEntity")
    found = []
    for d in devices:
        if getattr(d, 'PNPClass', '') == 'WPD' and d.DeviceID:
            found.append(f"{d.Caption} ({d.DeviceID})")
    
    print(f"Using Interpreter: {sys.executable}")
    if found:
        print("Connected WPD Cameras:")
        for cam in found:
            print(f" - {cam}")
    else:
        print("No WPD Cameras detected.")
    pythoncom.CoUninitialize()

if __name__ == '__main__':
    check_camera()
