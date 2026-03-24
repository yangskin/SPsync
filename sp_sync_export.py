# -*- coding: utf-8 -*-
import os
import tempfile
import shutil
from typing import List

import substance_painter.export
import substance_painter.textureset
import substance_painter.resource
import substance_painter.event

IsQt5 = substance_painter.application.version_info() < (10,1,0)

if IsQt5:
    from PySide2 import QtWidgets
else:
    from PySide6 import QtWidgets

from . sp_sync_ue import ue_sync
from . sp_sync_config import SPSyncConfig
from . sp_sync_ui import Ui_SPsync
from . utils import extract_mesh_name, determine_material_type


class SPSyncExport:
    """管理导出流程、预设和纹理集追踪。"""

    def __init__(self, ui: Ui_SPsync, main_widget: QtWidgets.QWidget,
                 sp_sync_ue: ue_sync, config: SPSyncConfig):
        self._ui = ui
        self._main_widget = main_widget
        self._sp_sync_ue = sp_sync_ue
        self._config = config
        self._root_path = os.path.dirname(__file__)
        self._current_preset = None
        self._export_sync_button_type = False
        self._current_mesh_name = ""
        self._current_udim_type = False
        self._current_set_names = []
        self._load_type = False

        self._temp_path = tempfile.gettempdir().replace('\\', '/') + "/sp_sync_temp"
        self.clean_temp_folder()
        os.makedirs(self._temp_path)

    @property
    def current_preset(self):
        return self._current_preset

    @current_preset.setter
    def current_preset(self, value):
        self._current_preset = value

    @property
    def current_mesh_name(self) -> str:
        return self._current_mesh_name

    @property
    def load_type(self) -> bool:
        return self._load_type

    @load_type.setter
    def load_type(self, value: bool):
        self._load_type = value

    def clean_temp_folder(self):
        if os.path.exists(self._temp_path):
            shutil.rmtree(self._temp_path)

    def export_all_set(self):
        self._current_set_names = []
        for texture_set in substance_painter.textureset.all_texture_sets():
            self._current_set_names.append(texture_set.name())

    def get_project_udim_type(self) -> bool:
        for texture_set in substance_painter.textureset.all_texture_sets():
            return texture_set.has_uv_tiles()
        return False

    def get_texture_set_material_type(self):
        texture_set_list = substance_painter.textureset.all_texture_sets()
        request = []
        for texture_set in texture_set_list:
            channel_names = []
            for stack in texture_set.all_stacks():
                for channel in stack.all_channels().keys():
                    channel_names.append(channel.name)
            current_material_type = determine_material_type(channel_names)
            request.append([texture_set.name(), current_material_type])
        return request

    def on_layerstack_changed(self, event):
        stack = substance_painter.textureset.get_active_stack()
        current_set_name = stack.material().name()
        if current_set_name not in self._current_set_names:
            self._current_set_names.append(current_set_name)

    def on_project_open(self):
        self._current_preset = None
        self._sp_sync_ue.set_material_masked(False)
        self._sp_sync_ue.set_material_translucent(False)
        self.export_all_set()

        mesh_path = substance_painter.project.last_imported_mesh_path()
        self._current_mesh_name = extract_mesh_name(mesh_path)

        self._current_udim_type = self.get_project_udim_type()
        self._sp_sync_ue.set_udim_type(self._current_udim_type)
        self.get_texture_set_material_type()

    def on_project_close(self):
        self._load_type = False
        self._ui.select_preset.currentIndexChanged.disconnect(self.select_preset_changed)
        self._ui.mesh_scale.valueChanged.disconnect(self._mesh_scale_changed)
        self._ui.select_preset.clear()
        self.clean_temp_folder()

    def load_presets(self):
        if self._load_type:
            return

        if not substance_painter.project.is_open():
            return

        self._ui.select_preset.clear()

        if len(substance_painter.export.list_resource_export_presets()) < 10:
            return

        substance_painter.resource.import_session_resource(
            self._root_path + "/assets/export-presets/SPSYNCDefault.spexp",
            substance_painter.resource.Usage.EXPORT)

        resource_presets_list = substance_painter.export.list_resource_export_presets()
        resource_presets_list.sort(key=lambda x: x.resource_id.name != "SPSYNCDefault")

        for preset in resource_presets_list:
            self._ui.select_preset.addItem(preset.resource_id.name)

        self._current_preset = self._config.load(self._ui, self._sp_sync_ue)
        self._ui.select_preset.currentIndexChanged.connect(self.select_preset_changed)
        self._ui.mesh_scale.valueChanged.connect(self._mesh_scale_changed)
        self._ui.tabWidget.setEnabled(True)
        self._load_type = True

    def wait_shelf_crawling_ended(self, state):
        if state.shelf_name == "starter_assets":
            self.load_presets()

    def wait_project_edition_entered(self, state):
        substance_painter.event.DISPATCHER.disconnect(
            substance_painter.event.ProjectEditionEntered,
            self.wait_project_edition_entered
        )
        self.load_presets()

    def select_preset_changed(self, index: int):
        if not substance_painter.project.is_open():
            return

        if index != -1:
            self._ui.select_preset.setCurrentIndex(index)
            resource_presets_list = substance_painter.export.list_resource_export_presets()
            for preset in resource_presets_list:
                if self._ui.select_preset.currentText() == preset.resource_id.name:
                    self._current_preset = preset
                    self._config.save(self._ui)

    def _reset_all_freeze_ui(self, request):
        if request:
            self._ui.sync_button.setEnabled(True)
            self._ui.sync_mesh_button.setEnabled(True)

    def _mesh_scale_changed(self):
        self._sp_sync_ue.set_mesh_scale(self._ui.mesh_scale.value())
        self._config.save(self._ui)

    def export_end_event(self, export_data: substance_painter.event.ExportTexturesEnded):
        if self._ui.auto_sync.isChecked() or self._export_sync_button_type:
            self._export_sync_button_type = False

            if self._ui.file_path.text() == "":
                QtWidgets.QMessageBox.information(self._main_widget, "Warning",
                    "You need to specify the output path under the 'content/' directory in the engine!")
                return

            export_file_list = []
            for item in export_data.textures:
                for file in export_data.textures[item]:
                    export_file_list.append(file)

            if self._ui.create_material.isChecked():
                if self._current_preset.resource_id.name == "SPSYNCDefault":
                    self._sp_sync_ue.sync_ue_textures(self._ui.file_path.text(), export_file_list)
                    self._sp_sync_ue.sync_ue_create_material_and_connect_textures(
                        self._ui.file_path.text(), self._current_mesh_name,
                        self._current_set_names, self.get_texture_set_material_type(),
                        self._reset_all_freeze_ui)
                else:
                    self._sp_sync_ue.sync_ue_textures(self._ui.file_path.text(), export_file_list,
                        self._reset_all_freeze_ui)
                    self._ui.create_material.setChecked(False)
                    QtWidgets.QMessageBox.information(self._main_widget, "Warning",
                        "The texture output configuration must be 'SPSYNCDefault' to generate materials!")
            else:
                self._sp_sync_ue.sync_ue_textures(self._ui.file_path.text(), export_file_list,
                    self._reset_all_freeze_ui)

            self._current_set_names = []
            self.on_layerstack_changed(None)

    def sync_textures(self):
        if not substance_painter.project.is_open():
            return

        if self._current_preset is None:
            QtWidgets.QMessageBox.information(self._main_widget, "Warning",
                "Need to specify the texture output configuration!")
            return

        self._ui.sync_mesh_button.setEnabled(False)
        self._ui.sync_button.setEnabled(False)

        self._export_sync_button_type = True

        export_list = []
        for name in self._current_set_names:
            export_list.append({"rootPath": name})

        self.on_layerstack_changed(None)

        export_config = self._build_export_config(export_list)
        substance_painter.export.export_project_textures(export_config)

    def _build_export_config(self, export_list: list) -> dict:
        newPreset = {
            "name": self._current_preset.resource_id.name,
            "maps": self._current_preset.list_output_maps()
        }

        return {
            "exportShaderParams": False,
            "exportPath": self._temp_path,
            "defaultExportPreset": newPreset["name"],
            "exportPresets": [newPreset],
            "exportList": export_list,
            "exportParameters": [
                {
                    "parameters": {
                        "dithering": True,
                        "paddingAlgorithm": "infinite"
                    }
                }]
        }

    def sync_mesh(self):
        if not substance_painter.project.is_open():
            return

        if self._current_preset is None:
            QtWidgets.QMessageBox.information(self._main_widget, "Warning",
                "Need to specify the texture output configuration!")
            return

        self.export_all_set()
        self.sync_textures()

        export_path = self._temp_path + "/" + self._current_mesh_name + ".fbx"
        substance_painter.export.export_mesh(export_path,
            substance_painter.export.MeshExportOption.TriangulatedMesh)
        self._sp_sync_ue.ue_import_mesh(self._ui.file_path.text(), export_path,
            self._reset_all_freeze_ui)
