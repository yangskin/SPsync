# -*- coding: utf-8 -*-
import os
import threading
import time
import queue
from typing import List

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

IsQt5 = substance_painter.application.version_info() < (10,1,0)

if IsQt5 :
    from PySide2 import QtWidgets
    from PySide2 import QtCore
    from PySide2.QtGui import QPixmap
else :
    from PySide6 import QtWidgets
    from PySide6 import QtCore
    from PySide6.QtGui import QPixmap

from . sp_sync_ui import Ui_SPsync

class ImageDialog(QtWidgets.QDialog):
    def __init__(self, image_path, message:str, parent = None):
        super().__init__(parent)
        self.setWindowTitle("Warning")
        
        layout = QtWidgets.QVBoxLayout()
        lable = QtWidgets.QLabel(message, self)
        layout.addWidget(lable)

        self.image_label = QtWidgets.QLabel(self)
        pixmap = QPixmap(image_path)
        self.image_label.setPixmap(pixmap.scaled(400, 667))
        layout.addWidget(self.image_label)

        button = QtWidgets.QPushButton("Yes", self)
        button.clicked.connect(self._colse)
        layout.addWidget(button)

        self.setLayout(layout)
        self.setFixedSize(425, 760)

    def _colse(self):
        self.close()

class ue_sync_command():
    code:str
    error_fun:callable
    call_back_fun:callable
    model:str

    def __init__(self, code:str, error_fun:callable, call_back_fun:callable = None, model:str = remote_execution.MODE_EXEC_FILE):
        self.code = code
        self.error_fun = error_fun
        self.call_back_fun = call_back_fun
        self.model = model
    
class ue_sync_remote(QtCore.QObject):

    _command_queue:queue.Queue
    _thread:threading.Thread
    _lock:threading.Lock
    _remote_exec:remote_execution.RemoteExecution = remote_execution.RemoteExecution()
    _timeout: float = 0.06

    def __init__(self):
        self._command_queue = queue.Queue()
        self._thread = None
        self._lock = threading.Lock()

    def _worker(self):

        while True:
            try:
                if not self._remote_exec.has_command_connection():
                    self._remote_exec.start()
                    self._remote_exec.open_command_connection(self._remote_exec.remote_nodes)

                command = self._command_queue.get(True)
                start_time = time.time()

                try :
                    rec = self._remote_exec.run_command(command.code, True, command.model)
                    if rec['success'] == True:
                        if command.call_back_fun != None:
                            command.call_back_fun(rec['result'])

                except Exception as e:
                    print(e)
                    command.error_fun()
                    self._remote_exec.stop()
                    pass
                
                if time.time() - start_time > self._timeout:
                    self._remote_exec.stop()
                    self._remote_exec.start()
                    self._remote_exec.open_command_connection(self._remote_exec.remote_nodes)

                self._command_queue.task_done()

            except queue.Empty:
                with self._lock:
                    if self._command_queue.empty():
                        self._thread = None
                        break

    def add_command(self, command:ue_sync_command):
        with self._lock:
            self._command_queue.put(command, True)
            if self._thread is None:
                self._thread = threading.Thread(target=self._worker, daemon=True)
                self._thread.start()

    def stop(self):
        with self._lock:
            if self._thread is not None:
                self._thread.join()
                self._thread = None


class ue_sync_camera(QtCore.QObject):
    _ue_sync_remote:ue_sync_remote
    sync_error = QtCore.Signal(str)
    thread_loop_type:threading.Event = threading.Event()
    model_scale:float = 1
    force_front_x_axis:bool = True
    
    def __init__(self, ue_sync_remote_instance:ue_sync_remote):
        super().__init__()
        self._ue_sync_remote = ue_sync_remote_instance

    def update(self):
        while not self.thread_loop_type.is_set():
            camera:substance_painter.display.Camera = None

            try: 
                camera = substance_painter.display.Camera.get_default_camera()
            except:
                pass
            
            if camera != None:
                pos = camera.position
                rot = camera.rotation
                code:str = "".join( 
                    ["sync_camera(" , str(pos[0]) , "," , str(pos[1]) , "," , str(pos[2]) , "," , str(rot[0]) , "," , str(rot[1]) , "," , str(rot[2]) , "," , str(camera.field_of_view) ,  ",", str(self.model_scale),  ",", str(self.force_front_x_axis), ")"]
                    )
                self._ue_sync_remote.add_command(ue_sync_command(code, lambda: self.sync_error.emit("sync_error")))
                
                time.sleep(0.033333)

