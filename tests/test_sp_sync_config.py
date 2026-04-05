import importlib.util
import os
import sys
import types

import substance_painter


def _load_sp_sync_config_module(sp_receive_stub):
    plugin_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    package = sys.modules.get("SPsync")
    if package is None:
        package = types.ModuleType("SPsync")
        sys.modules["SPsync"] = package
    package.__path__ = [plugin_root]

    sys.modules["SPsync.sp_receive"] = sp_receive_stub

    module_name = "SPsync.sp_sync_config"
    sys.modules.pop(module_name, None)

    spec = importlib.util.spec_from_file_location(
        module_name,
        os.path.join(plugin_root, "sp_sync_config.py"),
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class _DummyLineEdit:
    def __init__(self):
        self.value = ""

    def setText(self, value):
        self.value = value

    def text(self):
        return self.value


class _DummyCheckBox:
    def __init__(self):
        self.checked = None
        self.visible = None

    def setChecked(self, value):
        self.checked = value

    def isChecked(self):
        return bool(self.checked)

    def setVisible(self, value):
        self.visible = value


class _DummySpinBox:
    def __init__(self):
        self.current = None

    def setValue(self, value):
        self.current = value

    def value(self):
        return self.current


class _DummyComboBox:
    def __init__(self):
        self.items = []
        self.current_index = 0

    def count(self):
        return len(self.items)

    def itemText(self, index):
        return self.items[index]

    def setCurrentIndex(self, index):
        self.current_index = index

    def currentText(self):
        if not self.items:
            return ""
        return self.items[self.current_index]


class _DummyUI:
    def __init__(self):
        self.file_path = _DummyLineEdit()
        self.highpoly_path = _DummyLineEdit()
        self.mesh_scale = _DummySpinBox()
        self.force_front_x_axis = _DummyCheckBox()
        self.sync_mesh_button = _DummyCheckBox()
        self.create_material = _DummyCheckBox()
        self.select_preset = _DummyComboBox()


class _DummyMetadata:
    def __init__(self, values):
        self.values = dict(values)

    def get(self, key):
        return self.values.get(key, "")

    def set(self, key, value):
        self.values[key] = value

    def list(self):
        return list(self.values.keys())


class _DummySyncUe:
    def __init__(self):
        self.mesh_scale = None
        self.force_front_x_axis = None

    def set_mesh_scale(self, value):
        self.mesh_scale = value

    def set_force_front_x_axis(self, value):
        self.force_front_x_axis = value


def test_load_defaults_force_front_x_axis_true_for_from_ue(monkeypatch):
    sp_receive_stub = types.ModuleType("SPsync.sp_receive")
    sp_receive_stub._from_ue_pending = True
    sp_receive_stub._created_from_ue_session = True

    module = _load_sp_sync_config_module(sp_receive_stub)

    metadata = _DummyMetadata({})
    monkeypatch.setattr(substance_painter.project, "Metadata", lambda _name: metadata, raising=False)
    monkeypatch.setattr(substance_painter.export, "list_resource_export_presets", lambda: [], raising=False)

    ui = _DummyUI()
    sync_ue = _DummySyncUe()

    config = module.SPSyncConfig()
    config.load(ui, sync_ue)

    assert ui.mesh_scale.current == 1.0
    assert sync_ue.mesh_scale == 1.0
    assert ui.force_front_x_axis.checked is True
    assert sync_ue.force_front_x_axis is True
    assert ui.sync_mesh_button.visible is False


def test_load_respects_explicit_force_front_x_axis_metadata(monkeypatch):
    sp_receive_stub = types.ModuleType("SPsync.sp_receive")
    sp_receive_stub._from_ue_pending = False
    sp_receive_stub._created_from_ue_session = False

    module = _load_sp_sync_config_module(sp_receive_stub)

    metadata = _DummyMetadata({
        "from_ue": True,
        "force_front_x_axis": False,
        "mesh_scale": 1.0,
    })
    monkeypatch.setattr(substance_painter.project, "Metadata", lambda _name: metadata, raising=False)
    monkeypatch.setattr(substance_painter.export, "list_resource_export_presets", lambda: [], raising=False)

    ui = _DummyUI()
    sync_ue = _DummySyncUe()

    config = module.SPSyncConfig()
    config.load(ui, sync_ue)

    assert ui.force_front_x_axis.checked is False
    assert sync_ue.force_front_x_axis is False