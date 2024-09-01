# -*- coding: utf-8 -*-
import os
import tempfile
import shutil
import threading
import time

from . import remote_execution

import substance_painter.export
import substance_painter.textureset
import substance_painter.resource
import substance_painter.event
import substance_painter.display
import substance_painter.js
import substance_painter.properties
import substance_painter.ui
import substance_painter_plugins

from PySide2 import QtWidgets
from PySide2 import QtCore
from PySide2.QtGui import QPixmap

from . sp_sync_ui import Ui_SPsync

class ImageDialog(QtWidgets.QDialog):
    def __init__(self, image_path, message:str, parent = None):
        super().__init__(parent)
        self.setWindowTitle("提示")
        
        layout = QtWidgets.QVBoxLayout()
        lable = QtWidgets.QLabel(message, self)
        layout.addWidget(lable)

        self.image_label = QtWidgets.QLabel(self)
        pixmap = QPixmap(image_path)
        self.image_label.setPixmap(pixmap.scaled(400, 667))
        layout.addWidget(self.image_label)

        button = QtWidgets.QPushButton("确认", self)
        button.clicked.connect(self._colse)
        layout.addWidget(button)

        self.setLayout(layout)
        self.setFixedSize(425, 760)

    def _colse(self):
        self.close()

class ue_sync_camera(QtCore.QObject):
    _sync_camera_code:str = ""
    sync_error = QtCore.Signal(str)
    thread_loop_type:threading.Event = threading.Event()

    def update(self):
        while not self.thread_loop_type.is_set():
            camera:substance_painter.display.Camera = None

            try: 
                camera = substance_painter.display.Camera.get_default_camera()
            except:
                pass

            if camera != None:
                code:str = self._sync_camera_code

                pos = camera.position
                code = code.replace('POS', str(pos[0]) + "," + str(pos[1]) + "," + str(pos[2]))

                rot = camera.rotation
                code = code.replace('ROTATE', str(rot[0]) + "," + str(rot[1]) + "," + str(rot[2]))

                code = code.replace('FOV', str(camera.field_of_view))

                self._execute_ue_command(code)
                time.sleep(0.033333)

    def _execute_ue_command(self, command):

        _remote_exec = remote_execution.RemoteExecution()
        _remote_exec.start()

        try :
            _remote_exec.open_command_connection(_remote_exec.remote_nodes)
            rec = _remote_exec.run_command(command, exec_mode='ExecuteFile')
            if rec['success'] == True:
                return rec['result']
            
            _remote_exec.stop()

        except :
            self.thread_loop_type.set()
            _remote_exec.stop()
            self.sync_error.emit("sync_error")

class ue_sync:

    _ui: Ui_SPsync
    _main_widget:QtWidgets.QWidget
    _root_path: str = ""
    _to_ue_code: str = ""
    _sync_camera_code:str = ""
    _ue_sync_camera:ue_sync_camera
    _ue_sync_camera_thread:threading.Thread = None
    ue_sync_camera_type:bool = False
    
    def __init__(self, ui: Ui_SPsync, main_widget:QtWidgets.QWidget) -> None:

        self._ui = ui
        self._main_widget = main_widget
        self._root_path = os.path.dirname(__file__)

        #读取导入ue贴图脚本
        with open(self._root_path + "\\import_textures_ue.py", "r") as f:
            self._to_ue_code = f.read()
        
        with open(self._root_path + "\\sync_camera_ue.py", "r") as f:
            self._sync_camera_code = f.read()

        self._ue_sync_camera = ue_sync_camera()
        self._ue_sync_camera._sync_camera_code = self._sync_camera_code

        pass

    def _show_help_window(self):
        image_dialog = ImageDialog(self._root_path + "\\doc\\ue_setting.png", "端口链接失败,检查UE中相关设置!", self._main_widget)
        image_dialog.exec_()

    def sync_ue_textures(self, target_path: str, exportFileList:list):
        """
        同步列表中的贴图到UE中
        """

        current_to_ue_code: str = self._to_ue_code
        current_to_ue_code = current_to_ue_code.replace('FOLDER_PATH', target_path)
        exportFileListStr = ''

        for file in exportFileList:
            exportFileListStr += "  '"+ file + "',\n"
        current_to_ue_code = current_to_ue_code.replace('EXPORT_TEXTURE_PATH', exportFileListStr)

        self._execute_ue_command(current_to_ue_code)

    def _execute_ue_command(self, command):

        if self.ue_sync_camera_type:
            self._ue_sync_camera.thread_loop_type.set()
            self._ue_sync_camera_thread.join()

        remote_exec = remote_execution.RemoteExecution()
        remote_exec.start()
        
        try :
            remote_exec.open_command_connection(remote_exec.remote_nodes)
            rec = remote_exec.run_command(command, exec_mode='ExecuteFile')
            if rec['success'] == True:
                return rec['result']
            remote_exec.stop()
        except :
            self._show_help_window()
            self._ui.auto_sync.setChecked(False)
            
            remote_exec.stop()

        if self.ue_sync_camera_type:
            self.sync_ue_camera_init()

    def close_ue_sync_camera(self):
        self._ue_sync_camera.thread_loop_type.set()
        self.ue_sync_camera_type = False
        self._ui.view_sync.setChecked(False)

    def ue_sync_camera_error(self, message:str):
        self.close_ue_sync_camera()
        self._show_help_window()

    def sync_ue_camera_init(self):
        if self._ue_sync_camera_thread != None:
            self._ue_sync_camera.thread_loop_type.set()
            self._ue_sync_camera_thread.join()

        self.ue_sync_camera_type = True

        self._ue_sync_camera.sync_error.connect(self.ue_sync_camera_error)
        self._ue_sync_camera.thread_loop_type.clear()

        self._ue_sync_camera_thread = threading.Thread(target=self._ue_sync_camera.update, daemon=True)
        self._ue_sync_camera_thread.start()

        pass
           