import os
import win32com.client

def main():
    print("WIA (Windows Image Acquisition) 초기화 중...")
    try:
        dev_manager = win32com.client.Dispatch("WIA.DeviceManager")
        camera = None
        
        print(f"총 {dev_manager.DeviceInfos.Count}개의 WIA 장치 발견.")
        for info in dev_manager.DeviceInfos:
            # Type 2는 보통 카메라(Camera)를 의미합니다.
            name = ""
            try:
                name = info.Properties("Name").Value
            except:
                name = info.DeviceID
                
            print(f"장치 확인 중: {name} (Type: {info.Type})")
            if info.Type == 2 or "D90" in name or "D90" in info.DeviceID:
                camera = info.Connect()
                print(f"카메라 연결 성공: {name}")
                break
                
        if not camera:
            print("WIA 방식으로는 카메라를 찾을 수 없거나 연결할 수 없습니다.")
            return
            
        print("카메라 내 항목(이미지) 탐색 중...")
        if camera.Items.Count == 0:
            print("카메라 내에 항목이 없습니다.")
            return
            
        # 첫 번째 항목 가져오기
        for item in camera.Items:
            print("파일 하나를 발견했습니다. 복사(Transfer) 시도 중...")
            
            # 파일 확장자 찾기 시도
            ext = "jpg"
            try:
                ext = item.Properties("Item Extension").Value
            except:
                pass
                
            dest_path = r"C:\temp"
            os.makedirs(dest_path, exist_ok=True)
            dest_file = os.path.join(dest_path, f"wia_test_image.{ext}")
            
            if os.path.exists(dest_file):
                os.remove(dest_file)
                
            # Transfer 메서드를 사용해 파일을 다운로드 (ImageFile 객체 반환)
            image = item.Transfer()
            image.SaveFile(dest_file)
            
            print(f"WIA 복사 성공! -> {dest_file}")
            break # 1개만 복사하고 종료
            
    except Exception as e:
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    main()
