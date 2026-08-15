import pythoncom
import win32com.client
from PySide6.QtCore import QThread, Signal
import time

class UsbDetectorWorker(QThread):
    camera_connected = Signal(str)  # Emits the DeviceID
    camera_disconnected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_running = True

    def run(self):
        pythoncom.CoInitialize()
        wmi = win32com.client.GetObject("winmgmts:")
        
        watcher = wmi.ExecNotificationQuery(
            "SELECT * FROM __InstanceOperationEvent WITHIN 2 "
            "WHERE TargetInstance ISA 'Win32_PnPEntity' "
            "AND TargetInstance.PNPClass = 'WPD'"
        )
        
        while self._is_running:
            try:
                # 2000ms timeout
                event = watcher.NextEvent(2000)
                event_type = event.Path_.Class
                instance = event.Properties_("TargetInstance").Value
                
                device_id = instance.DeviceID
                if getattr(instance, 'PNPClass', '') == 'WPD' and device_id:
                    if event_type == '__InstanceCreationEvent':
                        self.camera_connected.emit(device_id)
                    elif event_type == '__InstanceDeletionEvent':
                        self.camera_disconnected.emit(device_id)
            except Exception:
                time.sleep(0.5)

        pythoncom.CoUninitialize()

    def stop(self):
        self._is_running = False
        self.wait()

    def check_existing_devices(self):
        """Check for devices that are already connected before the watcher starts."""
        pythoncom.CoInitialize()
        try:
            wmi = win32com.client.GetObject("winmgmts:")
            pnp_devices = wmi.InstancesOf("Win32_PnPEntity")
            for instance in pnp_devices:
                if getattr(instance, 'PNPClass', '') == 'WPD' and instance.DeviceID:
                    self.camera_connected.emit(instance.DeviceID)
        except Exception as e:
            print(f"Error checking existing devices: {e}")
        finally:
            pythoncom.CoUninitialize()
