import sys
import os
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QStyleFactory, QMessageBox
from PySide6.QtGui import QIcon, QPalette, QColor, QAction
from PySide6.QtCore import Qt

# Adjust sys.path so we can import internal modules easily
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.camera_handler_worker import CameraHandler
from core.usb_detector_worker import UsbDetectorWorker
from gui.main_window import MainWindow

def set_dark_mode(app):
    app.setStyle(QStyleFactory.create("Fusion"))
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.WindowText, Qt.white)
    dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
    dark_palette.setColor(QPalette.ToolTipText, Qt.white)
    dark_palette.setColor(QPalette.Text, Qt.white)
    dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ButtonText, Qt.white)
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(dark_palette)

APP_VERSION = "2.1.0"

def main():
    app = QApplication(sys.argv)
    
    # Check for unregister startup argument
    if "--remove-startup" in sys.argv:
        from core.registry_manager import unregister_startup
        success, message = unregister_startup()
        if success:
            QMessageBox.information(None, "시작프로그램 해제", message)
        else:
            QMessageBox.critical(None, "오류", message)
        sys.exit(0)
    
    # Enforce Dark Mode
    set_dark_mode(app)
    
    # Prevent application from closing when main window is hidden
    app.setQuitOnLastWindowClosed(False)

    # Check for startup registration
    from core.registry_manager import is_registered_in_startup, register_startup
    
    is_tray_mode = "--tray" in sys.argv
    
    is_frozen = getattr(sys, 'frozen', False)
    if is_frozen and not is_registered_in_startup():
        reply = QMessageBox.question(
            None,
            "시작프로그램 등록",
            "윈도우 로그인 시 이 앱을 시스템 트레이에 자동으로 실행하도록 등록하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply == QMessageBox.Yes:
            register_startup()
            is_tray_mode = True # Default to tray mode if just registered

    # Initialize Core Components
    camera_handler = CameraHandler()
    usb_detector = UsbDetectorWorker()

    # Link Usb Detector with Camera Handler
    usb_detector.camera_connected.connect(lambda dev_id: camera_handler.check_connection())
    usb_detector.camera_disconnected.connect(lambda dev_id: camera_handler.check_connection())
    
    # Initialize UI
    main_window = MainWindow(camera_handler, usb_detector, app_version=APP_VERSION)
    if not is_tray_mode:
        main_window.showNormal()

    # Setup System Tray Icon
    icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'icon.svg')
    if os.path.exists(icon_path):
        tray_icon = QIcon(icon_path)
    else:
        # Fallback to default Qt icon if not found
        tray_icon = app.style().standardIcon(QStyleFactory.create("Fusion").standardIcon(0))

    tray = QSystemTrayIcon(tray_icon, app)
    tray.setToolTip("DSLR File Transfer")

    menu = QMenu()
    
    action_open = QAction("Open UI", menu)
    action_open.triggered.connect(main_window.showNormal)
    menu.addAction(action_open)
    
    action_quit = QAction("Quit", menu)
    action_quit.triggered.connect(app.quit)
    menu.addAction(action_quit)

    tray.setContextMenu(menu)
    tray.show()

    # Single click on tray to open
    def on_tray_activated(reason):
        if reason == QSystemTrayIcon.Trigger:
            main_window.showNormal()
            main_window.activateWindow()

    tray.activated.connect(on_tray_activated)

    # Auto popup if autorun is triggered
    camera_handler.connection_changed.connect(
        lambda conn, name, serial: main_window.showNormal() if conn else main_window.hide()
    )

    # Notify unregistered device
    camera_handler.unregistered_device_connected.connect(
        lambda name, serial: QMessageBox.information(main_window, "기기 미등록", f"기기 '{name}' 가 등록되지 않아 자동 실행이 차단되었습니다.")
    )

    # Start the background USB detector
    usb_detector.start()
    app.aboutToQuit.connect(usb_detector.stop)
    
    # Check if a device is already connected on startup
    usb_detector.check_existing_devices()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
