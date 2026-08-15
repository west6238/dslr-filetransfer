import winreg
import sys
import os

APP_KEY_NAME = "DSLR_FileTransfer"
REGISTRY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"

def get_executable_path():
    if getattr(sys, 'frozen', False):
        return sys.executable
    return f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'

def is_registered_in_startup():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH, 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, APP_KEY_NAME)
        winreg.CloseKey(key)
        
        expected_path = f'{get_executable_path()} --tray'
        return value == expected_path
    except WindowsError:
        return False

def register_startup():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH, 0, winreg.KEY_SET_VALUE)
        value = f'{get_executable_path()} --tray'
        winreg.SetValueEx(key, APP_KEY_NAME, 0, winreg.REG_SZ, value)
        winreg.CloseKey(key)
        return True
    except WindowsError as e:
        print("Failed to register startup:", e)
        return False
