# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'sp_sync_ui.ui'
##
## Created by: Qt User Interface Compiler version 6.8.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDoubleSpinBox,
    QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSizePolicy, QSpacerItem,
    QTabWidget, QTextBrowser, QToolButton, QVBoxLayout,
    QWidget)

class Ui_SPsync(object):
    def setupUi(self, SPsync):
        if not SPsync.objectName():
            SPsync.setObjectName(u"SPsync")
        SPsync.setEnabled(True)
        SPsync.resize(380, 526)
        self.gridLayout_2 = QGridLayout(SPsync)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(-1, 0, -1, -1)

        self.gridLayout_2.addLayout(self.horizontalLayout_2, 0, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 206, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_2.addItem(self.verticalSpacer, 2, 0, 1, 1)

        self.tabWidget = QTabWidget(SPsync)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabWidget.setEnabled(True)
        self.tabWidget.setAutoFillBackground(True)
        self.tabWidget.setTabPosition(QTabWidget.TabPosition.North)
        self.tabWidget.setTabsClosable(False)
        self.tabWidget.setMovable(True)
        self.tabWidget.setTabBarAutoHide(False)
        self.unreal = QWidget()
        self.unreal.setObjectName(u"unreal")
        self.unreal.setEnabled(True)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.unreal.sizePolicy().hasHeightForWidth())
        self.unreal.setSizePolicy(sizePolicy)
        self.unreal.setSizeIncrement(QSize(0, 0))
        self.unreal.setBaseSize(QSize(0, 0))
        self.unreal.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.unreal.setAutoFillBackground(False)
        self.verticalLayout_2 = QVBoxLayout(self.unreal)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.label = QLabel(self.unreal)
        self.label.setObjectName(u"label")

        self.verticalLayout_2.addWidget(self.label)

        self.select_preset = QComboBox(self.unreal)
        self.select_preset.setObjectName(u"select_preset")

        self.verticalLayout_2.addWidget(self.select_preset)

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

        self.groupBox = QGroupBox(self.unreal)
        self.groupBox.setObjectName(u"groupBox")
        self.groupBox.setEnabled(True)
        self.verticalLayout_3 = QVBoxLayout(self.groupBox)
        self.verticalLayout_3.setSpacing(5)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(5, 5, 5, 5)
        self.create_material = QCheckBox(self.groupBox)
        self.create_material.setObjectName(u"create_material")
        self.create_material.setChecked(True)

        self.verticalLayout_3.addWidget(self.create_material)


        self.verticalLayout_2.addWidget(self.groupBox)

        self.groupBox_2 = QGroupBox(self.unreal)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.verticalLayout_4 = QVBoxLayout(self.groupBox_2)
        self.verticalLayout_4.setSpacing(5)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(5, 5, 5, 5)
        self.label_2 = QLabel(self.groupBox_2)
        self.label_2.setObjectName(u"label_2")

        self.verticalLayout_4.addWidget(self.label_2)

        self.mesh_scale = QDoubleSpinBox(self.groupBox_2)
        self.mesh_scale.setObjectName(u"mesh_scale")
        self.mesh_scale.setMaximum(99999.899999999994179)
        self.mesh_scale.setSingleStep(0.100000000000000)
        self.mesh_scale.setValue(100.000000000000000)

        self.verticalLayout_4.addWidget(self.mesh_scale)


        self.verticalLayout_2.addWidget(self.groupBox_2)

        self.groupBox_3 = QGroupBox(self.unreal)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.verticalLayout_5 = QVBoxLayout(self.groupBox_3)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.force_front_x_axis = QCheckBox(self.groupBox_3)
        self.force_front_x_axis.setObjectName(u"force_front_x_axis")
        self.force_front_x_axis.setChecked(True)

        self.verticalLayout_5.addWidget(self.force_front_x_axis)

        self.sync_view = QToolButton(self.groupBox_3)
        self.sync_view.setObjectName(u"sync_view")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.sync_view.sizePolicy().hasHeightForWidth())
        self.sync_view.setSizePolicy(sizePolicy1)
        self.sync_view.setMinimumSize(QSize(0, 50))
        self.sync_view.setTabletTracking(False)
        self.sync_view.setAcceptDrops(False)
        self.sync_view.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.sync_view.setAutoFillBackground(False)
        self.sync_view.setCheckable(True)
        self.sync_view.setChecked(False)

        self.verticalLayout_5.addWidget(self.sync_view)


        self.verticalLayout_2.addWidget(self.groupBox_3)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setSpacing(6)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(-1, -1, 0, 0)

        self.verticalLayout_2.addLayout(self.horizontalLayout_3)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

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

        self.textBrowser = QTextBrowser(self.Help)
        self.textBrowser.setObjectName(u"textBrowser")

        self.verticalLayout.addWidget(self.textBrowser)

        self.verticalSpacer_3 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer_3)

        self.tabWidget.addTab(self.Help, "")

        self.gridLayout_2.addWidget(self.tabWidget, 2, 1, 1, 1)


        self.retranslateUi(SPsync)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(SPsync)
    # setupUi

    def retranslateUi(self, SPsync):
        SPsync.setWindowTitle(QCoreApplication.translate("SPsync", u"SPsync 0.964", None))
        self.label.setText(QCoreApplication.translate("SPsync", u"Export Preset:", None))
        self.file_select.setText(QCoreApplication.translate("SPsync", u"Selet Path", None))
        self.sync_button.setText(QCoreApplication.translate("SPsync", u"SYNC", None))
        self.sync_mesh_button.setText(QCoreApplication.translate("SPsync", u"SYNC(Mesh)", None))
        self.auto_sync.setText(QCoreApplication.translate("SPsync", u"Auto Export Texture", None))
        self.groupBox.setTitle(QCoreApplication.translate("SPsync", u"Material", None))
        self.create_material.setText(QCoreApplication.translate("SPsync", u"Create Materials", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("SPsync", u"Mesh", None))
        self.label_2.setText(QCoreApplication.translate("SPsync", u"Scale", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("SPsync", u"View", None))
        self.force_front_x_axis.setText(QCoreApplication.translate("SPsync", u"Force front x axis", None))
        self.sync_view.setText(QCoreApplication.translate("SPsync", u"View Sync", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.unreal), QCoreApplication.translate("SPsync", u"Unreal", None))
        self.help_video.setText(QCoreApplication.translate("SPsync", u"Video Tutorial", None))
        self.textBrowser.setHtml(QCoreApplication.translate("SPsync", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><meta charset=\"utf-8\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"hr { height: 1px; border-width: 0; }\n"
"li.unchecked::marker { content: \"\\2610\"; }\n"
"li.checked::marker { content: \"\\2612\"; }\n"
"</style></head><body style=\" font-family:'Microsoft YaHei UI'; font-size:9pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-family:'SimSun'; font-size:7pt;\">Emial    : yangskin@163.com</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-family:'SimSun'; font-size:7pt;\">BiliBili : https://space.bilibili.com/249466</span></p></body></html>", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.Help), QCoreApplication.translate("SPsync", u"Help", None))
    # retranslateUi

