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
        return True, "시작프로그램 자동 실행이 성공적으로 등록되었습니다."
    except WindowsError as e:
        return False, f"등록 중 오류가 발생했습니다: {e}"

def unregister_startup():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, APP_KEY_NAME)
        winreg.CloseKey(key)
        return True, "시작프로그램 자동 실행이 성공적으로 해제되었습니다."
    except FileNotFoundError:
        return True, "이미 레지스트리에 등록되어 있지 않습니다."
    except WindowsError as e:
        return False, f"삭제 중 오류가 발생했습니다: {e}"
