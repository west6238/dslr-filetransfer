import win32com.client
import pythoncom
import os
import time

pythoncom.CoInitialize()
shell = win32com.client.Dispatch("Shell.Application")

# Find device
folder = shell.NameSpace(17) # ssfDRIVES
device_item = None
for item in folder.Items():
    path = item.Path
    name = item.Name
    if not (len(path) == 3 and path[1] == ':' and path[2] == '\\'):
        if name not in ["네트워크", "제어판", "Network", "Control Panel"]:
            device_item = item
            break

if not device_item:
    print("No device found")
else:
    print("Found device:", device_item.Name)
    dest_path = r"C:\workbin4py\usbapp_autorun_v2\scratch\test_copy"
    os.makedirs(dest_path, exist_ok=True)
    dest_folder = shell.NameSpace(dest_path)
    print("Dest folder:", dest_folder)
    
    # Traverse and copy first media file
    def _traverse_and_copy(folder_obj):
        if not folder_obj: return False
        for item in folder_obj.Items():
            if item.IsFolder:
                if _traverse_and_copy(item.GetFolder): return True
            else:
                ext = os.path.splitext(item.Name)[1].lower()
                if ext in [".jpg", ".jpeg", ".png", ".mp4", ".mov", ".avi"]:
                    print("Copying:", item.Name)
                    try:
                        dest_folder.CopyHere(item, 4 | 16 | 512 | 1024)
                        # Pump messages
                        for _ in range(50):
                            pythoncom.PumpWaitingMessages()
                            time.sleep(0.1)
                            if os.path.exists(os.path.join(dest_path, item.Name)):
                                print("File copied successfully!")
                                return True
                        print("Timeout copying file")
                    except Exception as e:
                        print("Error copying:", e)
                    return True
        return False
    
    _traverse_and_copy(device_item.GetFolder)

pythoncom.CoUninitialize()
