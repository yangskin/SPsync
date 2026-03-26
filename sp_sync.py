# -*- coding: utf-8 -*-
import webbrowser

import substance_painter.event
import substance_painter.resource
import substance_painter.ui

IsQt5 = substance_painter.application.version_info() < (10,1,0)

if IsQt5:
    from PySide2 import QtWidgets
else:
    from PySide6 import QtWidgets

from . sp_sync_ue import ue_sync
from . sp_sync_config import SPSyncConfig
from . sp_sync_export import SPSyncExport
from . utils import validate_content_path, content_path_to_game_path
from . sp_sync_ui import Ui_SPsync


class sp_sync:
    """控制器：连接 UI 事件、SP 事件与 Config / Export / UE 模块。"""

    plugin_widgets = []

    def __init__(self):
        self._config_ui()

        self._config = SPSyncConfig()
        self._sp_sync_ue = ue_sync(self._ui, self._main_widget)
        self._export = SPSyncExport(self._ui, self._main_widget, self._sp_sync_ue, self._config)

        if substance_painter.project.is_open() and (not substance_painter.resource.Shelf("starter_assets").is_crawling()):
            self._export.load_presets()

        # 绑定 SP 事件
        substance_painter.event.DISPATCHER.connect(
            substance_painter.event.ExportTexturesEnded,
            self._on_export_end)

        substance_painter.event.DISPATCHER.connect(
            substance_painter.event.ProjectOpened,
            self._project_open_event)

        substance_painter.event.DISPATCHER.connect(
            substance_painter.event.ProjectCreated,
            self._project_open_event)

        substance_painter.event.DISPATCHER.connect(
            substance_painter.event.ProjectAboutToClose,
            self._project_about_to_close_event)

        substance_painter.event.DISPATCHER.connect(
            substance_painter.event.LayerStacksModelDataChanged,
            self._export.on_layerstack_changed)

    # ── 项目生命周期 ──────────────────────────────────

    def _on_export_end(self, export_data):
        self._export.export_end_event(export_data)

    def _project_open_event(self, state):
        self._export.on_project_open()
        self._reset_all_freeze_ui(True)

        substance_painter.event.DISPATCHER.connect(
            substance_painter.event.ProjectEditionEntered,
            self._export.wait_project_edition_entered)

        substance_painter.event.DISPATCHER.connect(
            substance_painter.event.ShelfCrawlingEnded,
            self._export.wait_shelf_crawling_ended)

        if self._ui.sync_view.isChecked():
            self._sp_sync_ue.sync_ue_camera_init()

    def _project_about_to_close_event(self, state):
        from . import sp_receive
        sp_receive.reset_ue_session()
        self._ui.sync_mesh_button.setVisible(True)

        self._export.on_project_close()
        self._ui.tabWidget.setEnabled(False)
        self._ui.file_path.setText("")
        self._sp_sync_ue.close_ue_sync_camera()

    # ── UI 事件 ───────────────────────────────────────

    def _reset_all_freeze_ui(self, request):
        if request:
            self._ui.sync_button.setEnabled(True)
            self._ui.sync_mesh_button.setEnabled(True)

    def _select_file_button_click(self):
        if not substance_painter.project.is_open():
            return

        file_path: str = QtWidgets.QFileDialog.getExistingDirectory(
            self._main_widget, "打开", self._config.origin_export_path,
            QtWidgets.QFileDialog.Option.ShowDirsOnly)
        if validate_content_path(file_path):
            self._config.origin_export_path = file_path
            self._ui.file_path.setText(content_path_to_game_path(file_path))
            self._config.save(self._ui)
        else:
            QtWidgets.QMessageBox.information(self._main_widget, "Warning",
                "You need to specify the output path under the 'content/' directory in the engine!")

    def _view_sync_click(self):
        if self._ui.sync_view.isChecked():
            if substance_painter.project.is_open():
                self._sp_sync_ue.sync_ue_camera_init()
        else:
            self._sp_sync_ue.close_ue_sync_camera()

    def _help_video_click(self):
        webbrowser.open("https://www.bilibili.com/video/BV1XS11YKEJe/")

    def _force_front_x_axis_changed(self):
        self._sp_sync_ue.set_force_front_x_axis(self._ui.force_front_x_axis.isChecked())

    def _create_material_clicked(self):
        self._config.save(self._ui)

    def _config_ui(self):
        self._main_widget = QtWidgets.QWidget()
        self._main_widget.setWindowTitle("sp_sync")

        self._ui = Ui_SPsync()
        self._ui.setupUi(self._main_widget)

        self._ui.file_select.clicked.connect(self._select_file_button_click)
        self._ui.sync_button.clicked.connect(lambda: self._export.sync_textures())
        self._ui.sync_view.clicked.connect(self._view_sync_click)
        self._ui.sync_mesh_button.clicked.connect(lambda: self._export.sync_mesh())
        self._ui.help_video.clicked.connect(self._help_video_click)
        self._ui.force_front_x_axis.clicked.connect(self._force_front_x_axis_changed)
        self._ui.create_material.clicked.connect(self._create_material_clicked)

        self.plugin_widgets.append(self._main_widget)
        substance_painter.ui.add_dock_widget(self._main_widget)

        if (not substance_painter.project.is_open()) and (not substance_painter.project.is_busy()):
            self._ui.tabWidget.setEnabled(False)
