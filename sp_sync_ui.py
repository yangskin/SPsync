# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'sp_sync_ui.ui'
##
## Created by: Qt User Interface Compiler version 5.15.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *


class Ui_SPsync(object):
    def setupUi(self, SPsync):
        if not SPsync.objectName():
            SPsync.setObjectName(u"SPsync")
        SPsync.setEnabled(True)
        SPsync.resize(380, 526)
        self.gridLayout_2 = QGridLayout(SPsync)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.tabWidget = QTabWidget(SPsync)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabWidget.setEnabled(True)
        self.tabWidget.setAutoFillBackground(True)
        self.tabWidget.setTabPosition(QTabWidget.North)
        self.tabWidget.setTabsClosable(False)
        self.tabWidget.setMovable(True)
        self.tabWidget.setTabBarAutoHide(False)
        self.unreal = QWidget()
        self.unreal.setObjectName(u"unreal")
        self.unreal.setEnabled(True)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.unreal.sizePolicy().hasHeightForWidth())
        self.unreal.setSizePolicy(sizePolicy)
        self.unreal.setSizeIncrement(QSize(0, 0))
        self.unreal.setBaseSize(QSize(0, 0))
        self.unreal.setLayoutDirection(Qt.LeftToRight)
        self.unreal.setAutoFillBackground(False)
        self.verticalLayout_2 = QVBoxLayout(self.unreal)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(-1, 0, -1, -1)
        self.file_path = QLineEdit(self.unreal)
        self.file_path.setObjectName(u"file_path")
        self.file_path.setBaseSize(QSize(0, 0))

        self.horizontalLayout.addWidget(self.file_path)

        self.file_select = QPushButton(self.unreal)
        self.file_select.setObjectName(u"file_select")

        self.horizontalLayout.addWidget(self.file_select)


        self.verticalLayout_2.addLayout(self.horizontalLayout)

        self.sync_button = QPushButton(self.unreal)
        self.sync_button.setObjectName(u"sync_button")

        self.verticalLayout_2.addWidget(self.sync_button)

        self.sync_mesh_button = QPushButton(self.unreal)
        self.sync_mesh_button.setObjectName(u"sync_mesh_button")

        self.verticalLayout_2.addWidget(self.sync_mesh_button)

        self.auto_sync = QCheckBox(self.unreal)
        self.auto_sync.setObjectName(u"auto_sync")
        self.auto_sync.setChecked(True)

        self.verticalLayout_2.addWidget(self.auto_sync)

        self.create_material = QCheckBox(self.unreal)
        self.create_material.setObjectName(u"create_material")
        self.create_material.setChecked(True)

        self.verticalLayout_2.addWidget(self.create_material)

        self.sync_view = QToolButton(self.unreal)
        self.sync_view.setObjectName(u"sync_view")
        sizePolicy1 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.sync_view.sizePolicy().hasHeightForWidth())
        self.sync_view.setSizePolicy(sizePolicy1)
        self.sync_view.setMinimumSize(QSize(0, 50))
        self.sync_view.setTabletTracking(False)
        self.sync_view.setAcceptDrops(False)
        self.sync_view.setLayoutDirection(Qt.LeftToRight)
        self.sync_view.setAutoFillBackground(False)
        self.sync_view.setCheckable(True)
        self.sync_view.setChecked(False)

        self.verticalLayout_2.addWidget(self.sync_view)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setSpacing(6)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(-1, -1, 0, 0)

        self.verticalLayout_2.addLayout(self.horizontalLayout_3)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.verticalLayout_2.addItem(self.verticalSpacer_2)

        self.tabWidget.addTab(self.unreal, "")
        self.Help = QWidget()
        self.Help.setObjectName(u"Help")
        self.Help.setEnabled(True)
        sizePolicy.setHeightForWidth(self.Help.sizePolicy().hasHeightForWidth())
        self.Help.setSizePolicy(sizePolicy)
        self.Help.setAutoFillBackground(False)
        self.verticalLayout = QVBoxLayout(self.Help)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.help_video = QPushButton(self.Help)
        self.help_video.setObjectName(u"help_video")

        self.verticalLayout.addWidget(self.help_video)

        self.verticalSpacer_3 = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer_3)

        self.tabWidget.addTab(self.Help, "")

        self.gridLayout_2.addWidget(self.tabWidget, 1, 0, 1, 1)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(-1, 0, -1, -1)
        self.select_preset = QComboBox(SPsync)
        self.select_preset.addItem("")
        self.select_preset.setObjectName(u"select_preset")

        self.horizontalLayout_2.addWidget(self.select_preset)


        self.gridLayout_2.addLayout(self.horizontalLayout_2, 0, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 206, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.gridLayout_2.addItem(self.verticalSpacer, 2, 0, 1, 1)


        self.retranslateUi(SPsync)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(SPsync)
    # setupUi

    def retranslateUi(self, SPsync):
        SPsync.setWindowTitle(QCoreApplication.translate("SPsync", u"SPsync", None))
        self.file_select.setText(QCoreApplication.translate("SPsync", u"Selet Path", None))
        self.sync_button.setText(QCoreApplication.translate("SPsync", u"SYNC", None))
        self.sync_mesh_button.setText(QCoreApplication.translate("SPsync", u"SYNC(Mesh)", None))
        self.auto_sync.setText(QCoreApplication.translate("SPsync", u"Auto Export Texture", None))
        self.create_material.setText(QCoreApplication.translate("SPsync", u"Create Materials", None))
        self.sync_view.setText(QCoreApplication.translate("SPsync", u"View Sync", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.unreal), QCoreApplication.translate("SPsync", u"Unreal", None))
        self.help_video.setText(QCoreApplication.translate("SPsync", u"Video Tutorial", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.Help), QCoreApplication.translate("SPsync", u"Help", None))
        self.select_preset.setItemText(0, QCoreApplication.translate("SPsync", u"Default", None))

    # retranslateUi

