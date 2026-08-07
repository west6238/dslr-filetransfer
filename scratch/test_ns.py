import win32com.client
import pythoncom
import os

pythoncom.CoInitialize()
shell = win32com.client.Dispatch("Shell.Application")

test_dir = r"C:\workbin4py\usbapp_autorun_v2\scratch\test_folder"
os.makedirs(test_dir, exist_ok=True)
print("Is abs?", os.path.isabs(test_dir))
ns = shell.NameSpace(test_dir)
print("NameSpace returned:", ns)

test_dir2 = os.path.abspath(test_dir)
ns2 = shell.NameSpace(test_dir2)
print("NameSpace(abs) returned:", ns2)

pythoncom.CoUninitialize()
