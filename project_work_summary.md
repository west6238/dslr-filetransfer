# DSLR File Transfer 개발 및 문제 해결 최종 작업 정리

이 문서는 DSLR 카메라 자동 사진 가져오기 앱(`DSLR File Transfer`)의 업데이트 시스템 개선, Windows 보안/경고 이슈 해결, 그리고 MTP 원본 파일 일괄 삭제 최적화 작업 내역을 정리한 기록입니다.

---

## 📌 주요 작업 및 해결 내역

### 1. 셀프 업데이트 시스템 V2 리팩토링 및 배포 방식 변경
- **문제점**:
  - 이전 PyInstaller `--onefile` 단일 실행 파일 방식 사용 시 Windows Defender 및 백신 프로그램의 오탐(접근 권한 없음 오류 창) 문제 발생.
  - 실행 시 `_MEIxxxx` 임시 폴더 압축 해제로 인한 실행 지연 및 `python312.dll LoadLibrary` 오류 팝업 발생.
  - 업데이트 후 기존 앱 폴더 삭제 시 실행 중인 배치 파일(`update.bat`)이 삭제 대상 폴더 내부에서 동작하여 폴더 덮어쓰기 무한 루프 발생.
- **해결 방안**:
  - **`--onedir` 빌드 방식으로 전환**: `DSLR_FileTransfer_onedir.spec`을 생성하여 디렉토리 형태 패키징 적용.
  - **`.zip` 기반 업데이트 로직 구현**: GitHub Release 자산 규격을 `.exe` 단일 파일에서 전체 폴더를 포함한 `.zip` 압축 파일로 변경.
  - **디렉토리 잠금(cwd) 해제**: `app.py`에서 `update.bat` 프로세스를 실행할 때 실행 작업 위치(`cwd`)를 상위 폴더(`parent_dir`)로 지정하여 구버전 폴더가 원활히 삭제되고 교체되도록 수정.
  - **환경 변수 정화**: 자식 프로세스 실행 시 `sys._MEIPASS` 관련 환경 변수를 제거하여 DLL 로딩 에러 방지.

---

### 2. DSLR(MTP 기기) 원본 파일 일괄 삭제 최적화
- **문제점**:
  - 미디어 파일 가져오기(Fetch) 완료 후 `원본 삭제` 실행 시, 기존 코드가 파일 1개마다 개별 삭제 명령(`item.InvokeVerb("delete")`)을 내림.
  - DSLR 카메라(MTP 프로토콜) 특성상 파일 개수만큼(예: 100개 사진 ➔ 100번) Windows 삭제 확인 팝업이 출력되는 심각한 UX 불편 발생.
  - 프론트엔드 API 호출 경로 오타 (`/api/delete` ➔ 백엔드 `/api/fetch/delete-originals`와 불일치)로 삭제 미동작.
- **해결 방안**:
  - **API 경로 수정**: `static/app.js`에서 `/api/fetch/delete-originals`로 호출 경로 수정.
  - **`FolderItems.InvokeVerbEx("delete")` 일괄 삭제 도입**:
    - 개별 파일 순회 삭제를 제거하고, 카메라 내부 폴더의 파일 묶음 컬렉션(`FolderItems`)에 대해 `InvokeVerbEx("delete")` 1회 호출.
    - 탐색기 전체 선택(Ctrl+A) 후 삭제와 동일하게 동작하도록 변경하여 **Windows 확인 팝업을 단 1회로 단축**.
  - **UI 및 종료 흐름 개선**:
    - "예(삭제)" 선택 시 **"일괄 삭제를 시작합니다..."** 모달 표출.
    - 윈도우 팝업 1회 승인 후 일괄 삭제 완료 시 **3초 후 앱 자동 종료** 처리.

---

### 3. 배포 버전 자동화 및 파이프라인 정리
- **버전 분리 및 패키징**:
  - `v1.0.0`: GitHub Release 등록용 최신 릴리즈 패키지 (`DSLR_FileTransfer_v1.0.0.zip`).
  - `v0.9.0`: 로컬 PC 업데이트 테스트용 구버전 패키지 (`DSLR_FileTransfer_v0.9.0.zip`).
- **빌드 아티팩트 위치**:
  - `dist/DSLR_FileTransfer_v1.0.0.zip`
  - `dist/DSLR_FileTransfer_v0.9.0.zip`

---

## 📂 변경된 주요 핵심 코드 요약

### `app.py` (업데이트 적용 및 프로세스 실행 위치 수정)
```python
# update.bat 실행 시 cwd를 parent_dir로 설정하여 실행 디렉토리 잠금 방지
parent_dir = os.path.dirname(exe_dir)
subprocess.Popen(
    [bat_path], 
    cwd=parent_dir,
    creationflags=subprocess.CREATE_NEW_CONSOLE,
    env=clean_env
)
```

### `camera_handler.py` (MTP 일괄 삭제 로직)
```python
# FolderItems 단위로 InvokeVerbEx("delete") 호출 -> 윈도우 팝업 1회로 감소
items = folder_obj.Items()
if has_files:
    self.delete_state['current_file'] = '카메라 폴더 파일 일괄 삭제 중...'
    items.InvokeVerbEx('delete')
```

### `static/app.js` (삭제 모달 및 경로 수정)
```javascript
document.getElementById('btn-delete-yes').addEventListener('click', () => {
    const modal = document.getElementById('modal-delete-confirm');
    modal.innerHTML = '<div class="modal-card"><p>일괄 삭제를 시작합니다...</p></div>';
    setTimeout(() => {
        modal.classList.add('hidden');
        fetch('/api/fetch/delete-originals', { method: 'POST' });
    }, 1000);
});
```

---

## 🧪 최종 테스트 및 검증 절차

1. **GitHub Release 등록**:
   - GitHub `v1.0.0` 릴리즈 자산으로 `dist/DSLR_FileTransfer_v1.0.0.zip` 업로드.
2. **로컬 업데이트 테스트**:
   - `dist/DSLR_FileTransfer_v0.9.0.zip` 압축 해제 ➔ 실행.
   - 앱 실행 시 `v1.0.0` 업데이트 감지 ➔ `업데이트` 클릭 ➔ 다운로드 및 자동 재시작 확인.
3. **일괄 삭제 테스트**:
   - 파일 가져오기 후 `원본 삭제` ➔ `예` 선택.
   - Windows 팝업 **1회만** 표시 확인 ➔ `예` 클릭 시 원본 일괄 삭제 및 앱 자동 종료 확인.
