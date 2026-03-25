import sys
import os
import types

# 将插件根目录加入 path，让 sp_channel_map / sp_receive 等可直接 import
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)

# ---------------------------------------------------------------------------
# Mock substance_painter 及全部子模块
# sp_sync.py 在模块顶层调用 substance_painter.application.version_info()，
# 因此 mock 必须在任何 SPsync 包导入之前就位。
# ---------------------------------------------------------------------------
_sp_root = types.ModuleType("substance_painter")
_sp_sub_names = [
    "ui", "event", "project", "resource", "textureset",
    "layerstack", "export", "application",
]
for _name in _sp_sub_names:
    _sub = types.ModuleType(f"substance_painter.{_name}")
    setattr(_sp_root, _name, _sub)
    sys.modules[f"substance_painter.{_name}"] = _sub

# application.version_info() 必须返回可比较的 tuple
_sp_root.application.version_info = lambda: (10, 1, 0)

sys.modules["substance_painter"] = _sp_root

# Mock PySide2 / PySide6（sp_sync.py 按版本二选一导入 QtWidgets）
for _pyside in ("PySide2", "PySide6"):
    _ps = types.ModuleType(_pyside)
    _qw = types.ModuleType(f"{_pyside}.QtWidgets")
    setattr(_ps, "QtWidgets", _qw)
    sys.modules[_pyside] = _ps
    sys.modules[f"{_pyside}.QtWidgets"] = _qw

# Mock SPsync 包自身，阻止 __init__.py 执行其 SP 导入链。
# 测试通过 sys.path 直接 import sp_channel_map / sp_receive，无需 SPsync 包。
sys.modules["SPsync"] = types.ModuleType("SPsync")

# 防止 pytest 遍历父目录的 __init__.py
collect_ignore_glob = ["../__init__.py", "../sp_sync*.py"]
