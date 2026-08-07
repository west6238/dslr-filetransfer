# usbapp_autorun_v2 작업 및 변환 로그

## 2026-08-06
- `usbapp_autorun_v2` 작업 폴더 생성 및 초기화
- 기존 USB Mass Storage 감지 방식에서 PTP/MTP 디지털 캠코더(예: D90) 감지 방식으로 전환 계획 수립 및 승인 완료
- 기본 스켈레톤 코드 구현: `app.py` (Flask + pywebview), `index.html`, `style.css`
- **1차 시도 (`ptpy` 라이브러리 사용)**:
  - `ptpy`를 통한 스크립트 실행 중 `NoBackendError` 발생.
  - 윈도우에서는 기본적으로 WPD(Windows Portable Devices) 드라이버를 사용하기 때문에 `libusb` 등의 백엔드 드라이버가 없어 에러가 발생함.
  - `libusb`용 드라이버를 강제 설치할 경우 윈도우 탐색기(내 PC)에서 기기(D90) 접근이 막히는 치명적 단점이 있음을 확인.
- **2차 시도 (WPD 네이티브 방식 적용 - 해결 완료)**:
  - 탐색기 호환성을 유지하기 위해 `ptpy` 대신 윈도우 네이티브 API인 COM 객체를 활용하도록 방향 수정.
  - `requirements.txt`에 `pywin32` 패키지 추가.
  - `camera_handler.py`를 전면 수정하여 `win32com.client`의 `Shell.Application` 객체를 호출해 휴대용 장치(WPD)를 감지하도록 로직 변경.
- **가상환경 적용 및 검증**:
  - `C:\Python\Python312` 버전을 기반으로 `.venv` 가상환경 생성.
  - 의존성 패키지 설치 완료 후 앱 정상 구동 확인.
- **WPD 기반 파일 복사 에러(0x8007001F) 분석 및 해결**:
  - `Shell.Application.CopyHere` 호출 시 COM 스레드 간 객체 공유 문제(Cross-thread COM Exception)로 인해 `0x8007001F` (장치에 연결할 수 없습니다) 에러가 발생하는 것을 파악.
  - `_scan_worker` 스레드에서는 파일 이름(문자열)만 저장하고, `_fetch_worker` 스레드 실행 시 기기를 재순회하여 안전하게 새 COM 객체를 다루도록 로직 전면 개편.
  - 비동기 복사 진행 중 앱이 멈추거나 튕기지 않도록 `pythoncom.PumpWaitingMessages()` 메시지 펌핑 대기 루프를 추가하여 안정성 확보.
- **테스트 환경 원본 보호 확인**:
  - 프로그램적 개입 시 원본 유실이 발생하지 않도록 `MoveHere`가 아닌 `CopyHere` 명령어만 사용함을 더블 체크.
- **연결 해제 시 자동 종료 기능 추가**:
  - USB 연결이 강제 해제될 경우, 프론트엔드 폴링 로직에서 이를 즉각 감지하여 화면 중앙에 3초 카운트다운 팝업창 표시.
  - 카운트다운 완료 후 `/api/shutdown` 라우트를 호출해 Flask 서버(`os._exit(0)`)와 브라우저 UI(`window.close()`)를 동시에 안전하게 종료하도록 구현.
