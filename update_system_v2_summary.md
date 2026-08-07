# DSLR File Transfer - 업데이트 시스템 개선 (v2)

본 문서는 Windows Defender 등 백신 프로그램의 오탐(False Positive)과 임시 폴더 삭제 문제(`python312.dll` 로드 에러)를 해결하기 위해 도입된 **새로운 단일 폴더(`--onedir`) 배포 및 자동 업데이트 시스템**에 대한 작업 내역과 가이드를 정리한 문서입니다.

## 1. 문제 배경
기존에는 PyInstaller의 `--onefile` 옵션을 사용하여 단일 실행 파일(`.exe`)로 배포했습니다. 
하지만 이 방식은 다음과 같은 치명적인 문제가 있었습니다.
1. **백신 프로그램 오탐 및 차단**: 앱 실행 시 `AppData/Local/Temp/_MEIxxxxxx` 형태의 임시 폴더에 모든 라이브러리를 압축 해제하는 동작이 악성코드로 오인되어, 덮어쓰기나 실행이 차단되는 현상이 빈번하게 발생했습니다. (접근 권한 에러)
2. **DLL 로드 에러**: 업데이트 과정에서 새 버전을 실행할 때, 부모 프로세스로부터 상속받은 `_PYI_` 및 `_MEI` 환경 변수 때문에 새 프로세스가 이미 삭제된 기존 임시 폴더(`_MEIxxxx`)에서 DLL을 찾으려 시도하다가 충돌하는 현상이 있었습니다.

## 2. 해결 방안 및 작업 내역

### 2.1. `--onedir` (단일 폴더) 방식으로 빌드 구성 변경
- `DSLR_FileTransfer_onedir.spec` 파일을 새로 작성하여, `--onefile` 대신 `--onedir` 모드로 빌드하도록 변경했습니다.
- 이제 앱은 실행할 때마다 임시 폴더에 파일을 풀지 않고, 배포된 폴더 자체(`dist\DSLR_FileTransfer`)에서 라이브러리를 즉시 로드하므로 백신 프로그램의 오탐률이 크게 낮아집니다.

### 2.2. 업데이트 다운로드 포맷 변경 (.zip)
- 단일 폴더 형태이므로 실행 파일 하나만 다운로드할 수 없습니다. 따라서 **GitHub Releases에 `.exe` 대신 전체 폴더를 압축한 `.zip` 파일을 릴리즈**하도록 변경했습니다.
- **`app.js`**: `check-update` 시 `.exe` 대신 `.zip` 자산을 찾아 다운로드 URL로 넘기도록 수정했습니다.

### 2.3. 안전한 폴더 교체 및 재시작 (update.bat 수정)
- **압축 해제 (`app.py`)**: 다운로드한 `.zip` 파일을 파이썬 내장 `zipfile` 모듈을 이용해 `update_temp` 폴더에 임시로 압축 해제합니다.
- **배치 스크립트 실행 위치(cwd) 문제 해결**: `update.bat`이 삭제 대상인 현재 앱 폴더 내부에서 실행될 경우 폴더 잠금(Lock)이 걸려 삭제(`rmdir`)가 실패하는 무한 루프 버그가 있었습니다. 이를 해결하기 위해 `subprocess.Popen` 호출 시 `cwd=parent_dir`로 설정하여 부모 폴더에서 스크립트가 실행되도록 수정했습니다.
- **업데이트 흐름**: 
  1. 원본 앱 종료 대기 (`tasklist`로 프로세스 확인)
  2. 기존 앱 폴더(`DSLR_FileTransfer`) 완전 삭제 (`rmdir /s /q`)
  3. 압축이 풀린 `update_temp` 폴더를 `DSLR_FileTransfer`로 이름 변경 (덮어쓰기)
  4. 찌꺼기 임시 파일(`.zip`) 삭제 후 앱 재시작

## 3. 향후 릴리즈 배포 가이드 (관리자용)

앞으로 새로운 버전을 배포할 때는 아래 절차를 따릅니다.

1. `app.py` 내부의 **`CURRENT_VERSION` 변수를 새 버전으로 변경**합니다. (예: `v1.0.1`)
2. `pyinstaller`를 이용해 **`--onedir` 스펙으로 빌드**합니다.
   ```cmd
   .venv\Scripts\pyinstaller --noconfirm --clean DSLR_FileTransfer_onedir.spec
   ```
3. 생성된 `dist\DSLR_FileTransfer` 폴더 전체를 `.zip`으로 압축합니다. (폴더 안의 내용물을 압축해도 되고, 폴더 자체를 압축해도 업데이트 로직이 안전하게 인식합니다.)
   ```cmd
   Compress-Archive -Path dist\DSLR_FileTransfer\* -DestinationPath dist\DSLR_FileTransfer_v1.0.1.zip -Force
   ```
4. GitHub 리포지토리의 **Releases 페이지에서 새 릴리즈를 작성**하고 (태그명: `v1.0.1`), 방금 만든 **`.zip` 파일을 Assets에 첨부하여 배포**합니다.

> 일반 사용자는 이 `.zip` 파일을 최초 한 번만 다운받아 압축을 풀면 되며, 이후 버전부터는 앱 내부의 **자동 업데이트 기능을 통해 폴더가 통째로 갱신**됩니다.
