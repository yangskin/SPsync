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
        button.clicked.connect(self._close)
        layout.addWidget(button)

        self.setLayout(layout)
        self.setFixedSize(425, 760)

    def _close(self):
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

    # 连接健康检测超时（秒）。命令执行超过此时长则认为连接可能不健康，
    # 下一次命令前会重新建连。设为 30s 以适应贴图导入等耗时操作。
    _timeout: float = 30.0

    # 重连前等待时间（秒），让 TCP TIME_WAIT 有时间释放
    _reconnect_delay: float = 2.0

    # 单条命令最大重试次数
    _max_retries: int = 2

    def __init__(self):
        self._command_queue = queue.Queue()
        self._thread = None
        self._lock = threading.Lock()
        self._remote_exec = remote_execution.RemoteExecution()
        self._need_reconnect = False

    def _ensure_connection(self):
        """确保有活跃的命令连接，必要时重连。"""
        if self._need_reconnect:
            self._need_reconnect = False
            try:
                self._remote_exec.stop()
            except Exception:
                pass
            time.sleep(self._reconnect_delay)

        if not self._remote_exec.has_command_connection():
            self._remote_exec.start()
            # 等待节点发现（最多 5 秒）
            for _ in range(50):
                if self._remote_exec.remote_nodes:
                    break
                time.sleep(0.1)
            if not self._remote_exec.remote_nodes:
                raise RuntimeError('No UE remote nodes discovered')
            self._remote_exec.open_command_connection(self._remote_exec.remote_nodes)

    def _worker(self):

        while True:
            try:
                self._ensure_connection()

                command = self._command_queue.get(True)
                start_time = time.time()

                try:
                    rec = self._remote_exec.run_command(command.code, True, command.model)
                    if rec['success'] == True:
                        if command.call_back_fun != None:
                            command.call_back_fun(rec['result'])

                except Exception as e:
                    print(f'[SPsync] Command failed: {e}')
                    command.error_fun()
                    # 标记需要重连，但不在此处立即重连（避免端口残留）
                    self._need_reconnect = True
                    self._command_queue.task_done()
                    continue
                
                elapsed = time.time() - start_time
                if elapsed > self._timeout:
                    print(f'[SPsync] Command took {elapsed:.1f}s (> {self._timeout}s), scheduling reconnect')
                    self._need_reconnect = True

                self._command_queue.task_done()

            except queue.Empty:
                with self._lock:
                    if self._command_queue.empty():
                        self._thread = None
                        break
            except Exception as e:
                # 连接建立失败时不要死循环，通知错误后退出
                print(f'[SPsync] Worker connection error: {e}')
                # 排空队列，通知所有等待的命令
                while not self._command_queue.empty():
                    try:
                        cmd = self._command_queue.get_nowait()
                        cmd.error_fun()
                        self._command_queue.task_done()
                    except queue.Empty:
                        break
                with self._lock:
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

    def __init__(self, ue_sync_remote_instance: ue_sync_remote):
        super().__init__()
        self._ue_sync_remote = ue_sync_remote_instance
        self.thread_loop_type = threading.Event()
        self.model_scale = 1.0
        self.force_front_x_axis = True
        # 最新帧槽位：相机循环写入，worker 读取
        self._pending_code = None          # type: str | None
        self._pending_lock = threading.Lock()
        self._pending_event = threading.Event()

    # ── 生产端：相机采样循环 ──────────────────────────

    def update(self):
        while not self.thread_loop_type.is_set():
            camera: substance_painter.display.Camera = None

            try:
                camera = substance_painter.display.Camera.get_default_camera()
            except Exception:
                pass

            if camera is not None:
                pos = camera.position
                rot = camera.rotation
                code: str = "".join(
                    ["sync_camera(", str(pos[0]), ",", str(pos[1]), ",", str(pos[2]), ",",
                     str(rot[0]), ",", str(rot[1]), ",", str(rot[2]), ",",
                     str(camera.field_of_view), ",", str(self.model_scale), ",",
                     str(self.force_front_x_axis), ")"]
                )
                # 覆盖式写入：只保留最新帧
                with self._pending_lock:
                    self._pending_code = code
                self._pending_event.set()

            time.sleep(0.033333)

    # ── 消费端：通过共享连接发送，带背压 ────────────────

    def worker(self):
        """从最新帧槽位取数据并通过共享连接发送到 UE。
        
        背压机制：每次只投递 1 条命令到队列，等它执行完再取下一帧，
        因此队列中最多只有 1 条相机命令，不会积压。
        """
        while not self.thread_loop_type.is_set():
            # 等待新帧或停止信号
            self._pending_event.wait(timeout=0.5)
            self._pending_event.clear()

            # 取出最新帧（原子交换为 None）
            with self._pending_lock:
                code = self._pending_code
                self._pending_code = None

            if code is None:
                continue

            # 背压：用 Event 等待本条命令执行完成
            cmd_done = threading.Event()
            has_error = [False]

            def on_complete(result=None):
                cmd_done.set()

            def on_error():
                has_error[0] = True
                cmd_done.set()

            self._ue_sync_remote.add_command(
                ue_sync_command(code, on_error, on_complete, remote_execution.MODE_EXEC_FILE)
            )

            # 等待命令完成（5s 超时兜底 success=False 未触发回调的情况）
            cmd_done.wait(timeout=5)

            if has_error[0]:
                self.sync_error.emit("sync_error")
                break

    def clear_pending(self):
        """清空待发帧，确保关闭时不再发送过时数据。"""
        with self._pending_lock:
            self._pending_code = None
        self._pending_event.clear()

