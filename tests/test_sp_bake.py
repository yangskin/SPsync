import types
from unittest.mock import Mock

import substance_painter

import sp_bake


class _DummyButton:
    def __init__(self):
        self.enabled = None
        self.text = None

    def setEnabled(self, value):
        self.enabled = value

    def setText(self, value):
        self.text = value


class _DummyUI:
    def __init__(self):
        self.highpoly_select = _DummyButton()
        self.bake_highpoly_button = _DummyButton()


def test_finish_bake_switches_back_to_edition_mode(monkeypatch):
    dispatcher = types.SimpleNamespace(disconnect=lambda *args, **kwargs: None)
    ui_mode = types.SimpleNamespace(Edition="Edition", Baking="Baking")
    switch_to_mode = Mock()
    message_box = types.SimpleNamespace(information=Mock(), warning=Mock())
    main_widget = object()

    monkeypatch.setattr(substance_painter.project, "is_open", lambda: True, raising=False)
    monkeypatch.setattr(substance_painter.ui, "UIMode", ui_mode, raising=False)
    monkeypatch.setattr(substance_painter.ui, "get_current_mode", lambda: ui_mode.Baking, raising=False)
    monkeypatch.setattr(substance_painter.ui, "switch_to_mode", switch_to_mode, raising=False)
    monkeypatch.setattr(substance_painter.event, "DISPATCHER", dispatcher, raising=False)
    monkeypatch.setattr(substance_painter.event, "BakingProcessAboutToStart", object(), raising=False)
    monkeypatch.setattr(substance_painter.event, "BakingProcessProgress", object(), raising=False)
    monkeypatch.setattr(substance_painter.event, "BakingProcessEnded", object(), raising=False)
    monkeypatch.setattr(sp_bake.QtWidgets, "QMessageBox", message_box, raising=False)

    manager = sp_bake.SPBakeManager(_DummyUI(), main_widget, types.SimpleNamespace(highpoly_mesh_path=""))
    manager._is_baking = True
    manager._current_texture_set_name = "Body"
    manager._bake_queue = [object()]

    manager._finish_bake(True, "done")

    switch_to_mode.assert_called_once_with(ui_mode.Edition)
    message_box.information.assert_called_once_with(main_widget, "High Poly Bake", "done")
    assert manager._is_baking is False
    assert manager._bake_queue == []
    assert manager._current_texture_set_name == ""
    assert manager._ui.bake_highpoly_button.text == "Bake (HighPoly)"