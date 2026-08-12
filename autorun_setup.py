import os
import sys
import ctypes
import winreg

APP_RUN_KEY = "DSLRFileTransferDetector"

def get_detector_command():
    # If compiled with PyInstaller, use the executable if we built a detector exe
    # Since we are adding usb_detector.py, if frozen we might just launch app.exe --detect (but we didn't add --detect yet).
    # Let's assume we run pythonw.exe usb_detector.py if not frozen, or if frozen we might need to rely on the user running from source for now, or just use pythonw.exe.
    # Actually, for a PyInstaller build, we should launch the detector via the main exe if possible, or assume pythonw exists.
    # A cleaner approach for PyInstaller is to have app.exe check for a special flag like "--detector"
    # But since usb_detector is a separate script right now, let's just use pythonw if available.
    if getattr(sys, 'frozen', False):
        # We don't have a separate detector.exe built by PyInstaller automatically.
        # So we'll run app.exe --detector
        return f'"{sys.executable}" --detector'
    else:
        # Use pythonw to hide console
        detector_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'usb_detector.py'))
        python_exe = sys.executable.replace("python.exe", "pythonw.exe")
        return f'"{python_exe}" "{detector_path}"'

def register_autoplay():
    try:
        cmd = get_detector_command()
        
        # Register to HKCU Run (Startup)
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run")
        winreg.SetValueEx(key, APP_RUN_KEY, 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)

        print(f"[SUCCESS] 백그라운드 에이전트가 시작프로그램에 등록되었습니다.")
        print(f"[INFO] 등록된 명령어: {cmd}")
        
        # Also start it immediately if not running
        import subprocess
        subprocess.Popen(cmd, shell=True)
        
    except Exception as e:
        print(f"[ERROR] 시작프로그램 등록 중 오류 발생: {e}")

def unregister_autoplay():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_ALL_ACCESS)
        winreg.DeleteValue(key, APP_RUN_KEY)
        winreg.CloseKey(key)

        print(f"[SUCCESS] 백그라운드 에이전트가 시작프로그램에서 제거되었습니다.")
        
        # Try to kill it
        os.system("taskkill /F /IM pythonw.exe /FI \"WINDOWTITLE eq DSLRFileTransferDetector\" 2>nul")
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"[ERROR] 시작프로그램 삭제 중 오류 발생: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="DSLR AutoRun Setup")
    parser.add_argument("--install", action="store_true", help="Install AutoRun silently")
    parser.add_argument("--uninstall", action="store_true", help="Uninstall AutoRun silently")
    args, unknown = parser.parse_known_args()

    if args.install:
        register_autoplay()
        sys.exit(0)
    elif args.uninstall:
        unregister_autoplay()
        sys.exit(0)

    # Interactive mode fallback
    print("=== 백그라운드 자동 실행 설정 ===")
    print("1. 자동 실행 등록 (설치)")
    print("2. 자동 실행 제거 (삭제)")
    choice = input("원하는 작업을 선택하세요 (1/2): ").strip()
    
    if choice == '1':
        register_autoplay()
    elif choice == '2':
        unregister_autoplay()
    else:
        print("잘못된 입력입니다.")
        
    input("종료하려면 아무 키나 누르세요...")