class ue_sync(QtCore.QObject):

    _ui: Ui_SPsync
    _main_widget:QtWidgets.QWidget
    _root_path: str = ""
    _to_ue_code: str = ""
    _sync_camera_code:str = ""
    _material_ue_code:str = ""
    _material_instance_ue_code:str = ""
    _create_material_and_connect_textures_code:str = ""
    _import_mesh_ue_code:str = ""
    _ue_sync_camera:ue_sync_camera = None
    _ue_sync_camera_thread:threading.Thread = None
    _ue_sync_remote:ue_sync_remote = ue_sync_remote()
    _udim_type_str:str = "False"
    _mesh_scale_str:str = "1"
    sync_error = QtCore.Signal(str)
    
    def __init__(self, ui: Ui_SPsync, main_widget:QtWidgets.QWidget) -> None:
        super().__init__()
        self._ui = ui
        self._main_widget = main_widget
        self._root_path = os.path.dirname(__file__)

        #读取导入ue贴图脚本
        with open(self._root_path + "\\import_textures_ue.py", "r") as f:
            self._to_ue_code = f.read()
        
        with open(self._root_path + "\\sync_camera_ue.py", "r") as f:
            self._sync_camera_code = f.read()

        with open(self._root_path + "\\material_ue.py", "r") as f:
            self._material_ue_code = f.read()

        with open(self._root_path + "\\material_instance_ue.py", "r") as f:
            self._material_instance_ue_code = f.read()
        
        with open(self._root_path + "\\create_material_and_connect_textures.py", "r") as f:
            self._create_material_and_connect_textures_code = f.read()

        with open(self._root_path + "\\import_mesh_ue.py", "r") as f:
            self._import_mesh_ue_code = f.read()
        
        self._ue_sync_camera = ue_sync_camera(self._ue_sync_remote)
        
        self.sync_error.connect(self.ue_sync_textures_error)
        pass

    def set_udim_type(self, udim_type:bool):
        if udim_type:
            self._udim_type_str = "True"
        else:
            self._udim_type_str = "False"

    def set_material_masked(self, material_masked:bool):
        if material_masked:
            self._material_masked_str = "True"
        else:
            self._material_masked_str = "False"

    def set_material_translucent(self, material_translucent:bool):
        if material_translucent:
            self._material_translucent_str = "True"
        else:
            self._material_translucent_str = "False"

    def set_mesh_scale(self, scale:float):
        self._ue_sync_camera.model_scale = scale
        self._mesh_scale_str = str(scale)

    def set_force_front_x_axis(self, force_front_x_axis:bool):
        self._ue_sync_camera.force_front_x_axis = force_front_x_axis

    def _show_help_window(self):
        image_dialog = ImageDialog(self._root_path + "\\doc\\ue_setting.png", "Port link failed, check the relevant settings in UE!", self._main_widget)
        image_dialog.exec_()

    def sync_ue_textures(self, target_path: str, export_file_list:list, callback:callable = None):
        """
        同步列表中的贴图到UE中
        """

        current_to_ue_code: str = self._to_ue_code
        current_to_ue_code = current_to_ue_code.replace('FOLDER_PATH', target_path)
        exportFileListStr = ""

        for file in export_file_list:
            exportFileListStr += "  '"+ file + "',\n"
        current_to_ue_code = current_to_ue_code.replace('EXPORT_TEXTURE_PATH', exportFileListStr)

        current_to_ue_code = current_to_ue_code.replace('UDIM_TYPE', self._udim_type_str)

        self._ue_sync_remote.add_command(ue_sync_command(current_to_ue_code, lambda: self.sync_error.emit("sync_error")))

        self._ue_sync_remote.add_command(ue_sync_command("import_textures()", 
                                                         lambda: self.sync_error.emit("sync_error"), 
                                                         callback, 
                                                         remote_execution.MODE_EVAL_STATEMENT))
          
    def sync_ue_create_material_and_connect_textures(self, target_path, mesh_name, material_names:List[str], material_types, callback:callable):
        self._ue_sync_remote.add_command(ue_sync_command(self._material_ue_code, lambda: self.sync_error.emit("sync_error")))
        self._ue_sync_remote.add_command(ue_sync_command(self._material_instance_ue_code, lambda: self.sync_error.emit("sync_error")))

        current_to_ue_code:str = self._create_material_and_connect_textures_code
        current_to_ue_code = current_to_ue_code.replace('TARGET_PATH', target_path)

        material_names_str = ""
        for material_name in material_names:
            for material_type in material_types:
                if material_name == material_type[0]:
                    material_names_str += "  '"+ material_name + ":" + material_type[1] + "',\n"

        current_to_ue_code = current_to_ue_code.replace('MATERIAL_NAME_TYPES', material_names_str)
        current_to_ue_code = current_to_ue_code.replace('MESH_NAME', mesh_name)
        current_to_ue_code = current_to_ue_code.replace('UDIM_TYPE', self._udim_type_str)
 
        self._ue_sync_remote.add_command(ue_sync_command(current_to_ue_code, lambda: self.sync_error.emit("sync_error")))

        self._ue_sync_remote.add_command(ue_sync_command("create_material_and_connect_texture()", 
                                                         lambda: self.sync_error.emit("sync_error"), 
                                                         callback, 
                                                         remote_execution.MODE_EVAL_STATEMENT))

    def ue_sync_textures_error(self):
        self._show_help_window() 
        self._ui.auto_sync.setChecked(False)

    def ue_import_mesh(self, target_path:str, mesh_path:str, callback:callable):
        current_to_ue_code = "import_mesh_and_swap('PATH', 'TARGET', 'NAME', UDMI_TYPE, SCALE)"
        current_to_ue_code = current_to_ue_code.replace('PATH', mesh_path)
        current_to_ue_code = current_to_ue_code.replace('TARGET', target_path)
        current_to_ue_code = current_to_ue_code.replace('NAME', mesh_path[mesh_path.rfind("/") + 1 :mesh_path.rfind(".")])
        current_to_ue_code = current_to_ue_code.replace('UDMI_TYPE', self._udim_type_str)
        current_to_ue_code = current_to_ue_code.replace('SCALE', self._mesh_scale_str)

        self._ue_sync_remote.add_command(ue_sync_command(self._import_mesh_ue_code, lambda: self.sync_error.emit("sync_error")))
        self._ue_sync_remote.add_command(ue_sync_command(current_to_ue_code, 
                                                         lambda: self.sync_error.emit("sync_error"), 
                                                         callback, 
                                                         remote_execution.MODE_EVAL_STATEMENT))

    def close_ue_sync_camera(self):
        self._ue_sync_camera.thread_loop_type.set()
        self._ue_sync_remote.add_command(ue_sync_command("exit_sync_camera()", 
                                                         lambda: self.sync_error.emit("sync_error"), 
                                                         None, 
                                                         remote_execution.MODE_EVAL_STATEMENT))
        self._ui.sync_view.setChecked(False)

    def ue_sync_camera_error(self, message:str):
        self.close_ue_sync_camera()
        self._show_help_window()

    def sync_ue_camera_init(self):
        if self._ue_sync_camera_thread != None:
            self._ue_sync_camera.thread_loop_type.set()
            self._ue_sync_camera_thread.join()

        self._ue_sync_camera.sync_error.connect(self.ue_sync_camera_error)
        self._ue_sync_camera.thread_loop_type.clear()

        self._ue_sync_remote.add_command(ue_sync_command(self._sync_camera_code, lambda: self.sync_error.emit("sync_error")))
        self._ue_sync_remote.add_command(ue_sync_command("init_sync_camera()", lambda: self.sync_error.emit("sync_error")))
        
        self._ue_sync_camera_thread = threading.Thread(target=self._ue_sync_camera.update, daemon=True)
        self._ue_sync_camera_thread.start()
        pass
           