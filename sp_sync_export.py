# -*- coding: utf-8 -*-
import os
import json
import tempfile
import shutil
from typing import List

import substance_painter.export
import substance_painter.textureset
import substance_painter.resource
import substance_painter.event
import substance_painter.project

IsQt5 = substance_painter.application.version_info() < (10,1,0)

if IsQt5:
    from PySide2 import QtWidgets
else:
    from PySide6 import QtWidgets

from . sp_sync_ue import ue_sync
from . sp_sync_config import SPSyncConfig
from . sp_sync_ui import Ui_SPsync
from . utils import extract_mesh_name, determine_material_type
from . sp_channel_map import build_roundtrip_export_config, build_roundtrip_refresh_list


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
        self._roundtrip_mode = False
        self._roundtrip_ue_defs = None

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
        try:
            self.export_all_set()
        except (RuntimeError, ValueError):
            # ProjectOpened 触发时 texture sets 可能还没就绪，
            # 后续 ProjectEditionEntered 会再次处理
            pass

        try:
            mesh_path = substance_painter.project.last_imported_mesh_path()
            self._current_mesh_name = extract_mesh_name(mesh_path)

            self._current_udim_type = self.get_project_udim_type()
            self._sp_sync_ue.set_udim_type(self._current_udim_type)
            self.get_texture_set_material_type()
        except (RuntimeError, ValueError):
            pass

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

        # Round-Trip: 从 metadata 提取 UE 路径并显示到 UI
        self._try_populate_roundtrip_path()

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

            export_file_list = []
            for item in export_data.textures:
                for file in export_data.textures[item]:
                    export_file_list.append(file)

            # --- Round-Trip 模式：按原始 UE 路径刷新 ---
            if self._roundtrip_mode and self._roundtrip_ue_defs is not None:
                self._roundtrip_mode = False
                ue_defs = self._roundtrip_ue_defs
                self._roundtrip_ue_defs = None
                print(f'[SPsync] Round-Trip 导出完成，{len(export_file_list)} 个文件')
                for f in export_file_list:
                    print(f'[SPsync]   → {f}')
                refresh_items = build_roundtrip_refresh_list(ue_defs, export_file_list)
                print(f'[SPsync] Round-Trip 匹配 UE 资产: {len(refresh_items)} 个')
                for item in refresh_items:
                    print(f'[SPsync]   {item["ue_name"]} → {item["ue_folder"]}')
                if refresh_items:
                    print(f'[SPsync] 发送到 UE 刷新...')
                    self._sp_sync_ue.sync_ue_refresh_textures(
                        refresh_items, self._reset_all_freeze_ui)
                else:
                    print(f'[SPsync] ✗ 无匹配的 UE 资产，跳过刷新')
                    self._reset_all_freeze_ui(True)
                self._current_set_names = []
                self.on_layerstack_changed(None)
                return

            # --- 常规模式 ---
            if self._ui.file_path.text() == "":
                QtWidgets.QMessageBox.information(self._main_widget, "Warning",
                    "You need to specify the output path under the 'content/' directory in the engine!")
                return

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

    def sync_textures(self, roundtrip: bool | None = None):
        if not substance_painter.project.is_open():
            return

        # --- 尝试 Round-Trip 模式 ---
        # roundtrip=None: 自动检测 metadata；True: 强制；False: 跳过
        if roundtrip is not False:
            ue_defs = self._try_load_roundtrip_metadata()
        else:
            ue_defs = None
        if ue_defs is not None:
            mat_count = len(ue_defs.get('materials', []))
            print(f'[SPsync] Round-Trip 模式：检测到 {mat_count} 个材质定义')
            self._ui.sync_mesh_button.setEnabled(False)
            self._ui.sync_button.setEnabled(False)
            self._export_sync_button_type = True
            self._roundtrip_mode = True
            self._roundtrip_ue_defs = ue_defs

            export_config = build_roundtrip_export_config(ue_defs, self._temp_path)
            # 兜底：用实际 SP TextureSet 名称覆写 exportList，避免名称不匹配
            if self._current_set_names:
                export_config["exportList"] = [{"rootPath": n} for n in self._current_set_names]
                print(f'[SPsync] Round-Trip exportList: {self._current_set_names}')
            maps_count = len(export_config.get('exportPresets', [{}])[0].get('maps', []))
            print(f'[SPsync] Round-Trip 导出配置: {maps_count} 个 maps → {self._temp_path}')
            # DEBUG: 打印完整导出配置供诊断
            import json as _json
            for i, m in enumerate(export_config.get('exportPresets', [{}])[0].get('maps', [])):
                print(f'[SPsync] DEBUG map[{i}]: {_json.dumps(m, ensure_ascii=False)}')
            self.on_layerstack_changed(None)
            try:
                substance_painter.export.export_project_textures(export_config)
            except Exception as e:
                print(f'[SPsync] ✗ Round-Trip 导出失败: {e}')
                self._roundtrip_mode = False
                self._roundtrip_ue_defs = None
                self._export_sync_button_type = False
                self._reset_all_freeze_ui(True)
            return

        # --- 常规模式 ---
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

    def _try_populate_roundtrip_path(self):
        """项目加载时，若存在 roundtrip metadata 则将 UE 贴图文件夹显示到 UI path。"""
        ue_defs = self._try_load_roundtrip_metadata()
        if ue_defs is None:
            return
        # 从所有贴图路径中提取公共文件夹
        folders = set()
        for mat in ue_defs.get('materials', []):
            for tex in mat.get('textures', []):
                tp = tex.get('texture_path', '')
                if '/' in tp:
                    folders.add(tp.rsplit('/', 1)[0])
        if len(folders) == 1:
            ue_folder = folders.pop()
            self._ui.file_path.setText(ue_folder)
            print(f'[SPsync] Round-Trip: UE 资产路径 → {ue_folder}')
        elif folders:
            # 多个文件夹时取第一个材质的第一个贴图路径
            first = next(iter(folders))
            self._ui.file_path.setText(first)
            print(f'[SPsync] Round-Trip: UE 资产路径（多文件夹，取首个）→ {first}')

    def _try_load_roundtrip_metadata(self):
        """尝试从 SP 项目元数据加载 UE 材质定义。

        Returns:
            dict | None: 成功时返回 ue_defs，无元数据或解析失败返回 None。
        """
        try:
            metadata = substance_painter.project.Metadata("sp_sync")
            raw = metadata.get("ue_material_defs")
            if raw:
                return json.loads(raw)
        except Exception:
            pass
        return None

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
        self.sync_textures(roundtrip=False)  # sync_mesh 始终使用标准预设

        export_path = self._temp_path + "/" + self._current_mesh_name + ".fbx"
        substance_painter.export.export_mesh(export_path,
            substance_painter.export.MeshExportOption.TriangulatedMesh)
        self._sp_sync_ue.ue_import_mesh(self._ui.file_path.text(), export_path,
            self._reset_all_freeze_ui)
