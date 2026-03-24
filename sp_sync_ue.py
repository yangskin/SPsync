# -*- coding: utf-8 -*-
import os
import json
import threading
import time
import queue
from typing import List

from . import remote_execution
from . utils import extract_mesh_name

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

    _timeout: float = 0.06

    def __init__(self):
        self._command_queue = queue.Queue()
        self._thread = None
        self._lock = threading.Lock()
        self._remote_exec = remote_execution.RemoteExecution()

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
                    self._command_queue.task_done()
                    continue
                
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
    sync_error = QtCore.Signal(str)

    def __init__(self, ue_sync_remote_instance:ue_sync_remote):
        super().__init__()
        self._ue_sync_remote = ue_sync_remote_instance
        self.thread_loop_type = threading.Event()
        self.model_scale = 1.0
        self.force_front_x_axis = True

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

    sync_error = QtCore.Signal(str)
    
    def __init__(self, ui: Ui_SPsync, main_widget:QtWidgets.QWidget) -> None:
        super().__init__()
        self._ui = ui
        self._main_widget = main_widget
        self._root_path = os.path.dirname(__file__)
        self._bootstrap_injected = False
        self._udim_type = False
        self._mesh_scale = 1.0
        self._force_front_x_axis = True
        self._ue_sync_camera_thread = None
        self._ue_sync_remote = ue_sync_remote()

        self._ue_bootstrap_code = self._load_ue_scripts()
        
        self._ue_sync_camera = ue_sync_camera(self._ue_sync_remote)
        self._ue_sync_camera.sync_error.connect(self.ue_sync_camera_error)
        
        self.sync_error.connect(self.ue_sync_textures_error)

    def _load_ue_scripts(self) -> str:
        """将所有 UE 侧脚本合并为一个 bootstrap 脚本。
        
        加载顺序有依赖关系：
        1. import_textures_ue.py  — 定义 find_asset()，被后续脚本使用
        2. material_ue.py         — 定义 create_material()，被 material_instance_ue 和 create_material 使用
        3. material_instance_ue.py — 定义 get_material_instance()，依赖 create_material()
        4. create_material_and_connect_textures.py — 依赖 find_asset(), create_material(), get_material_instance()
        5. import_mesh_ue.py      — 依赖 find_asset()
        6. sync_camera_ue.py      — 独立，无跨文件依赖
        """
        scripts = [
            "import_textures_ue.py",
            "material_ue.py",
            "material_instance_ue.py",
            "create_material_and_connect_textures.py",
            "import_mesh_ue.py",
            "sync_camera_ue.py",
        ]
        combined = ""
        for script in scripts:
            with open(os.path.join(self._root_path, script), "r", encoding="utf-8") as f:
                combined += f"\n# === {script} ===\n"
                combined += f.read()
                combined += "\n"
        return combined

    def _ensure_bootstrap(self):
        """确保 UE 侧函数已注入。连接后一次性发送所有脚本定义。"""
        if not self._bootstrap_injected:
            self._ue_sync_remote.add_command(
                ue_sync_command(
                    code=self._ue_bootstrap_code,
                    error_fun=lambda: self.sync_error.emit("sync_error"),
                    call_back_fun=self._on_bootstrap_done,
                    model=remote_execution.MODE_EXEC_FILE
                ))

    def _on_bootstrap_done(self, result):
        self._bootstrap_injected = True

    def set_udim_type(self, udim_type:bool):
        self._udim_type = udim_type

    def set_material_masked(self, material_masked:bool):
        pass

    def set_material_translucent(self, material_translucent:bool):
        pass

    def set_mesh_scale(self, scale:float):
        self._ue_sync_camera.model_scale = scale
        self._mesh_scale = scale

    def set_force_front_x_axis(self, force_front_x_axis:bool):
        self._ue_sync_camera.force_front_x_axis = force_front_x_axis
        self._force_front_x_axis = force_front_x_axis

    def _show_help_window(self):
        image_dialog = ImageDialog(self._root_path + "\\doc\\ue_setting.png", "Port link failed, check the relevant settings in UE!", self._main_widget)
        image_dialog.exec_()

    def sync_ue_textures(self, target_path: str, export_file_list:list, callback:callable = None):
        """
        同步列表中的贴图到UE中
        """
        self._ensure_bootstrap()
        params_json = json.dumps({
            "folder_path": target_path,
            "files": export_file_list,
            "udim": self._udim_type
        })
        call = f"import_textures({params_json!r})"
        self._ue_sync_remote.add_command(ue_sync_command(call, 
                                                         lambda: self.sync_error.emit("sync_error"), 
                                                         callback, 
                                                         remote_execution.MODE_EVAL_STATEMENT))
          
    def sync_ue_create_material_and_connect_textures(self, target_path, mesh_name, material_names:List[str], material_types, callback:callable):
        self._ensure_bootstrap()
        material_type_list = []
        for material_name in material_names:
            for material_type in material_types:
                if material_name == material_type[0]:
                    material_type_list.append({"name": material_name, "type": material_type[1]})

        params_json = json.dumps({
            "target_path": target_path,
            "mesh_name": mesh_name,
            "material_types": material_type_list,
            "udim": self._udim_type
        })
        call = f"create_material_and_connect_textures({params_json!r})"
        self._ue_sync_remote.add_command(ue_sync_command(call, 
                                                         lambda: self.sync_error.emit("sync_error"), 
                                                         callback, 
                                                         remote_execution.MODE_EVAL_STATEMENT))

    def ue_sync_textures_error(self):
        self._bootstrap_injected = False
        self._show_help_window() 
        self._ui.auto_sync.setChecked(False)

    def ue_import_mesh(self, target_path:str, mesh_path:str, callback:callable):
        self._ensure_bootstrap()
        params_json = json.dumps({
            "path": mesh_path,
            "target": target_path,
            "name": extract_mesh_name(mesh_path),
            "udim": self._udim_type,
            "scale": self._mesh_scale,
            "force_front_x_axis": self._force_front_x_axis
        })
        call = f"import_mesh_and_swap({params_json!r})"
        self._ue_sync_remote.add_command(ue_sync_command(call, 
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
        self._bootstrap_injected = False
        self.close_ue_sync_camera()
        self._show_help_window()

    def sync_ue_camera_init(self):
        if self._ue_sync_camera_thread != None:
            self._ue_sync_camera.thread_loop_type.set()
            self._ue_sync_camera_thread.join()

        self._ue_sync_camera.thread_loop_type.clear()

        self._ensure_bootstrap()
        self._ue_sync_remote.add_command(ue_sync_command("init_sync_camera()", lambda: self.sync_error.emit("sync_error")))
        
        self._ue_sync_camera_thread = threading.Thread(target=self._ue_sync_camera.update, daemon=True)
        self._ue_sync_camera_thread.start()
           