# -*- coding: utf-8 -*-
from pathlib import Path

import substance_painter.application
import substance_painter.baking
import substance_painter.event
import substance_painter.project
import substance_painter.textureset

IsQt5 = substance_painter.application.version_info() < (10, 1, 0)

if IsQt5:
    from PySide2 import QtWidgets
else:
    from PySide6 import QtWidgets


class SPBakeManager:
    """管理高模路径选择与常用 Mesh Map 烘焙。"""

    DEFAULT_BAKER_NAMES = (
        "Normal",
        "AO",
        "Curvature",
        "Position",
        "Thickness",
    )

    def __init__(self, ui, main_widget, config):
        self._ui = ui
        self._main_widget = main_widget
        self._config = config

        self._bake_queue = []
        self._completed_texture_sets = []
        self._current_texture_set_name = ""
        self._is_baking = False

    def select_highpoly_mesh(self):
        if not substance_painter.project.is_open():
            return

        current_path = self._config.highpoly_mesh_path
        start_dir = current_path if current_path and Path(current_path).exists() else str(Path.home())
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self._main_widget,
            "Select High Poly Mesh",
            start_dir,
            "Mesh Files (*.fbx *.obj *.dae *.ply *.usd);;All Files (*)",
        )

        if file_path:
            self._set_highpoly_mesh_path(file_path)

    def bake_selected_highpoly_maps(self):
        if not substance_painter.project.is_open() or not substance_painter.project.is_in_edition_state():
            QtWidgets.QMessageBox.information(
                self._main_widget,
                "Warning",
                "Open a Substance Painter project before running High Poly bake.",
            )
            return

        if self._is_baking or substance_painter.project.is_busy():
            QtWidgets.QMessageBox.information(
                self._main_widget,
                "Warning",
                "Substance Painter is busy. Wait until the current task finishes.",
            )
            return

        highpoly_path = self._config.highpoly_mesh_path
        if not highpoly_path:
            self.select_highpoly_mesh()
            highpoly_path = self._config.highpoly_mesh_path
            if not highpoly_path:
                return

        highpoly_file = Path(highpoly_path)
        if not highpoly_file.is_file():
            QtWidgets.QMessageBox.warning(
                self._main_widget,
                "Warning",
                "The selected high poly file does not exist.",
            )
            return

        highpoly_uri = highpoly_file.resolve().as_uri()
        texture_sets = list(substance_painter.textureset.all_texture_sets())
        if not texture_sets:
            QtWidgets.QMessageBox.warning(
                self._main_widget,
                "Warning",
                "No Texture Set is available in the current project.",
            )
            return

        bakers = self._resolve_default_bakers()
        if not bakers:
            QtWidgets.QMessageBox.warning(
                self._main_widget,
                "Warning",
                "No supported baker was found in this Substance Painter version.",
            )
            return

        try:
            for texture_set in texture_sets:
                self._configure_texture_set(texture_set, highpoly_uri, bakers)
        except Exception as exc:
            QtWidgets.QMessageBox.warning(
                self._main_widget,
                "Bake Setup Failed",
                f"Unable to configure baking parameters: {exc}",
            )
            return

        self._bake_queue = texture_sets[:]
        self._completed_texture_sets = []
        self._current_texture_set_name = ""
        self._connect_events()
        self._set_bake_ui_state(True)
        self._is_baking = True
        self._bake_next_texture_set()

    def on_project_close(self):
        self._disconnect_events()
        self._is_baking = False
        self._bake_queue = []
        self._completed_texture_sets = []
        self._current_texture_set_name = ""
        self._set_bake_ui_state(False)
        self._config.highpoly_mesh_path = ""
        self._ui.highpoly_path.setText("")

    def _set_highpoly_mesh_path(self, file_path: str):
        self._config.highpoly_mesh_path = file_path
        self._ui.highpoly_path.setText(file_path)
        self._config.save(self._ui)

    def _resolve_default_bakers(self):
        resolved = []
        for baker_name in self.DEFAULT_BAKER_NAMES:
            if hasattr(substance_painter.textureset.MeshMapUsage, baker_name):
                resolved.append(getattr(substance_painter.textureset.MeshMapUsage, baker_name))
        return resolved

    def _configure_texture_set(self, texture_set, highpoly_uri: str, bakers):
        baking_params = substance_painter.baking.BakingParameters.from_texture_set(texture_set)
        common_params = baking_params.common()
        values = {}

        if "HipolyMesh" not in common_params:
            raise RuntimeError("Current Substance Painter version does not expose 'HipolyMesh'.")

        if "LowAsHigh" in common_params:
            values[common_params["LowAsHigh"]] = False
        values[common_params["HipolyMesh"]] = highpoly_uri

        if values:
            baking_params.set(values)

        baking_params.set_textureset_enabled(True)
        baking_params.set_enabled_bakers(bakers)

    def _connect_events(self):
        substance_painter.event.DISPATCHER.connect(
            substance_painter.event.BakingProcessAboutToStart,
            self._on_bake_start,
        )
        substance_painter.event.DISPATCHER.connect(
            substance_painter.event.BakingProcessProgress,
            self._on_bake_progress,
        )
        substance_painter.event.DISPATCHER.connect(
            substance_painter.event.BakingProcessEnded,
            self._on_bake_end,
        )

    def _disconnect_events(self):
        for event_type, handler in (
            (substance_painter.event.BakingProcessAboutToStart, self._on_bake_start),
            (substance_painter.event.BakingProcessProgress, self._on_bake_progress),
            (substance_painter.event.BakingProcessEnded, self._on_bake_end),
        ):
            try:
                substance_painter.event.DISPATCHER.disconnect(event_type, handler)
            except Exception:
                pass

    def _set_bake_ui_state(self, baking: bool):
        self._ui.highpoly_select.setEnabled(not baking)
        self._ui.bake_highpoly_button.setEnabled(not baking)
        if baking:
            label = self._current_texture_set_name or "Preparing"
            self._ui.bake_highpoly_button.setText(f"Baking: {label}")
        else:
            self._ui.bake_highpoly_button.setText("Bake (HighPoly)")

    def _bake_next_texture_set(self):
        if not self._bake_queue:
            completed_text = ", ".join(self._completed_texture_sets) if self._completed_texture_sets else "None"
            self._finish_bake(
                success=True,
                message=f"High poly bake finished. Texture Sets: {completed_text}",
            )
            return

        texture_set = self._bake_queue.pop(0)
        self._current_texture_set_name = texture_set.name()
        self._set_bake_ui_state(True)

        try:
            substance_painter.baking.bake_async(texture_set)
        except Exception as exc:
            self._finish_bake(
                success=False,
                message=f"Failed to start bake for '{self._current_texture_set_name}': {exc}",
            )

    def _on_bake_start(self, _event):
        self._set_bake_ui_state(True)

    def _on_bake_progress(self, event):
        if self._is_baking:
            percent = int(event.progress * 100)
            self._ui.bake_highpoly_button.setText(
                f"Baking: {self._current_texture_set_name} ({percent}%)"
            )

    def _on_bake_end(self, event):
        status_text = str(event.status).split(".")[-1]
        if status_text == "Success":
            if self._current_texture_set_name:
                self._completed_texture_sets.append(self._current_texture_set_name)
            self._bake_next_texture_set()
            return

        self._finish_bake(
            success=False,
            message=(
                f"Bake stopped on '{self._current_texture_set_name}' with status: {status_text}"
            ),
        )

    def _finish_bake(self, success: bool, message: str):
        self._disconnect_events()
        self._is_baking = False
        self._bake_queue = []
        self._current_texture_set_name = ""
        self._set_bake_ui_state(False)

        if success:
            QtWidgets.QMessageBox.information(self._main_widget, "High Poly Bake", message)
        else:
            QtWidgets.QMessageBox.warning(self._main_widget, "High Poly Bake", message)