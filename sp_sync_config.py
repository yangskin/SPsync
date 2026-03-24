# -*- coding: utf-8 -*-
import substance_painter.project
import substance_painter.export


class SPSyncConfig:
    """管理项目级配置的持久化和读取。"""

    _origin_export_path: str = ""

    @property
    def origin_export_path(self) -> str:
        return self._origin_export_path

    @origin_export_path.setter
    def origin_export_path(self, value: str):
        self._origin_export_path = value

    def save(self, ui):
        """将 UI 状态写入 SP 项目元数据。"""
        metadata = substance_painter.project.Metadata("sp_sync")
        metadata.set("export_path", ui.file_path.text())
        metadata.set("origin_export_path", self._origin_export_path)
        metadata.set("current_preset", ui.select_preset.currentText())
        metadata.set("mesh_scale", ui.mesh_scale.value())
        metadata.set("create_material", ui.create_material.isChecked())

    def load(self, ui, sp_sync_ue):
        """从 SP 项目元数据读取配置，应用到 UI 和 ue_sync。返回 True 表示加载成功。"""
        metadata = substance_painter.project.Metadata("sp_sync")
        ui.file_path.setText(metadata.get("export_path"))
        self._origin_export_path = metadata.get("origin_export_path")
        key_list = metadata.list()

        if "mesh_scale" in key_list:
            ui.mesh_scale.setValue(metadata.get("mesh_scale"))
            sp_sync_ue.set_mesh_scale(metadata.get("mesh_scale"))
        else:
            ui.mesh_scale.setValue(100)
            sp_sync_ue.set_mesh_scale(100)

        if "create_material" in key_list:
            ui.create_material.setChecked(metadata.get("create_material"))

        current_preset = metadata.get("current_preset")
        current_preset_obj = None

        for i in range(ui.select_preset.count()):
            if ui.select_preset.itemText(i) == current_preset:
                ui.select_preset.setCurrentIndex(i)

            for preset in substance_painter.export.list_resource_export_presets():
                if ui.select_preset.currentText() == preset.resource_id.name:
                    current_preset_obj = preset

        return current_preset_obj
