# -*- coding: utf-8 -*-
import os
import tempfile
import shutil
from typing import List
import webbrowser

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
    from PySide2 import QtGui
    from PySide2 import QtCore
    from PySide2.QtGui import QPixmap
else :
    from PySide6 import QtWidgets
    from PySide6 import QtGui
    from PySide6 import QtCore
    from PySide6.QtGui import QPixmap

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
    _current_udim_type:bool = False

    _sp_sync_ue:ue_sync
    _load_type:bool = False
    _current_set_names:List[str] = []
   
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

        if substance_painter.project.is_open() and (not substance_painter.resource.Shelf("starter_assets").is_crawling()):
            self._loade_export_presets()
            self._load_data()
        
        #绑定贴图导出事件
        substance_painter.event.DISPATCHER.connect(
            substance_painter.event.ExportTexturesEnded,
            self._export_end_event
        )

        #绑定项目开启事件
        substance_painter.event.DISPATCHER.connect(
            substance_painter.event.ProjectOpened,
            self._project_open_event
        )
        #绑定项目创建事件
        substance_painter.event.DISPATCHER.connect(
            substance_painter.event.ProjectCreated,
            self._project_open_event
        )

        substance_painter.event.DISPATCHER.connect(
            substance_painter.event.ProjectAboutToClose,
            self._project_about_to_close_event
        )

        substance_painter.event.DISPATCHER.connect(
            substance_painter.event.LayerStacksModelDataChanged, 
            self._on_layerstack_changed
        )

    def _on_layerstack_changed(self, event: substance_painter.event.LayerStacksModelDataChanged):
        """
        获取选中的纹理组        
        """

        stack:substance_painter.textureset.Stack = substance_painter.textureset.get_active_stack()
        current_set_name = stack.material().name()
        if current_set_name not in self._current_set_names:
            self._current_set_names.append(current_set_name)
        
    def _clean_temp_folder(self):
        """
        清理临时文件夹
        """
        if os.path.exists(self._temp_path):
            shutil.rmtree(self._temp_path)

    def _export_all_set(self):
        self._current_set_names = []
        for texture_set in substance_painter.textureset.all_texture_sets():
            self._current_set_names.append(texture_set.name())

    def _get_project_udim_type(self)->bool:
        """
        获取项目是否支持UDIM
        可能不科学
        """
        for texture_set in substance_painter.textureset.all_texture_sets():
            return texture_set.has_uv_tiles()
        return False
    
    def _get_texture_set_material_type(self):
        texture_set_list:List[substance_painter.textureset.TextureSet] = substance_painter.textureset.all_texture_sets()
        request = []
        for texture_set in texture_set_list:
            current_material_type:str = "opaque"
            for stack in texture_set.all_stacks():
                for channel in stack.all_channels().keys():
                    if channel == substance_painter.textureset.ChannelType.Opacity:
                        current_material_type = "masked"
                    if channel == substance_painter.textureset.ChannelType.Translucency:
                        current_material_type = "translucency"
            request.append([texture_set.name(), current_material_type])
        
        return request


    def _project_open_event(self, state):
        """
        项目打开
        """
        
        self._current_preset = None

        self._sp_sync_ue.set_material_masked(False)
        self._sp_sync_ue.set_material_translucent(False)

        self._export_all_set()

        self._reset_all_freeze_ui(True)

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

        self._current_udim_type = self._get_project_udim_type()
        self._sp_sync_ue.set_udim_type(self._current_udim_type)

        self._get_texture_set_material_type()

        
    def _project_about_to_close_event(self, state):

        self._load_type = False

        self._ui.tabWidget.setEnabled(False)
        self._ui.file_path.setText("")
        self._ui.select_preset.currentIndexChanged.disconnect(self._select_preset_changed)
        self._ui.mesh_scale.valueChanged.disconnect(self._mesh_scale_changed)
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
                QtWidgets.QMessageBox.information(self._main_widget, "Warning", "You need to specify the output path under the 'content/' directory in the engine!")
                return
            
            export_file_list = []
            for item in export_data.textures:
                for file in export_data.textures[item]:
                    export_file_list.append(file)

            if self._ui.create_material.isChecked():
                if self._current_preset.resource_id.name == "SPSYNCDefault":
                    self._sp_sync_ue.sync_ue_textures(self._ui.file_path.text(), export_file_list)
                    self._sp_sync_ue.sync_ue_create_material_and_connect_textures(self._ui.file_path.text(), self._current_mesh_name, self._current_set_names, self._get_texture_set_material_type(), self._reset_all_freeze_ui)
                else:
                    self._sp_sync_ue.sync_ue_textures(self._ui.file_path.text(), export_file_list, self._reset_all_freeze_ui)
                    self._ui.create_material.setChecked(False)
                    QtWidgets.QMessageBox.information(self._main_widget, "Warning", "The texture output configuration must be 'SPSYNCDefault' to generate materials!")
            else:
                self._sp_sync_ue.sync_ue_textures(self._ui.file_path.text(), export_file_list, self._reset_all_freeze_ui)

            #清空当前修改材质列表
            self._current_set_names = []
            self._on_layerstack_changed(None)


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
            QtWidgets.QMessageBox.information(self._main_widget, "Warning", "You need to specify the output path under the 'content/' directory in the engine!")

    def _wait_ShelfCrawlingEnded_loade_export_presets(self, state):
        if state.shelf_name ==  "starter_assets":
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
        
        if self._load_type:
            return

        if not substance_painter.project.is_open():
            return
        
        #清空列表
        self._ui.select_preset.clear()

        if len(substance_painter.export.list_resource_export_presets()) < 10:
            return

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
            QtWidgets.QMessageBox.information(self._main_widget, "Warning", "Need to specify the texture output configuration!")
            return
        
        self._ui.sync_mesh_button.setEnabled(False)
        self._ui.sync_button.setEnabled(False)
            
        self._export_sync_button_type = True

        export_list = []

        for _current_set_names in self._current_set_names:
            export_list.append({"rootPath" : _current_set_names})
        
        self._on_layerstack_changed(None)

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
            QtWidgets.QMessageBox.information(self._main_widget, "Warning", "Need to specify the texture output configuration!")
            return

        self._export_all_set()

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
        metadata.set("mesh_scale", self._ui.mesh_scale.value())

    def _load_data(self):
        """
        读取配置
        """

        metadata:substance_painter.project.Metadata = substance_painter.project.Metadata("sp_sync")
        self._ui.file_path.setText(metadata.get("export_path"))
        self._origin_export_path = metadata.get("origin_export_path")
        key_list = metadata.list()

        if "mesh_scale" in key_list:
            self._ui.mesh_scale.setValue(metadata.get("mesh_scale"))
            self._sp_sync_ue.set_mesh_scale(metadata.get("mesh_scale"))
        else:
            self._ui.mesh_scale.setValue(100)
            self._sp_sync_ue.set_mesh_scale(100)

        current_preset = metadata.get("current_preset")

        for i in range(self._ui.select_preset.count()):
            if self._ui.select_preset.itemText(i) == current_preset:
                self._ui.select_preset.setCurrentIndex(i)

            for preset in substance_painter.export.list_resource_export_presets(): 
                if self._ui.select_preset.currentText() == preset.resource_id.name:
                    self._current_preset = preset

        self._ui.select_preset.currentIndexChanged.connect(self._select_preset_changed)
        self._ui.mesh_scale.valueChanged.connect(self._mesh_scale_changed)
        self._ui.tabWidget.setEnabled(True)
        self._load_type = True

    def _view_sync_click(self):
        if self._ui.sync_view.isChecked():
            if substance_painter.project.is_open():
                self._sp_sync_ue.sync_ue_camera_init()
        else:
            self._sp_sync_ue.close_ue_sync_camera()

    def _help_video_click(self):
        webbrowser.open("https://www.bilibili.com/video/BV1XS11YKEJe/")

    def _mesh_scale_changed(self):
        self._sp_sync_ue.set_mesh_scale(self._ui.mesh_scale.value())
        self._save_data()
     
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

        self._ui.sync_view.clicked.connect(self._view_sync_click)

        self._ui.sync_mesh_button.clicked.connect(self._sync_button_mesh_click)

        self._ui.help_video.clicked.connect(self._help_video_click)

        self.plugin_widgets.append(self._main_widget)
        substance_painter.ui.add_dock_widget(self._main_widget)

        if (not substance_painter.project.is_open()) and (not substance_painter.project.is_busy()):
            self._ui.tabWidget.setEnabled(False)
            
