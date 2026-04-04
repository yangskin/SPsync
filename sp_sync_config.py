# -*- coding: utf-8 -*-
import substance_painter.project
import substance_painter.export


class SPSyncConfig:
    """管理项目级配置的持久化和读取。"""

    _origin_export_path: str = ""
    _highpoly_mesh_path: str = ""

    @property
    def origin_export_path(self) -> str:
        return self._origin_export_path

    @origin_export_path.setter
    def origin_export_path(self, value: str):
        self._origin_export_path = value

    @property
    def highpoly_mesh_path(self) -> str:
        return self._highpoly_mesh_path

    @highpoly_mesh_path.setter
    def highpoly_mesh_path(self, value: str):
        self._highpoly_mesh_path = value

    def save(self, ui):
        """将 UI 状态写入 SP 项目元数据。"""
        metadata = substance_painter.project.Metadata("sp_sync")
        metadata.set("export_path", ui.file_path.text())
        metadata.set("origin_export_path", self._origin_export_path)
        metadata.set("current_preset", ui.select_preset.currentText())
        metadata.set("mesh_scale", ui.mesh_scale.value())
        metadata.set("create_material", ui.create_material.isChecked())
        metadata.set("force_front_x_axis", ui.force_front_x_axis.isChecked())
        metadata.set("highpoly_mesh_path", self._highpoly_mesh_path)

    def load(self, ui, sp_sync_ue):
        """从 SP 项目元数据读取配置，应用到 UI 和 ue_sync。返回 True 表示加载成功。"""
        from . import sp_receive

        metadata = substance_painter.project.Metadata("sp_sync")
        ui.file_path.setText(metadata.get("export_path"))
        self._origin_export_path = metadata.get("origin_export_path")
        key_list = metadata.list()

        if "highpoly_mesh_path" in key_list:
            self._highpoly_mesh_path = metadata.get("highpoly_mesh_path")
            ui.highpoly_path.setText(self._highpoly_mesh_path)
        else:
            self._highpoly_mesh_path = ""
            ui.highpoly_path.setText("")

        # UE 来源项目：通过 pending flag（新建）或 metadata（重新打开）检测
        from_ue = sp_receive._from_ue_pending or (
            "from_ue" in key_list and metadata.get("from_ue")
        )

        if "mesh_scale" in key_list:
            ui.mesh_scale.setValue(metadata.get("mesh_scale"))
            sp_sync_ue.set_mesh_scale(metadata.get("mesh_scale"))
        else:
            default_scale = 1.0 if from_ue else 100.0
            ui.mesh_scale.setValue(default_scale)
            sp_sync_ue.set_mesh_scale(default_scale)

        if "force_front_x_axis" in key_list:
            val = metadata.get("force_front_x_axis")
            ui.force_front_x_axis.setChecked(val)
            sp_sync_ue.set_force_front_x_axis(val)
        else:
            default_ffa = not from_ue
            ui.force_front_x_axis.setChecked(default_ffa)
            sp_sync_ue.set_force_front_x_axis(default_ffa)

        # UE→SP 会话：隐藏 Sync Mesh 按钮；其他情况显示
        ui.sync_mesh_button.setVisible(not sp_receive._created_from_ue_session)

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
