import os
import shutil
import subprocess
import sys

def main():
    print("=" * 50)
    print("1. PyInstaller 빌드 시작")
    print("=" * 50)
    
    # Run PyInstaller
    # --noconfirm: overwrite existing
    # --onedir: folder mode (prevents 'Failed to create child process' and temp extraction issues)
    # --windowed: no console window
    # --add-data: include templates and static
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name", "dslr_autoplay",
        "--add-data", "templates;templates",
        "--add-data", "static;static",
        "app.py"
    ]
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"빌드 실패: {e}")
        sys.exit(1)
        
    print("\n" + "=" * 50)
    print("2. 배포 폴더로 복사")
    print("=" * 50)
    
    deploy_dir = r"C:\work\dslr_autoplay"
    if os.path.exists(deploy_dir):
        print(f"[{deploy_dir}] 기존 폴더 삭제 중...")
        shutil.rmtree(deploy_dir, ignore_errors=True)
        
    src_dir = os.path.join("dist", "dslr_autoplay")
    
    if os.path.exists(src_dir):
        try:
            print(f"{src_dir} -> {deploy_dir} 폴더 전체 복사 중...")
            shutil.copytree(src_dir, deploy_dir, dirs_exist_ok=True)
            print("복사 완료!")
            
            dst_exe = os.path.join(deploy_dir, "dslr_autoplay.exe")
            print("\n배포가 완료되었습니다.")
            print(f"이제 대상 PC에서 '{dst_exe}' 파일을 실행하여 자동 실행을 등록하세요.")
        except Exception as e:
            print(f"폴더 복사 실패: {e}")
    else:
        print(f"에러: {src_dir} 폴더를 찾을 수 없습니다.")

if __name__ == "__main__":
    main()
