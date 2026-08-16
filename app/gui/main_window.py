import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QComboBox, QCheckBox, QProgressBar, QGroupBox,
    QListWidget, QListWidgetItem, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt, Slot
import datetime
from core.camera_handler_worker import get_windows_pictures_folder

class MainWindow(QMainWindow):
    def __init__(self, camera_handler, usb_detector, app_version="1.0.0"):
        super().__init__()
        self.camera_handler = camera_handler
        self.usb_detector = usb_detector

        self.is_dirty = False

        self.setWindowTitle("DSLR File Transfer Settings")
        self.setMinimumSize(450, 600)

        # Main Widget and Layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Status Group
        status_group = QGroupBox("Camera Status")
        status_layout = QVBoxLayout(status_group)
        
        # Version and Update UI
        version_layout = QHBoxLayout()
        self.lbl_version = QLabel(f"v{app_version}")
        self.lbl_version.setStyleSheet("color: gray;")
        self.btn_update = QPushButton("업데이트 가능 (Update Available)")
        self.btn_update.setStyleSheet("color: white; background-color: #27ae60; font-weight: bold; border-radius: 3px; padding: 2px 5px;")
        self.btn_update.hide()
        version_layout.addWidget(self.lbl_version)
        version_layout.addWidget(self.btn_update)
        version_layout.addStretch()
        status_layout.addLayout(version_layout)

        self.lbl_status = QLabel("Disconnected")
        self.lbl_status.setStyleSheet("color: red; font-weight: bold;")
        self.lbl_device_info = QLabel("")
        status_layout.addWidget(self.lbl_status)
        status_layout.addWidget(self.lbl_device_info)

        # Actions Layout
        action_layout = QHBoxLayout()
        self.btn_scan = QPushButton("Scan Files")
        self.btn_fetch = QPushButton("Fetch Files")
        self.btn_scan.setEnabled(False)
        self.btn_fetch.setEnabled(False)
        action_layout.addWidget(self.btn_scan)
        action_layout.addWidget(self.btn_fetch)
        status_layout.addLayout(action_layout)
        layout.addWidget(status_group)

        # Setup Updater
        from core.updater import AppUpdater
        from PySide6.QtCore import QTimer
        
        self.updater = AppUpdater(app_version)
        self.updater.update_available.connect(self.on_update_available)
        self.updater.download_progress.connect(self.on_progress)
        self.updater.error_occurred.connect(lambda msg: QMessageBox.critical(self, "Update Error", msg))
        
        self.btn_update.clicked.connect(self.on_btn_update_clicked)

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.updater.check_for_updates)
        self.update_timer.start(4 * 60 * 60 * 1000) # 4 hours
        
        # Initial check
        QTimer.singleShot(2000, self.updater.check_for_updates)

        # Settings Accordion
        self.btn_toggle_settings = QPushButton("Settings ▼")
        self.btn_toggle_settings.setCheckable(True)
        self.btn_toggle_settings.setChecked(False)
        self.btn_toggle_settings.setStyleSheet("text-align: left; padding: 5px; font-weight: bold; background-color: #444;")
        layout.addWidget(self.btn_toggle_settings)
        
        self.settings_container = QWidget()
        self.settings_container.setVisible(False)
        settings_layout = QVBoxLayout(self.settings_container)
        
        # Tag Name
        tag_layout = QVBoxLayout()
        tag_row = QHBoxLayout()
        tag_row.addWidget(QLabel("Tag Name:"))
        self.combo_tag = QComboBox()
        self.combo_tag.setEditable(True)
        self.combo_tag.setMinimumHeight(28)
        tag_row.addWidget(self.combo_tag)
        tag_layout.addLayout(tag_row)
        
        self.lbl_tag_hint = QLabel("YYYY-MM-DD_<tag> 폴더에 저장")
        self.lbl_tag_hint.setStyleSheet("color: gray; font-size: 11px;")
        tag_layout.addWidget(self.lbl_tag_hint)
        settings_layout.addLayout(tag_layout)

        # Save Folder
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("저장 폴더:"))
        self.combo_folder = QComboBox()
        self.combo_folder.setEditable(True)
        self.combo_folder.setMinimumHeight(28)
        # expand combo box horizontally
        self.combo_folder.setSizePolicy(self.combo_tag.sizePolicy().horizontalPolicy(), self.combo_tag.sizePolicy().verticalPolicy())
        folder_layout.addWidget(self.combo_folder, 1)
        
        self.btn_browse_folder = QPushButton("...")
        self.btn_browse_folder.setMinimumHeight(28)
        self.btn_browse_folder.setMaximumWidth(40)
        folder_layout.addWidget(self.btn_browse_folder)
        settings_layout.addLayout(folder_layout)

        # Auto-fetch
        self.chk_autorun = QCheckBox("Auto-fetch on connect")
        settings_layout.addWidget(self.chk_autorun)

        # Delete after fetch
        self.chk_delete_after = QCheckBox("가져온 다음 항상 장치에서 지우기")
        settings_layout.addWidget(self.chk_delete_after)

        # Save Settings Button
        self.btn_save_settings = QPushButton("설정 (Save Settings)")
        self.btn_save_settings.setMinimumHeight(28)
        settings_layout.addWidget(self.btn_save_settings)

        layout.addWidget(self.settings_container)

        # Progress Group
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        self.lbl_progress = QLabel("Idle")
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.lbl_progress)
        progress_layout.addWidget(self.progress_bar)
        layout.addWidget(progress_group)

        # Devices Group
        devices_group = QGroupBox("Registered Devices")
        devices_layout = QVBoxLayout(devices_group)
        self.list_devices = QListWidget()
        devices_layout.addWidget(self.list_devices)
        
        dev_action_layout = QHBoxLayout()
        self.btn_register = QPushButton("Register Current Device")
        self.btn_remove_device = QPushButton("Remove Selected")
        self.btn_register.setEnabled(False)
        dev_action_layout.addWidget(self.btn_register)
        dev_action_layout.addWidget(self.btn_remove_device)
        devices_layout.addLayout(dev_action_layout)
        layout.addWidget(devices_group)

        # Connections
        self.combo_tag.editTextChanged.connect(self.mark_dirty)
        self.combo_tag.currentIndexChanged.connect(self.mark_dirty)
        self.combo_folder.editTextChanged.connect(self.mark_dirty)
        self.combo_folder.currentIndexChanged.connect(self.mark_dirty)
        self.chk_autorun.stateChanged.connect(self.mark_dirty)
        self.chk_delete_after.stateChanged.connect(self.mark_dirty)
        
        self.btn_toggle_settings.clicked.connect(self.on_toggle_settings)
        
        self.btn_browse_folder.clicked.connect(self.on_browse_folder)
        self.btn_save_settings.clicked.connect(self.save_settings)

        self.btn_scan.clicked.connect(self.on_btn_scan)
        self.btn_fetch.clicked.connect(self.on_btn_fetch)
        
        self.btn_register.clicked.connect(self.on_register_device)
        self.btn_remove_device.clicked.connect(self.on_remove_device)

        # Connect Worker Signals
        self.camera_handler.connection_changed.connect(self.on_connection_changed)
        self.camera_handler.scan_progress.connect(self.on_scan_progress)
        self.camera_handler.scan_complete.connect(self.on_scan_complete)
        self.camera_handler.fetch_progress.connect(self.on_progress)
        self.camera_handler.fetch_complete.connect(self.on_fetch_complete)
        self.camera_handler.delete_progress.connect(self.on_progress)
        self.camera_handler.scan_failed.connect(self.on_scan_failed)
        self.camera_handler.fetch_failed.connect(self.on_fetch_failed)
        self.camera_handler.auto_fetch_triggered.connect(self.on_btn_fetch)
        
        self.load_settings()
        
    @Slot(bool)
    def on_toggle_settings(self, checked):
        self.settings_container.setVisible(checked)
        self.btn_toggle_settings.setText("Settings ▲" if checked else "Settings ▼")

    @Slot(str, str)
    def on_update_available(self, new_version, download_url):
        self.btn_update.setText(f"업데이트 가능 (v{new_version})")
        self.btn_update.show()
        self.updater.new_version = new_version
        self.updater.download_url = download_url

    @Slot()
    def on_btn_update_clicked(self):
        reply = QMessageBox.question(self, "Update", "최신 버전으로 업데이트 하시겠습니까? 업데이트 중 앱이 재시작됩니다.", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.lbl_progress.setText("Downloading update...")
            self.progress_bar.setValue(0)
            self.updater.start_update(self.updater.new_version, self.updater.download_url)

    @Slot()
    def mark_dirty(self):
        self.is_dirty = True

    def showEvent(self, event):
        # Load settings cleanly when window is shown
        self.load_settings()
        self.is_dirty = False
        super().showEvent(event)

    def load_settings(self):
        config = self.camera_handler.config
        
        serial = self.camera_handler.device_serial
        registered = config.get("registered_cameras", [])
        is_registered = any(cam.get("serial") == serial for cam in registered) if serial else False
        
        # Load Autfetch and Delete After
        self.chk_autorun.blockSignals(True)
        self.chk_autorun.setChecked(is_registered and config.get("chkbox_autorun", False))
        self.chk_autorun.blockSignals(False)

        self.chk_delete_after.blockSignals(True)
        self.chk_delete_after.setChecked(is_registered and config.get("chkbox_delete_after", False))
        self.chk_delete_after.blockSignals(False)

        # Load Tag Name
        self.combo_tag.blockSignals(True)
        self.combo_tag.clear()
        tags = config.get("taglist", ["제주도여행", "가족모임", "테스트"])
        self.combo_tag.addItems(tags)
        last_tag = config.get("last_tag", "")
        if last_tag and last_tag in tags:
            self.combo_tag.setCurrentText(last_tag)
        else:
            self.combo_tag.setCurrentText(last_tag)
        self.combo_tag.blockSignals(False)

        # Load Save Folder
        self.combo_folder.blockSignals(True)
        self.combo_folder.clear()
        default_folder = get_windows_pictures_folder()
        save_folder_history = config.get("save_folder_history", [])
        if not save_folder_history:
            save_folder_history = [default_folder]
        
        self.combo_folder.addItems(save_folder_history)
        current_save_dir = config.get("save_dir", default_folder)
        self.combo_folder.setCurrentText(current_save_dir)
        self.combo_folder.blockSignals(False)

        self.refresh_device_list()

    @Slot()
    def save_settings(self):
        config = self.camera_handler.config
        
        # Tag update
        current_tag = self.combo_tag.currentText().strip()
        tags = config.get("taglist", ["제주도여행", "가족모임", "테스트"])
        if current_tag and current_tag not in tags:
            tags.insert(0, current_tag)
        config["taglist"] = tags
        config["last_tag"] = current_tag

        # Folder update
        current_folder = self.combo_folder.currentText().strip()
        if not current_folder:
            current_folder = get_windows_pictures_folder()
        
        folders = config.get("save_folder_history", [])
        if not folders:
            folders = [get_windows_pictures_folder()]
        if current_folder not in folders:
            folders.insert(0, current_folder)
            
        config["save_folder_history"] = folders
        config["save_dir"] = current_folder

        # Autorun update
        config["chkbox_autorun"] = self.chk_autorun.isChecked()
        config["chkbox_delete_after"] = self.chk_delete_after.isChecked()

        self.camera_handler.update_config(config)
        self.is_dirty = False
        
        # reload to update combos cleanly
        self.load_settings()
        
        QMessageBox.information(self, "Success", "설정값이 업데이트되었습니다.")

    @Slot()
    def on_browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Save Folder", self.combo_folder.currentText())
        if folder:
            # normalize path
            folder = os.path.abspath(os.path.normpath(folder))
            self.combo_folder.setCurrentText(folder)

    @Slot()
    def on_btn_scan(self):
        self.camera_handler.start_scan()

    @Slot()
    def on_btn_fetch(self):
        tag_name = self.combo_tag.currentText().strip()
        save_dir = self.combo_folder.currentText().strip()
        delete_after = self.chk_delete_after.isChecked()
        self.camera_handler.start_fetch(tag_name, save_dir, delete_after)

    @Slot()
    def on_register_device(self):
        
        if not self.camera_handler.is_connected:
            return
            
        serial = self.camera_handler.device_serial
        name = self.camera_handler.device_name
        if not serial:
            QMessageBox.warning(self, "Error", "Cannot identify device serial.")
            return

        config = self.camera_handler.config
        registered = config.get("registered_cameras", [])
        
        # Check if already exists
        for cam in registered:
            if cam.get("serial") == serial:
                QMessageBox.information(self, "Info", "Device is already registered.")
                return

        registered.append({"name": name, "serial": serial, "date_added": datetime.datetime.now().isoformat()})
        self.camera_handler.update_config({"registered_cameras": registered})
        self.refresh_device_list()
        # Force UI update since it's now registered
        self.on_connection_changed(True, name, serial)
        QMessageBox.information(self, "Success", "Device registered successfully.")

    @Slot()
    def on_remove_device(self):
        
        current_item = self.list_devices.currentItem()
        if not current_item:
            return
        
        serial = current_item.data(Qt.UserRole)
        config = self.camera_handler.config
        registered = config.get("registered_cameras", [])
        
        registered = [cam for cam in registered if cam.get("serial") != serial]
        self.camera_handler.update_config({"registered_cameras": registered})
        self.refresh_device_list()

    def refresh_device_list(self):
        self.list_devices.clear()
        registered = self.camera_handler.config.get("registered_cameras", [])
        for dev in registered:
            item = QListWidgetItem(f"{dev.get('name')} ({dev.get('serial')})")
            item.setData(Qt.UserRole, dev.get('serial'))
            self.list_devices.addItem(item)

    @Slot(bool, str, str)
    def on_connection_changed(self, connected, name, serial):
        if connected:
            self.lbl_status.setText("Connected")
            self.lbl_status.setStyleSheet("color: #2ecc71; font-weight: bold;")
            self.lbl_device_info.setText(f"{name} ({serial})")
            self.btn_scan.setEnabled(True)
            self.btn_register.setEnabled(True)
            self.lbl_progress.setText("Device connected.")
            
            config = self.camera_handler.config
            registered = config.get("registered_cameras", [])
            is_registered = any(cam.get("serial") == serial for cam in registered)
            
            if is_registered:
                self.chk_autorun.setVisible(True)
                self.chk_autorun.setEnabled(True)
                self.chk_delete_after.setVisible(True)
                self.chk_delete_after.setEnabled(True)
                self.btn_save_settings.setVisible(True)
                self.btn_save_settings.setEnabled(True)
            else:
                self.chk_autorun.setVisible(False)
                self.chk_autorun.setEnabled(False)
                self.chk_autorun.setChecked(False)
                
                self.chk_delete_after.setVisible(False)
                self.chk_delete_after.setEnabled(False)
                self.chk_delete_after.setChecked(False)
                
                self.btn_save_settings.setVisible(False)
                self.btn_save_settings.setEnabled(False)
        else:
            self.lbl_status.setText("Disconnected")
            self.lbl_status.setStyleSheet("color: #e74c3c; font-weight: bold;")
            self.lbl_device_info.setText("")
            self.btn_scan.setEnabled(False)
            self.btn_fetch.setEnabled(False)
            self.btn_register.setEnabled(False)
            self.lbl_progress.setText("Idle")
            self.progress_bar.setValue(0)

    @Slot(int, str)
    def on_scan_progress(self, count, filename):
        self.lbl_progress.setText(f"Scanning... Found {count} files.")
        
    @Slot(list)
    def on_scan_complete(self, files):
        self.lbl_progress.setText(f"Scan complete. {len(files)} media files ready.")
        self.btn_fetch.setEnabled(len(files) > 0)
        self.progress_bar.setValue(0)

    @Slot(int, int, str)
    def on_progress(self, current, total, filename):
        self.lbl_progress.setText(f"Processing: {filename}")
        if total > 0:
            self.progress_bar.setValue(int((current / total) * 100))

    @Slot(int, str, bool)
    def on_fetch_complete(self, copied_count, dest_path, is_deleted):
        self.progress_bar.setValue(100)
        
        if is_deleted:
            msg = f"Camera 저장 파일 {copied_count}개의 파일을 PC {dest_path}에 저장 완료되고 Camera 저장 파일은 삭제되었습니다."
        else:
            msg = f"Camera 저장 파일 {copied_count}개의 파일을 PC {dest_path}에 저장 완료되고 Camera 저장 파일은 삭제되지 않음."
            
        QMessageBox.information(self, "가져오기 완료", msg)
        
        # 팝업 닫히면 폴더 띄우고 UI 숨기기
        try:
            os.startfile(dest_path)
        except Exception:
            pass
        self.hide()

    @Slot(str)
    def on_scan_failed(self, error_msg):
        self.lbl_status.setText(f"스캔 실패: {error_msg}")
        self.btn_scan.setEnabled(True)
        self.progress_bar.setValue(0)
        QMessageBox.warning(self, "스캔 오류", f"기기 스캔에 실패했습니다.\n오류: {error_msg}")

    @Slot(str)
    def on_fetch_failed(self, error_msg):
        self.lbl_status.setText(f"가져오기 실패: {error_msg}")
        self.btn_scan.setEnabled(True)
        self.btn_fetch.setEnabled(len(self.camera_handler.found_files) > 0)
        self.progress_bar.setValue(0)
        QMessageBox.warning(self, "가져오기 오류", f"파일 가져오기에 실패했습니다.\n오류: {error_msg}")

    def closeEvent(self, event):
        # Prevent window close from exiting application
        event.ignore()
        # Discard dirty state
        self.is_dirty = False
        self.hide()
