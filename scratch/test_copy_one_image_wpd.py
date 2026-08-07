import os
import win32com.client
import pythoncom
import time

def print_log(msg):
    print(msg, flush=True)

def main():
    dest_path = r"C:\temp"
    os.makedirs(dest_path, exist_ok=True)
    
    print_log("COM 객체 초기화 중...")
    pythoncom.CoInitialize()
    try:
        shell = win32com.client.Dispatch("Shell.Application")
        folder = shell.NameSpace(17) # 내 PC
        
        device_item = None
        for item in folder.Items():
            path = item.Path
            if not (len(path) == 3 and path[1] == ':' and path[2] == '\\'):
                if item.Name not in ["네트워크", "제어판", "Network", "Control Panel"]:
                    device_item = item
                    break
        
        if not device_item:
            print_log("디지털 카메라를 찾을 수 없습니다.")
            return
            
        print_log(f"디지털 카메라 발견: {device_item.Name}")
        print_log("이미지 파일 1개 탐색 및 복사 진행 중...")
        
        dest_shell_folder = shell.NameSpace(dest_path)
        copy_success = False

        def traverse(folder_obj, depth=0):
            nonlocal copy_success
            if copy_success or not folder_obj or depth > 5:
                return
            
            try:
                for item in folder_obj.Items():
                    if copy_success:
                        break
                    
                    if item.IsFolder:
                        traverse(item.GetFolder, depth + 1)
                    else:
                        ext = os.path.splitext(item.Name)[1].lower()
                        if ext in {'.jpg', '.jpeg', '.png', '.nef', '.cr2', '.mp4'}:
                            print_log(f"복사할 파일 선택됨: {item.Name}")
                            
                            dest_file_path = os.path.join(dest_path, item.Name)
                            if os.path.exists(dest_file_path):
                                os.remove(dest_file_path)
                                
                            print_log(f"[{dest_path}] 로 복사 시작 (CopyHere)...")
                            # 4: 진행 창 숨김, 16: 모두 예, 512: 확인창 안함, 1024: 에러 UI 숨김
                            dest_shell_folder.CopyHere(item, 4 | 16 | 512 | 1024)
                            
                            # 부모 객체들이 살아있는 상태에서 대기
                            start_time = time.time()
                            while time.time() - start_time < 20:
                                pythoncom.PumpWaitingMessages()
                                time.sleep(0.2)
                                
                                if os.path.exists(dest_file_path):
                                    size = os.path.getsize(dest_file_path)
                                    if size > 0:
                                        try:
                                            with open(dest_file_path, 'rb') as f: pass
                                            copy_success = True
                                            print_log(f"복사 성공! ({size} bytes) -> {dest_file_path}")
                                            break
                                        except IOError:
                                            pass
                            if not copy_success:
                                print_log("복사 시간 초과")
                            break # 파일 1개만 처리하고 루프 탈출
            except Exception as e:
                pass

        traverse(device_item.GetFolder)
        
        if not copy_success:
            print_log("카메라 내에서 파일을 복사하지 못했습니다.")
            
    except Exception as e:
        print_log(f"오류 발생: {e}")
    finally:
        pythoncom.CoUninitialize()
        print_log("완료.")

if __name__ == "__main__":
    main()
