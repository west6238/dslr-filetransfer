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
    def __init__(self, camera_handler, usb_detector):
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
        self.lbl_status = QLabel("Disconnected")
        self.lbl_status.setStyleSheet("color: red; font-weight: bold;")
        self.lbl_device_info = QLabel("")
        status_layout.addWidget(self.lbl_status)
        status_layout.addWidget(self.lbl_device_info)

        # Actions Layout
        action_layout = QHBoxLayout()
        self.btn_scan = QPushButton("Scan Files")
        self.btn_fetch = QPushButton("Fetch Files")
        self.btn_delete = QPushButton("Delete Originals")
        self.btn_scan.setEnabled(False)
        self.btn_fetch.setEnabled(False)
        self.btn_delete.setEnabled(False)
        action_layout.addWidget(self.btn_scan)
        action_layout.addWidget(self.btn_fetch)
        action_layout.addWidget(self.btn_delete)
        status_layout.addLayout(action_layout)
        layout.addWidget(status_group)

        # Settings Group
        settings_group = QGroupBox("Settings")
        settings_layout = QVBoxLayout(settings_group)
        
        # Tag Name
        tag_layout = QVBoxLayout()
        tag_row = QHBoxLayout()
        tag_row.addWidget(QLabel("Tag Name:"))
        self.combo_tag = QComboBox()
        self.combo_tag.setEditable(True)
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
        # expand combo box horizontally
        self.combo_folder.setSizePolicy(self.combo_tag.sizePolicy().horizontalPolicy(), self.combo_tag.sizePolicy().verticalPolicy())
        folder_layout.addWidget(self.combo_folder, 1)
        
        self.btn_browse_folder = QPushButton("...")
        self.btn_browse_folder.setMaximumWidth(40)
        folder_layout.addWidget(self.btn_browse_folder)
        settings_layout.addLayout(folder_layout)

        # Auto-fetch
        self.chk_autorun = QCheckBox("Auto-fetch on connect")
        settings_layout.addWidget(self.chk_autorun)

        # Save Settings Button
        self.btn_save_settings = QPushButton("설정 (Save Settings)")
        settings_layout.addWidget(self.btn_save_settings)

        layout.addWidget(settings_group)

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
        
        self.btn_browse_folder.clicked.connect(self.on_browse_folder)
        self.btn_save_settings.clicked.connect(self.save_settings)

        self.btn_scan.clicked.connect(self.on_btn_scan)
        self.btn_fetch.clicked.connect(self.on_btn_fetch)
        self.btn_delete.clicked.connect(self.on_btn_delete)
        
        self.btn_register.clicked.connect(self.on_register_device)
        self.btn_remove_device.clicked.connect(self.on_remove_device)

        # Connect Worker Signals
        self.camera_handler.connection_changed.connect(self.on_connection_changed)
        self.camera_handler.scan_progress.connect(self.on_scan_progress)
        self.camera_handler.scan_complete.connect(self.on_scan_complete)
        self.camera_handler.fetch_progress.connect(self.on_progress)
        self.camera_handler.fetch_complete.connect(self.on_fetch_complete)
        self.camera_handler.delete_progress.connect(self.on_progress)
        self.camera_handler.delete_complete.connect(self.on_delete_complete)

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
        
        # Load Autfetch
        self.chk_autorun.blockSignals(True)
        self.chk_autorun.setChecked(config.get("chkbox_autorun", False))
        self.chk_autorun.blockSignals(False)

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

    def check_dirty_state(self):
        if self.is_dirty:
            QMessageBox.warning(self, "Warning", "설정값이 저장되지 않은 상태입니다. 먼저 '설정' 버튼을 눌러주세요.")
            return False
        return True

    @Slot()
    def on_btn_scan(self):
        if not self.check_dirty_state(): return
        self.camera_handler.start_scan()

    @Slot()
    def on_btn_fetch(self):
        if not self.check_dirty_state(): return
        # Since settings are saved, we fetch with current tag from config
        self.camera_handler.start_fetch(self.camera_handler.config.get("last_tag", ""))

    @Slot()
    def on_btn_delete(self):
        if not self.check_dirty_state(): return
        self.camera_handler.start_delete_originals()

    @Slot()
    def on_register_device(self):
        if not self.check_dirty_state(): return
        
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
        QMessageBox.information(self, "Success", "Device registered successfully.")

    @Slot()
    def on_remove_device(self):
        if not self.check_dirty_state(): return
        
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
        else:
            self.lbl_status.setText("Disconnected")
            self.lbl_status.setStyleSheet("color: #e74c3c; font-weight: bold;")
            self.lbl_device_info.setText("")
            self.btn_scan.setEnabled(False)
            self.btn_fetch.setEnabled(False)
            self.btn_delete.setEnabled(False)
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

    @Slot()
    def on_fetch_complete(self):
        self.lbl_progress.setText("Fetch completed successfully.")
        self.progress_bar.setValue(100)
        self.btn_delete.setEnabled(True)

    @Slot()
    def on_delete_complete(self):
        self.lbl_progress.setText("Deletion completed.")
        self.progress_bar.setValue(100)
        self.btn_delete.setEnabled(False)

    def closeEvent(self, event):
        # Prevent window close from exiting application
        event.ignore()
        # Discard dirty state
        self.is_dirty = False
        self.hide()