class ue_sync(QtCore.QObject):

    sync_error = QtCore.Signal(str)
    
    def __init__(self, ui: Ui_SPsync, main_widget:QtWidgets.QWidget) -> None:
        super().__init__()
        self._ui = ui
        self._main_widget = main_widget
        self._root_path = os.path.dirname(__file__)
        self._bootstrap_injected = False
        self._bootstrap_lock = threading.Lock()
        self._udim_type = False
        self._mesh_scale = 1.0
        self._force_front_x_axis = True
        self._ue_sync_camera_thread = None
        self._ue_sync_remote = ue_sync_remote()

        self._ue_bootstrap_code = self._load_ue_scripts()
        
        self._ue_sync_camera = ue_sync_camera(self._ue_sync_remote)
        self._ue_sync_camera.sync_error.connect(self.ue_sync_camera_error)
        self._ue_sync_camera_worker_thread = None
        
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
                # 分隔注释不能包含 .py，否则 UE ExecuteFile 模式会尝试解析为文件路径
                combined += f"\n# --- {script[:-3]} ---\n"
                combined += f.read()
                combined += "\n"
        return combined

    def _ensure_bootstrap(self):
        """确保 UE 侧函数已注入。连接后一次性发送所有脚本定义。"""
        with self._bootstrap_lock:
            if not self._bootstrap_injected:
                self._ue_sync_remote.add_command(
                    ue_sync_command(
                        code=self._ue_bootstrap_code,
                        error_fun=lambda: self.sync_error.emit("sync_error"),
                        call_back_fun=self._on_bootstrap_done,
                        model=remote_execution.MODE_EXEC_FILE
                    ))

    def _on_bootstrap_done(self, result):
        with self._bootstrap_lock:
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

    def sync_ue_refresh_textures(self, refresh_items: list, callback: callable = None):
        """Round-Trip: 按 UE 原始路径刷新贴图。

        refresh_items 格式:
            [{"local_path": "...", "ue_folder": "...", "ue_name": "..."}, ...]
        """
        self._ensure_bootstrap()
        params_json = json.dumps({"textures": refresh_items})
        call = f"refresh_textures({params_json!r})"
        self._ue_sync_remote.add_command(ue_sync_command(
            call,
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
        with self._bootstrap_lock:
            self._bootstrap_injected = False
        self._ui.sync_button.setEnabled(True)
        self._ui.sync_mesh_button.setEnabled(True)
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
        # 1. 停止相机采样循环
        self._ue_sync_camera.thread_loop_type.set()
        # 2. 清空待发帧，防止 worker 继续发送过时数据
        self._ue_sync_camera.clear_pending()
        # 唤醒 worker 使其检测到停止信号并退出
        self._ue_sync_camera._pending_event.set()
        # 3. 等待两个线程退出
        if self._ue_sync_camera_thread is not None:
            self._ue_sync_camera_thread.join(timeout=2)
            self._ue_sync_camera_thread = None
        if self._ue_sync_camera_worker_thread is not None:
            self._ue_sync_camera_worker_thread.join(timeout=2)
            self._ue_sync_camera_worker_thread = None
        # 4. 通过共享连接发送 exit 命令（线程已停止，队列不会再有相机命令）
        self._ue_sync_remote.add_command(ue_sync_command(
            "exit_sync_camera()",
            lambda: self.sync_error.emit("sync_error"),
            None,
            remote_execution.MODE_EVAL_STATEMENT))
        self._ui.sync_view.setChecked(False)

    def ue_sync_camera_error(self, message:str):
        with self._bootstrap_lock:
            self._bootstrap_injected = False
        self.close_ue_sync_camera()
        self._show_help_window()

    def sync_ue_camera_init(self):
        # 如果已有运行中的相机同步，先停止
        if self._ue_sync_camera_thread is not None:
            self._ue_sync_camera.thread_loop_type.set()
            self._ue_sync_camera.clear_pending()
            self._ue_sync_camera._pending_event.set()
            self._ue_sync_camera_thread.join(timeout=2)
            self._ue_sync_camera_thread = None
        if self._ue_sync_camera_worker_thread is not None:
            self._ue_sync_camera_worker_thread.join(timeout=2)
            self._ue_sync_camera_worker_thread = None

        self._ue_sync_camera.thread_loop_type.clear()
        self._ue_sync_camera.clear_pending()

        # 通过共享连接注入 bootstrap 并初始化相机
        self._ensure_bootstrap()
        self._ue_sync_remote.add_command(ue_sync_command(
            "init_sync_camera()",
            lambda: self.sync_error.emit("sync_error")))

        # 启动采样线程（生产端）和 worker 线程（消费端）
        self._ue_sync_camera_thread = threading.Thread(target=self._ue_sync_camera.update, daemon=True)
        self._ue_sync_camera_thread.start()
        self._ue_sync_camera_worker_thread = threading.Thread(target=self._ue_sync_camera.worker, daemon=True)
        self._ue_sync_camera_worker_thread.start()
           