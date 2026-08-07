import os
import win32com.client
import pythoncom
import time

def copy_one_image(dest_path):
    pythoncom.CoInitialize()
    try:
        os.makedirs(dest_path, exist_ok=True)
        shell = win32com.client.Dispatch("Shell.Application")
        dest_shell_folder = shell.NameSpace(dest_path)
        
        folder = shell.NameSpace(17) # ssfDRIVES
        device_item = None
        
        # Find portable device
        for item in folder.Items():
            path = item.Path
            name = item.Name
            # Exclude standard local drives and system folders
            if not (len(path) == 3 and path[1] == ':' and path[2] == '\\'):
                if name not in ["네트워크", "제어판", "Network", "Control Panel"]:
                    device_item = item
                    break
        
        if not device_item:
            print("No camera device found.")
            return
        
        print(f"Found device: {device_item.Name}")
        
        # Traverse to find one image
        image_to_copy = None
        
        def _traverse(folder_obj):
            nonlocal image_to_copy
            if image_to_copy or not folder_obj:
                return
            for item in folder_obj.Items():
                if image_to_copy:
                    break
                if item.IsFolder:
                    _traverse(item.GetFolder)
                else:
                    ext = os.path.splitext(item.Name)[1].lower()
                    if ext in {'.jpg', '.jpeg', '.png', '.nef', '.cr2', '.mp4'}:
                        image_to_copy = item
                        break
                        
        _traverse(device_item.GetFolder)
        
        if image_to_copy:
            print(f"Copying {image_to_copy.Name} to {dest_path}")
            dest_shell_folder.CopyHere(image_to_copy, 4 | 16)
            time.sleep(2) # Wait a bit for the shell copy to finish
            
            # Verify
            target_file = os.path.join(dest_path, image_to_copy.Name)
            if os.path.exists(target_file):
                print(f"Successfully copied to: {target_file}")
            else:
                print("Copy command sent, but file not found immediately.")
        else:
            print("No images found on the camera.")
            
    except Exception as e:
        print("Error:", e)
    finally:
        pythoncom.CoUninitialize()

if __name__ == "__main__":
    copy_one_image(r"C:\temp")
