# -*- coding: utf-8 -*-
"""
模块初始化 关闭时删除相关Ui控件
"""

import substance_painter.ui
from .sp_sync import sp_sync

SPSYNCPORTPLUGIN: sp_sync

def start_plugin():
    """
    启动插件
    """
    global SPSYNCPORTPLUGIN
    SPSYNCPORTPLUGIN = sp_sync()

def close_plugin():
    """
    关闭插件
    """
    global SPSYNCPORTPLUGIN

    # 关闭时移除相关UI控件
    for widget in SPSYNCPORTPLUGIN.plugin_widgets:
        substance_painter.ui.delete_ui_element(widget)

    del SPSYNCPORTPLUGIN

if __name__ == "__main__":
    start_plugin()
