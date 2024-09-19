# -*- coding: utf-8 -*-
import os
import tempfile
import shutil
from typing import List

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
from PySide2 import QtGui
from PySide2 import QtCore
from PySide2.QtGui import QPixmap

from . sp_sync_ue import ue_sync

# 载入UI描述
from . sp_sync_ui import Ui_SPsync

class sp_sync:
    """读取配置文件,在UI中生成对应按钮。点击按钮后,对Shader传入对应参数。"""

    plugin_widgets = []
    _main_widget:QtWidgets.QWidget
    _ui: Ui_SPsync
    _root_path: str = ""
    _temp_path: str = ""
    _origin_export_path: str = ""
    _current_preset:substance_painter.export.ResourceExportPreset = None
    _export_sync_button_type:bool = False
    _current_mesh_name:str = ""

    _sp_sync_ue:ue_sync
   
    def __init__(self):
        """
        初始化 读取配置文件 并配置UI
        """
        # 获取当前插件所在路径 以次作为插件根目录
        self._root_path = os.path.dirname(__file__)

        #获取当前系统临时文件路径
        self._temp_path = tempfile.gettempdir()
        self._temp_path = self._temp_path.replace('\\', '/')
        self._temp_path = self._temp_path + "/sp_sync_temp"
        #清理临时文件夹
        self._clean_temp_folder()
        os.makedirs(self._temp_path)

        self._config_ui()

        self._sp_sync_ue = ue_sync(self._ui, self._main_widget)
        
        #绑定贴图导出事件
        substance_painter.event.DISPATCHER.connect(
            substance_painter.event.ExportTexturesEnded,
        self._export_end_event)

        #绑定项目开启事件
        substance_painter.event.DISPATCHER.connect(
            substance_painter.event.ProjectOpened,
        self._project_open_event
        )

        substance_painter.event.DISPATCHER.connect(
            substance_painter.event.ProjectAboutToClose,
        self._project_about_to_close_event
        )

    def _clean_temp_folder(self):
        """
        清理临时文件夹
        """
        if os.path.exists(self._temp_path):
            shutil.rmtree(self._temp_path)

    def _project_open_event(self, state):
        """
        项目打开
        """
        
        self._current_preset = None

        mesh_path = substance_painter.project.last_imported_mesh_path()
        self._current_mesh_name = mesh_path[mesh_path.rfind("/") + 1 : mesh_path.rfind(".")]

        substance_painter.event.DISPATCHER.connect(
            substance_painter.event.ProjectEditionEntered,
        self._wait_ProjectEditionEntered_loade_export_presets
        )

        substance_painter.event.DISPATCHER.connect(
            substance_painter.event.ShelfCrawlingEnded,
        self._wait_ShelfCrawlingEnded_loade_export_presets
        )

        if self._ui.sync_view.isChecked():
            self._sp_sync_ue.sync_ue_camera_init()
        
    def _project_about_to_close_event(self, state):

        self._ui.file_path.setText("")
        self._ui.select_preset.clear()
        self._clean_temp_folder()

        self._sp_sync_ue.close_ue_sync_camera()

    def _reset_all_freeze_ui(self, request):
        if request:
            self._ui.sync_button.setEnabled(True)
            self._ui.sync_mesh_button.setEnabled(True)
    
    def _export_end_event(self, export_data:substance_painter.event.ExportTexturesEnded):

        if self._ui.auto_sync.isChecked() or self._export_sync_button_type:
            self._export_sync_button_type = False

            if self._ui.file_path.text() == "":
                QtWidgets.QMessageBox.information(self._main_widget, "提示", "需要指定引擎中的输出路径!")
                return
            
            export_file_list = []
            for item in export_data.textures:
                for file in export_data.textures[item]:
                    export_file_list.append(file)

            if self._ui.create_material.isChecked():
                self._sp_sync_ue.sync_ue_textures(self._ui.file_path.text(), export_file_list)
                self._sp_sync_ue.sync_ue_create_material_and_connect_textures(self._ui.file_path.text(), self._current_mesh_name, self._get_texture_sets(), self._reset_all_freeze_ui)
            else:
                self._sp_sync_ue.sync_ue_textures(self._ui.file_path.text(), export_file_list, self._reset_all_freeze_ui)

    def _select_file_button_click(self):
        
        if not substance_painter.project.is_open():
            return
        
        #打开文件选择对话框
        file_path: str = QtWidgets.QFileDialog.getExistingDirectory(self._main_widget, "打开", self._origin_export_path, QtWidgets.QFileDialog.Option.ShowDirsOnly)
        if "Content" in file_path:
            self._origin_export_path = file_path
            self._ui.file_path.setText( "/" + file_path[file_path.find("Content"):].replace("Content", "Game") )
            self._save_data()
        else:
            QtWidgets.QMessageBox.information(self._main_widget, "提示", "需要选择Content文件夹下的目录!")

    def _wait_ShelfCrawlingEnded_loade_export_presets(self, state):
        self._loade_export_presets()

    def _wait_ProjectEditionEntered_loade_export_presets(self, state):

        substance_painter.event.DISPATCHER.disconnect(
        substance_painter.event.ProjectEditionEntered,
        self._wait_ProjectEditionEntered_loade_export_presets
        )

        self._loade_export_presets()


    def _loade_export_presets(self):
        """
        读取导出预设 并绑定到UI
        """

        if not substance_painter.project.is_open():
            return
        
        #清空列表
        self._ui.select_preset.clear()

        #读取默认输出预设
        substance_painter.resource.import_session_resource(self._root_path + "/assets/export-presets/SPSYNCDefault.spexp", 
                                                           substance_painter.resource.Usage.EXPORT)

        resource_presets_list:list[substance_painter.export.ResourceExportPreset] = substance_painter.export.list_resource_export_presets()
        resource_presets_list.sort(key=lambda x: x.resource_id.name != "SPSYNCDefault")

        for preset in resource_presets_list: 
            self._ui.select_preset.addItem(preset.resource_id.name)

        #读取配置
        self._load_data()

    def _select_preset_changed(self, index:int):

        if not substance_painter.project.is_open():
            return
        
        """
        预设导出绑定事件
        """
        if substance_painter.project.is_open():
            if index != -1:
                self._ui.select_preset.setCurrentIndex(index)
                resource_presets_list:list[substance_painter.export.ResourceExportPreset] = substance_painter.export.list_resource_export_presets()

                for preset in resource_presets_list: 
                    if self._ui.select_preset.currentText() == preset.resource_id.name:
                        self._current_preset = preset
                        self._save_data()

    def _get_texture_sets(self)->List[str]:
        """
        获取材质名列表
        """
        
        export_list = []
        for texture_set in substance_painter.textureset.all_texture_sets():
            export_list.append(texture_set.name())
        return export_list

    def _sync_button_click(self):
        
        if not substance_painter.project.is_open():
            return
        
        if self._current_preset == None:
            QtWidgets.QMessageBox.information(self._main_widget, "提示", "需要指定贴图输出配置!")
            return
        
        self._ui.sync_mesh_button.setEnabled(False)
        self._ui.sync_button.setEnabled(False)
            
        self._export_sync_button_type = True

        export_list = []
        for texture_set in substance_painter.textureset.all_texture_sets():
            export_list.append({"rootPath" : texture_set.name()})

        newPreset = {
            "name": self._current_preset.resource_id.name,
            "maps": self._current_preset.list_output_maps()
        }
      
        export_config = {
            "exportShaderParams": False,
            "exportPath": self._temp_path,
            "defaultExportPreset" : newPreset["name"],
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

        substance_painter.export.export_project_textures(export_config)
    
    def _sync_button_mesh_click(self):

        if not substance_painter.project.is_open():
            return
        
        if self._current_preset == None:
            QtWidgets.QMessageBox.information(self._main_widget, "提示", "需要指定贴图输出配置!")
            return

        self._sync_button_click()

        export_path = self._temp_path + "/" + self._current_mesh_name + ".fbx"
        request = substance_painter.export.export_mesh(export_path, substance_painter.export.MeshExportOption.TriangulatedMesh)
        self._sp_sync_ue.ue_import_mesh(self._ui.file_path.text(), export_path, self._reset_all_freeze_ui)

    def _save_data(self):
        """
        保存配置
        """
        metadata:substance_painter.project.Metadata = substance_painter.project.Metadata("sp_sync")
        metadata.set("export_path", self._ui.file_path.text())
        metadata.set("origin_export_path", self._origin_export_path)
        metadata.set("current_preset", self._ui.select_preset.currentText())

    def _load_data(self):
        """
        读取配置
        """
        metadata:substance_painter.project.Metadata = substance_painter.project.Metadata("sp_sync")
        self._ui.file_path.setText(metadata.get("export_path"))
        self._origin_export_path = metadata.get("origin_export_path")

        current_preset = metadata.get("current_preset")
 
        for i in range(self._ui.select_preset.count()):
            if self._ui.select_preset.itemText(i) == current_preset:
                self._ui.select_preset.setCurrentIndex(i)
   
            for preset in substance_painter.export.list_resource_export_presets(): 
                if self._ui.select_preset.currentText() == preset.resource_id.name:
                    self._current_preset = preset

    def _view_sync_click(self):
        if self._ui.sync_view.isChecked():
            if substance_painter.project.is_open():
                self._sp_sync_ue.sync_ue_camera_init()
        else:
            self._sp_sync_ue.close_ue_sync_camera()
     
    def _config_ui(self):
        """
        配置UI
        """
        self._main_widget = QtWidgets.QWidget()
        self._main_widget.setWindowTitle("sp_sync")

        self._ui = Ui_SPsync()
        self._ui.setupUi(self._main_widget)

        #绑定选择路径按钮事件
        self._ui.file_select.clicked.connect(self._select_file_button_click)

        #绑定同步按钮事件
        self._ui.sync_button.clicked.connect(self._sync_button_click)

        #绑定列表选中事件
        self._ui.select_preset.highlighted.connect(self._select_preset_changed)

        self._ui.sync_view.clicked.connect(self._view_sync_click)

        self._ui.sync_mesh_button.clicked.connect(self._sync_button_mesh_click)

        self.plugin_widgets.append(self._main_widget)
        substance_painter.ui.add_dock_widget(self._main_widget)
