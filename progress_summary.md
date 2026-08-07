# DSLR 카메라 AutoRun v2 진행 상황 요약

## 1. UI/UX 및 창 크기 조정
- 브라우저 상단바와 앱 화면 사이의 공백을 줄이고 더 넓은 화면을 위해, 브라우저 윈도우 크기를 기존 `800 x 600` 사이즈에서 비율에 맞춰 최종적으로 `800 x 800` 사이즈로 넉넉하게 확장했습니다.
- Edge 브라우저가 창 크기 캐시를 유지하는 현상을 우회하기 위해 파이썬 Popen 실행 시 파라미터(`?size=800x800`)를 추가하고 HTML 렌더링 시 자바스크립트로 `window.resizeTo(800, 800)`를 호출하도록 설정했습니다.
- 불필요한 브라우저 스크롤바를 숨기기 위해 `style.css`에 `::-webkit-scrollbar { display: none; }` 속성을 추가하였습니다.

## 2. 브라우저 아이콘(파비콘) 적용
- 브라우저 상단 타이틀바와 작업표시줄에서 기본 '지구본' 아이콘이 표시되는 현상을 제거하기 위해, `index.html`에 카메라 이모지(📷) 형태의 Inline SVG 파비콘(Favicon)을 즉시 적용하였습니다.

## 3. PyInstaller 단일 배포(.exe) 지원 추가
- 파이썬 스크립트 외에 의존하는 HTML, CSS, JS 파일들(`static`, `templates` 폴더)을 배포용 `.exe` 파일 한 개에 모두 압축하기 위해 `app.py`에 PyInstaller 호환성 패치(제안 A)를 적용했습니다.
- `sys._MEIPASS` 경로를 참조하는 `resource_path` 헬퍼 함수를 통해, 개발 환경과 PyInstaller 런타임 환경 양쪽에서 문제없이 리소스 폴더를 인식하도록 Flask `static_folder`와 `template_folder` 옵션을 동적으로 수정했습니다.

## 4. 기타 취소된 작업 내역 및 Native Browser(pywebview) 부적합 사유
- 완전한 프레임리스(상단바 제거) 및 커스텀 디자인을 위해 `pywebview` 도입을 시도하였으나, 아래와 같은 치명적인 호환성 문제로 인해 적용을 취소하고 기존의 Edge 브라우저(`--app`) 실행 방식으로 롤백하였습니다.
  - **투명화 버그 (Hit-Testing 이슈)**: Windows의 Edge WebView2 엔진에서 창 투명화(`transparent=True`)와 프레임리스(`frameless=True`) 옵션을 동시 적용할 경우, 웹뷰의 렌더링 레이어가 마우스 이벤트를 가로채어 앱 내부의 모든 버튼과 UI의 클릭을 막아버리는 하드웨어 가속/렌더링 결함이 발생합니다.
  - **대체 수단 부재**: CSS의 `pointer-events` 속성을 조작하거나 1%의 불투명도를 주는 등의 우회 방식(Electron 등에서 쓰이는 방식)이 WebView2 자체의 결함으로 인해 제대로 동작하지 않아, 투명한 드롭 섀도우(Drop-shadow) 및 둥근 모서리 효과를 유지하면서 사용자 클릭을 입력받는 것이 불가능함을 확인했습니다.
