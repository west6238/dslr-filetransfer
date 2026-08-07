import os
import sys
import ctypes
import winreg

APP_PROGID = "UsbAppAutoRun_v2.App"
APP_NAME = "DSLR 사진/비디오 가져오기 (usbapp_autorun_v2)"
PROVIDER = "DSLR AutoRun"

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def get_app_command():
    # If compiled with PyInstaller, use the executable
    if getattr(sys, 'frozen', False):
        return f'"{sys.executable}" --autoplay "%1"'
    else:
        # Otherwise use the python executable and app.py
        app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'app.py'))
        python_exe = sys.executable
        return f'"{python_exe}" "{app_path}" --autoplay "%1"'

def register_autoplay():
    try:
        cmd = get_app_command()
        
        # 1. Register ProgID
        prog_id_key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\Classes\{APP_PROGID}")
        winreg.SetValue(prog_id_key, "", winreg.REG_SZ, APP_NAME)
        
        cmd_key = winreg.CreateKey(prog_id_key, rf"shell\open\command")
        winreg.SetValue(cmd_key, "", winreg.REG_SZ, cmd)
        
        winreg.CloseKey(cmd_key)
        winreg.CloseKey(prog_id_key)

        # 2. Register AutoPlay Handler
        handler_key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\AutoplayHandlers\Handlers\{APP_PROGID}")
        winreg.SetValueEx(handler_key, "Action", 0, winreg.REG_SZ, APP_NAME)
        winreg.SetValueEx(handler_key, "Provider", 0, winreg.REG_SZ, PROVIDER)
        winreg.SetValueEx(handler_key, "InvokeProgID", 0, winreg.REG_SZ, APP_PROGID)
        winreg.SetValueEx(handler_key, "InvokeVerb", 0, winreg.REG_SZ, "open")
        winreg.SetValueEx(handler_key, "InitCmdLine", 0, winreg.REG_SZ, cmd)
        winreg.SetValueEx(handler_key, "DefaultIcon", 0, winreg.REG_SZ, cmd.split('"')[1] + ",0")
        winreg.CloseKey(handler_key)

        # 3. Associate with various Events
        event_keys = [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\AutoplayHandlers\EventHandlers\WPD\ImageSource",
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\AutoplayHandlers\EventHandlers\WPD\VideoSource",
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\AutoplayHandlers\EventHandlers\WPD\Source",
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\AutoplayHandlers\EventHandlers\ShowPicturesOnArrival",
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\AutoplayHandlers\EventHandlers\UnknownContentOnArrival",
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\AutoplayHandlers\EventHandlers\DeviceArrival"
        ]
        
        for key_path in event_keys:
            try:
                event_key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, key_path)
                winreg.SetValueEx(event_key, APP_PROGID, 0, winreg.REG_SZ, "")
                winreg.CloseKey(event_key)
            except Exception as e:
                print(f"[WARN] Failed to register event {key_path}: {e}")

        # 4. Register WIA / StillImage Event Handler (For DSLR cameras like D90)
        try:
            wia_key_path = rf"SYSTEM\CurrentControlSet\Control\StillImage\Events\STIProxyEvent\{APP_PROGID}"
            wia_key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, wia_key_path)
            winreg.SetValueEx(wia_key, "Name", 0, winreg.REG_SZ, APP_NAME)
            winreg.SetValueEx(wia_key, "Desc", 0, winreg.REG_SZ, APP_NAME)
            winreg.SetValueEx(wia_key, "Icon", 0, winreg.REG_SZ, cmd.split('"')[1] + ",0")
            winreg.SetValueEx(wia_key, "Cmdline", 0, winreg.REG_SZ, cmd)
            winreg.CloseKey(wia_key)
        except Exception as e:
            print(f"[WARN] Failed to register WIA event handler: {e}")

        print(f"[SUCCESS] AutoPlay 핸들러가 성공적으로 등록되었습니다.")
        print(f"[INFO] 등록된 명령어: {cmd}")
    except Exception as e:
        print(f"[ERROR] 레지스트리 등록 중 오류 발생: {e}")

def unregister_autoplay():
    try:
        # Delete Event Handlers
        event_keys = [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\AutoplayHandlers\EventHandlers\WPD\ImageSource",
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\AutoplayHandlers\EventHandlers\WPD\VideoSource",
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\AutoplayHandlers\EventHandlers\WPD\Source",
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\AutoplayHandlers\EventHandlers\ShowPicturesOnArrival",
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\AutoplayHandlers\EventHandlers\UnknownContentOnArrival",
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\AutoplayHandlers\EventHandlers\DeviceArrival"
        ]
        for key_path in event_keys:
            try:
                event_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_ALL_ACCESS)
                winreg.DeleteValue(event_key, APP_PROGID)
                winreg.CloseKey(event_key)
            except FileNotFoundError:
                pass
            except Exception as e:
                pass
            
        # Delete Handler
        try:
            winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\AutoplayHandlers\Handlers\{APP_PROGID}")
        except FileNotFoundError:
            pass

        # Delete ProgID
        try:
            winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\Classes\{APP_PROGID}\shell\open\command")
            winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\Classes\{APP_PROGID}\shell\open")
            winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\Classes\{APP_PROGID}\shell")
            winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\Classes\{APP_PROGID}")
        except FileNotFoundError:
            pass

        # Delete WIA / StillImage Event Handler
        try:
            winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, rf"SYSTEM\CurrentControlSet\Control\StillImage\Events\STIProxyEvent\{APP_PROGID}")
        except FileNotFoundError:
            pass

        print(f"[SUCCESS] AutoPlay 핸들러가 성공적으로 삭제되었습니다.")
    except Exception as e:
        print(f"[ERROR] 레지스트리 삭제 중 오류 발생: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="DSLR AutoRun Setup")
    parser.add_argument("--install", action="store_true", help="Install AutoRun silently")
    parser.add_argument("--uninstall", action="store_true", help="Uninstall AutoRun silently")
    args, unknown = parser.parse_known_args()

    if not is_admin():
        # Re-run with admin rights and pass the same arguments
        print("관리자 권한으로 다시 실행합니다...")
        args_str = " ".join(sys.argv[1:])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{os.path.abspath(__file__)}" {args_str}', None, 1)
        sys.exit()

    if args.install:
        register_autoplay()
        sys.exit(0)
    elif args.uninstall:
        unregister_autoplay()
        sys.exit(0)

    # Interactive mode fallback
    print("=== DSLR AutoRun AutoPlay 설정 ===")
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
