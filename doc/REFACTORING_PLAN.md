# SPsync 重构方案

> 版本: 0.964 → 1.0  
> 日期: 2026-03-24  
> 方案代号: **方案 A — 一次注入 + JSON 参数化调用**

---

## 一、现状分析

### 1.1 代码规模

| 文件 | 行数 | 运行环境 | 职责 |
|------|------|---------|------|
| `__init__.py` | 31 | SP | 插件入口/生命周期 |
| `sp_sync.py` | 475 | SP | 主控制器（上帝类） |
| `sp_sync_ui.py` | 248 | SP | Qt UI 定义 |
| `sp_sync_ue.py` | 331 | SP | UE 编排/线程/远程调用 |
| `remote_execution.py` | 630 | SP | Epic 官方远程执行协议 |
| `import_textures_ue.py` | 52 | UE (远程注入) | 纹理导入 |
| `material_ue.py` | 70 | UE (远程注入) | 材质创建 |
| `material_instance_ue.py` | 30 | UE (远程注入) | 材质实例 |
| `create_material_and_connect_textures.py` | 97 | UE (远程注入) | 材质+纹理连接 |
| `import_mesh_ue.py` | 79 | UE (远程注入) | 网格导入/场景放置 |
| `sync_camera_ue.py` | 79 | UE (远程注入) | 相机同步 |
| **合计** | **2,122** | | |

### 1.2 现有架构

```
┌───────────────────────────────────────────────────────────────┐
│ Substance Painter 进程                                        │
│                                                               │
│  __init__.py                                                  │
│    └─> sp_sync.py (主控制器)                                    │
│          ├─> sp_sync_ui.py (UI)                               │
│          └─> sp_sync_ue.py (UE 编排)                           │
│                ├─> remote_execution.py (TCP/UDP 协议)           │
│                └─> [读取 6 个 .py 文件为字符串模板]               │
│                     ├─ import_textures_ue.py                  │
│                     ├─ material_ue.py                         │
│                     ├─ material_instance_ue.py                │
│                     ├─ create_material_and_connect_textures.py│
│                     ├─ import_mesh_ue.py                      │
│                     └─ sync_camera_ue.py                      │
│                                                               │
│                    ↓ 字符串 .replace() 替换占位符               │
│                    ↓ 通过 RemoteExecution 发送完整脚本           │
│                                                               │
├───── TCP ──────────────────────────────────────────────────────┤
│                                                               │
│ Unreal Engine 进程                                             │
│  接收字符串 → exec() 执行 → 返回结果                             │
└───────────────────────────────────────────────────────────────┘
```

### 1.3 核心问题

#### P0: 字符串模板注入

当前 6 个 UE 侧脚本作为字符串模板，通过 `.replace()` 拼接参数后整体发送执行：

```python
# 当前方式 — 字符串拼接 (sp_sync_ue.py)
current_to_ue_code = self._to_ue_code
current_to_ue_code = current_to_ue_code.replace('FOLDER_PATH', target_path)
current_to_ue_code = current_to_ue_code.replace('EXPORT_TEXTURE_PATH', exportFileListStr)
current_to_ue_code = current_to_ue_code.replace('UDIM_TYPE', self._udim_type_str)
```

**问题:**
- 占位符无类型约束，替换错误只在 UE 运行时才能发现
- 占位符可能与脚本中其他文本冲突（如 `PATH` 会匹配到 `FOLDER_PATH` 中的子串）
- 无法对参数进行校验
- 每次调用都发送完整脚本（~100 行），浪费带宽
- 拼接的 Python 代码无法获得 IDE 语法检查

#### P1: 隐式作用域依赖

`material_instance_ue.py` 中的 `get_material_instance()` 调用了 `create_material()`，但该函数定义在 `material_ue.py` 中。当前依赖"先发送 material_ue.py 注入作用域，再发送 material_instance_ue.py"的执行顺序。改变顺序会导致 `NameError`。

#### P2: sp_sync.py 上帝类

475 行包含 UI 配置、事件注册、导出编排、配置持久化、材质类型判断等多种职责。

---

## 二、重构方案：一次注入 + JSON 参数化调用

### 2.1 核心思路

```
┌ 连接建立时 ──────────────────────────────────────────────────┐
│ ExecuteFile: 注入所有 UE 侧函数定义（一次性，~400 行）         │
│   → 函数驻留在 UE 的 Python 全局作用域中                      │
└──────────────────────────────────────────────────────────────┘
         ↓ 后续每次操作
┌──────────────────────────────────────────────────────────────┐
│ EvaluateStatement: 只发送参数化的函数调用（一行）              │
│   → import_textures(folder_path="/Game/...", files=[...])    │
└──────────────────────────────────────────────────────────────┘
```

**对比变化:**

| 维度 | 重构前 | 重构后 |
|------|--------|--------|
| 每次发送内容 | 完整脚本 + 嵌入参数 (~100行) | 一行函数调用 + JSON 参数 |
| 参数传递 | `.replace()` 字符串替换 | `json.dumps()` 序列化 |
| 函数注入时机 | 每次操作都注入 | 连接建立时一次注入 |
| 作用域管理 | 隐式（依赖发送顺序） | 显式（统一 bootstrap） |
| 部署要求 | 无 (零侵入) | 无 (零侵入，保持不变) |
| UE 多项目兼容 | ✅ | ✅ (保持不变) |

### 2.2 不变部分

以下模块**不做改动**：

| 模块 | 原因 |
|------|------|
| `remote_execution.py` | Epic 官方代码，稳定可靠，不应修改 |
| `sp_sync_ui.py` / `sp_sync_ui.ui` | UI 定义独立，不涉及架构问题 |
| `__init__.py` | 入口简单，无需修改 |

---

## 三、分阶段实施计划

### 阶段一：抽离纯逻辑 + 添加单元测试

> 风险: ⭐ 低 | 改动范围: 新增文件 + 小幅提取

#### 3.1.1 创建纯逻辑工具模块 `utils.py`

从各文件中抽离可独立测试的纯函数：

```python
# utils.py — 新增文件，纯逻辑，无外部依赖

import json
from typing import List, Tuple


def sp_to_unreal_rotation(x: float, y: float, z: float, 
                          force_front_x_axis: bool) -> Tuple[float, float, float]:
    """
    从 sync_camera_ue.py 抽离的坐标转换算法。
    返回 (pitch, yaw, roll)。
    """
    ...


def determine_material_type(channels: List[str]) -> str:
    """
    从 sp_sync.py._get_texture_set_material_type() 抽离。
    输入通道名列表，输出 "opaque" | "masked" | "translucency"。
    """
    material_type = "opaque"
    for channel in channels:
        if channel == "Opacity":
            material_type = "masked"
        if channel == "Translucency":
            material_type = "translucency"
    return material_type


def build_texture_names(mesh_name: str, material_name: str) -> dict:
    """
    从 create_material_and_connect_textures.py 抽离的纹理命名规则。
    """
    base = f"T_{mesh_name}_{material_name}"
    return {
        "bco": f"{base}_BCO",
        "mras": f"{base}_MRAS",
        "n": f"{base}_N",
        "es": f"{base}_ES",
    }


def validate_content_path(path: str) -> bool:
    """验证路径包含 Content 目录。"""
    return "Content" in path


def filter_udim_paths(paths: List[str]) -> List[str]:
    """UDIM 过滤：只保留 1001 tile。"""
    return [p for p in paths if "1001" in p]


def serialize_ue_params(**kwargs) -> str:
    """将参数序列化为 JSON 字符串，用于远程调用。"""
    return json.dumps(kwargs, ensure_ascii=False)


def extract_mesh_name(mesh_path: str) -> str:
    """从完整路径提取网格名（不含扩展名）。"""
    name_with_ext = mesh_path[mesh_path.rfind("/") + 1:]
    return name_with_ext[:name_with_ext.rfind(".")]
```

#### 3.1.2 创建单元测试 `tests/test_utils.py`

```python
# tests/test_utils.py

import pytest
from utils import (
    determine_material_type,
    build_texture_names,
    validate_content_path,
    filter_udim_paths,
    extract_mesh_name,
)


class TestDetermineMaterialType:
    def test_opaque_no_special_channels(self):
        assert determine_material_type(["BaseColor", "Normal"]) == "opaque"

    def test_masked_with_opacity(self):
        assert determine_material_type(["BaseColor", "Opacity"]) == "masked"

    def test_translucency_overrides_opacity(self):
        assert determine_material_type(["Opacity", "Translucency"]) == "translucency"


class TestBuildTextureNames:
    def test_standard_naming(self):
        result = build_texture_names("Chair", "Wood")
        assert result["bco"] == "T_Chair_Wood_BCO"
        assert result["n"] == "T_Chair_Wood_N"


class TestFilterUdimPaths:
    def test_keeps_only_1001(self):
        paths = ["tex_1001.exr", "tex_1002.exr", "tex_1003.exr"]
        assert filter_udim_paths(paths) == ["tex_1001.exr"]


class TestExtractMeshName:
    def test_standard_path(self):
        assert extract_mesh_name("/Game/Meshes/Chair.fbx") == "Chair"
```

#### 3.1.3 此阶段改动清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 新增 | `utils.py` | 纯逻辑函数，从各模块抽离 |
| 新增 | `tests/test_utils.py` | 单元测试 |
| 微调 | `sp_sync.py` | `_get_texture_set_material_type()` 内部调用 `utils.determine_material_type()` |
| 微调 | `sp_sync_ue.py` | 路径提取调用 `utils.extract_mesh_name()` |

**人工测试需求**: 最小 — 纯提取，不改变任何逻辑流

---

### 阶段二：UE 侧脚本参数化改造

> 风险: ⭐⭐⭐ 中 | 改动范围: 6 个 UE 侧脚本 + sp_sync_ue.py

#### 3.2.1 UE 侧脚本改造原则

**改造前** (以 `import_textures_ue.py` 为例):
```python
# 占位符直接嵌在代码中
paths = [
EXPORT_TEXTURE_PATH
]
folder_path = 'FOLDER_PATH'
udim_type = UDIM_TYPE

def import_textures():
    # ... 使用上面的全局变量 ...

import_textures()
```

**改造后:**
```python
# 纯函数定义，不包含任何占位符，不自动执行
import json

def import_textures(params_json: str):
    params = json.loads(params_json)
    folder_path = params["folder_path"]
    paths = params["files"]
    udim_type = params["udim"]
    # ... 原有逻辑不变 ...
```

#### 3.2.2 每个 UE 侧脚本的改造规格

##### `import_textures_ue.py`

| 项目 | 改造前 | 改造后 |
|------|--------|--------|
| 占位符 | `FOLDER_PATH`, `EXPORT_TEXTURE_PATH`, `UDIM_TYPE` | 无 |
| 入口 | 全局代码自动执行 | `def import_textures(params_json: str)` |
| 参数 | 字符串替换嵌入 | JSON: `{"folder_path": str, "files": [str], "udim": bool}` |

##### `material_ue.py`

| 项目 | 改造前 | 改造后 |
|------|--------|--------|
| 占位符 | 无（纯函数定义） | 无 |
| 入口 | `create_material(path, bco_path, ...)` | 保持不变 — 已是参数化函数 |
| 说明 | 此文件无需改造，只需纳入统一 bootstrap |

##### `material_instance_ue.py`

| 项目 | 改造前 | 改造后 |
|------|--------|--------|
| 占位符 | 无 | 无 |
| 入口 | `create_material_instance()`, `get_material_instance()` | 保持不变 |
| 隐式依赖 | 需要 `material_ue.py` 已在作用域 | 通过统一 bootstrap 解决 |

##### `create_material_and_connect_textures.py`

| 项目 | 改造前 | 改造后 |
|------|--------|--------|
| 占位符 | `TARGET_PATH`, `MESH_NAME`, `MATERIAL_NAME_TYPES`, `UDIM_TYPE` | 无 |
| 入口 | 全局代码 + `create_material_and_connect_texture()` | `def create_material_and_connect_textures(params_json: str)` |
| 参数 | 字符串替换 | JSON: `{"target_path": str, "mesh_name": str, "material_types": [{"name": str, "type": str}], "udim": bool}` |

##### `import_mesh_ue.py`

| 项目 | 改造前 | 改造后 |
|------|--------|--------|
| 占位符 | 无（通过函数调用字符串传参） | 无 |
| 入口 | `import_mesh_and_swap(path, target, name, ...)` | `def import_mesh_and_swap(params_json: str)` |
| 参数 | 6 个位置参数通过字符串拼接 | JSON: `{"path": str, "target": str, "name": str, "udim": bool, "scale": float, "force_front_x_axis": bool}` |

##### `sync_camera_ue.py`

| 项目 | 改造前 | 改造后 |
|------|--------|--------|
| 占位符 | 无 | 无 |
| 入口 | `init_sync_camera()`, `sync_camera(px,py,pz,...)`, `exit_sync_camera()` | 保持不变 — 相机同步是高频调用 (~30fps)，JSON 开销不值得 |
| 说明 | 此文件保持参数直传方式，只纳入统一 bootstrap |

#### 3.2.3 SP 侧 `sp_sync_ue.py` 改造

##### 新增: 连接 bootstrap 机制

```python
class ue_sync:
    def __init__(self, ui, main_widget):
        # ... 原有初始化 ...
        self._bootstrap_injected = False
        
        # 读取所有 UE 侧脚本（用于一次性注入）
        self._ue_scripts = self._load_ue_scripts()
    
    def _load_ue_scripts(self) -> str:
        """将所有 UE 侧脚本合并为一个 bootstrap 脚本。"""
        root = os.path.dirname(__file__)
        scripts = [
            "import_textures_ue.py",
            "sync_camera_ue.py",
            "material_ue.py",
            "material_instance_ue.py",
            "create_material_and_connect_textures.py",
            "import_mesh_ue.py",
        ]
        combined = "import json\n"
        for script in scripts:
            with open(os.path.join(root, script), "r") as f:
                combined += f"\n# === {script} ===\n"
                combined += f.read()
                combined += "\n"
        return combined
    
    def _ensure_bootstrap(self):
        """确保 UE 侧函数已注入。每次连接后调用一次。"""
        if not self._bootstrap_injected:
            self._ue_sync_remote.add_command(
                ue_sync_command(
                    code=self._ue_scripts,
                    error_fun=self.ue_sync_textures_error,
                    call_back_fun=self._on_bootstrap_done,
                    model='ExecuteFile'
                ))
    
    def _on_bootstrap_done(self):
        self._bootstrap_injected = True
```

##### 改造: 调用方式

```python
# 改造前
def sync_ue_textures(self, target_path, export_file_list, callback=None):
    current_to_ue_code = self._to_ue_code
    current_to_ue_code = current_to_ue_code.replace('FOLDER_PATH', target_path)
    exportFileListStr = ""
    for file in export_file_list:
        exportFileListStr += "  '" + file + "',\n"
    current_to_ue_code = current_to_ue_code.replace('EXPORT_TEXTURE_PATH', exportFileListStr)
    current_to_ue_code = current_to_ue_code.replace('UDIM_TYPE', self._udim_type_str)
    self._ue_sync_remote.add_command(ue_sync_command(current_to_ue_code, ...))

# 改造后
def sync_ue_textures(self, target_path, export_file_list, callback=None):
    self._ensure_bootstrap()
    params = json.dumps({
        "folder_path": target_path,
        "files": export_file_list,
        "udim": self._udim_type
    })
    call = f"import_textures('{params}')"
    self._ue_sync_remote.add_command(
        ue_sync_command(call, self.ue_sync_textures_error, callback, 'EvaluateStatement'))
```

```python
# 改造前
def ue_import_mesh(self, target_path, mesh_path, callback):
    current_to_ue_code = "import_mesh_and_swap('PATH', 'TARGET', 'NAME', UDMI_TYPE, SCALE, FORCE_FRONT_X_AXIS)"
    current_to_ue_code = current_to_ue_code.replace('PATH', mesh_path)
    current_to_ue_code = current_to_ue_code.replace('TARGET', target_path)
    # ... 更多 replace ...

# 改造后
def ue_import_mesh(self, target_path, mesh_path, callback):
    self._ensure_bootstrap()
    params = json.dumps({
        "path": mesh_path,
        "target": target_path,
        "name": extract_mesh_name(mesh_path),
        "udim": self._udim_type,
        "scale": self._mesh_scale,
        "force_front_x_axis": self._force_front_x_axis
    })
    call = f"import_mesh_and_swap('{params}')"
    self._ue_sync_remote.add_command(
        ue_sync_command(call, self.ue_sync_textures_error, callback, 'EvaluateStatement'))
```

#### 3.2.4 相机同步保持高频直传

相机同步 ~30fps，每帧一次调用。JSON 解析的开销不值得。保持现有的直接参数传递：

```python
# 不变 — sync_camera(px, py, pz, rx, ry, rz, fov, scale, force_front_x_axis) 
sync_str = f"sync_camera({px},{py},{pz},{rx},{ry},{rz},{fov},{scale},{force})"
```

#### 3.2.5 此阶段改动清单

| 操作 | 文件 | 说明 |
|------|------|------|
| **重构** | `sp_sync_ue.py` | 新增 bootstrap 机制；6 个调用方法改为 JSON 参数化 |
| **重构** | `import_textures_ue.py` | 去掉占位符，改为 `def import_textures(params_json)` |
| **重构** | `create_material_and_connect_textures.py` | 去掉占位符，改为参数化函数 |
| **重构** | `import_mesh_ue.py` | `import_mesh_and_swap` 改为接收 JSON 参数 |
| 微调 | `material_ue.py` | 无需改动（已是参数化函数） |
| 微调 | `material_instance_ue.py` | 无需改动（已是参数化函数） |
| 微调 | `sync_camera_ue.py` | 无需改动（保持直传） |

**人工测试需求**: **中等** — 需完整测试以下矩阵：

| 测试项 | 变体 |
|--------|------|
| 纹理同步 | 非 UDIM / UDIM |
| 材质创建 | Opaque / Masked / Translucent × 含/不含 Emissive |
| 网格导入 | 含/不含 Force Front X Axis |
| 相机同步 | 开启/关闭 |

---

### 阶段三：sp_sync.py 职责拆分

> 风险: ⭐⭐ 低中 | 改动范围: sp_sync.py 拆为 3 个类

#### 3.3.1 拆分方案

```
sp_sync.py (475 行，上帝类)
   ↓ 拆分为
├── sp_sync.py         (~150 行) — 控制器：事件注册、UI绑定（胶水层）
├── sp_sync_config.py  (~100 行) — 配置管理：_save_data / _load_data / 路径校验
└── sp_sync_export.py  (~200 行) — 导出编排：_sync_button_click / _export_end_event / 预设管理
```

#### 3.3.2 类职责划分

##### `SPSyncConfig` — 配置持久化

```python
class SPSyncConfig:
    """管理项目级配置的持久化和读取。"""
    
    def save(self, ui_state: dict) -> None:
        """将 UI 状态写入 SP 项目元数据。"""
    
    def load(self) -> dict:
        """从 SP 项目元数据读取配置。"""
    
    @staticmethod
    def validate_export_path(path: str) -> bool:
        """校验导出路径是否在 Content/ 目录下。"""
```

##### `SPSyncExporter` — 导出编排

```python
class SPSyncExporter:
    """管理导出流程和预设。"""
    
    def export_textures(self, set_names: List[str]) -> None:
        """触发纹理导出。"""
    
    def export_textures_and_mesh(self, set_names: List[str]) -> None:
        """触发纹理+网格导出。"""
    
    def on_export_end(self, export_data) -> None:
        """导出完成回调，触发 UE 同步。"""
    
    def load_presets(self) -> None:
        """加载导出预设列表。"""
```

##### `sp_sync` — 控制器 (精简)

```python
class sp_sync:
    """插件入口，只负责事件注册和 UI 绑定。"""
    
    def __init__(self):
        self._config = SPSyncConfig()
        self._exporter = SPSyncExporter(self._config, self._ue_sync)
        self._config_ui()
        self._register_events()
```

#### 3.3.3 此阶段改动清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 新增 | `sp_sync_config.py` | 配置管理类 |
| 新增 | `sp_sync_export.py` | 导出编排类 |
| **重构** | `sp_sync.py` | 精简为控制器 |

**人工测试需求**: **中等** — 配置保存/读取 + 完整导出流程回归

---

## 四、文件结构对比

### 重构前

```
SPsync/
├── __init__.py
├── sp_sync.py                                  # 475 行上帝类
├── sp_sync_ui.py
├── sp_sync_ue.py                               # 字符串模板替换
├── remote_execution.py
├── import_textures_ue.py                       # 含占位符模板
├── material_ue.py
├── material_instance_ue.py
├── create_material_and_connect_textures.py     # 含占位符模板
├── import_mesh_ue.py                           # 含占位符模板
└── sync_camera_ue.py
```

### 重构后

```
SPsync/
├── __init__.py                                 # 不变
├── sp_sync.py                                  # 精简为控制器 (~150 行)
├── sp_sync_config.py                           # 新增: 配置管理
├── sp_sync_export.py                           # 新增: 导出编排
├── sp_sync_ui.py                               # 不变
├── sp_sync_ue.py                               # 重构: bootstrap + JSON 调用
├── remote_execution.py                         # 不变
├── utils.py                                    # 新增: 纯逻辑工具函数
├── import_textures_ue.py                       # 重构: 参数化函数
├── material_ue.py                              # 不变
├── material_instance_ue.py                     # 不变
├── create_material_and_connect_textures.py     # 重构: 参数化函数
├── import_mesh_ue.py                           # 重构: 参数化函数
├── sync_camera_ue.py                           # 不变
└── tests/
    └── test_utils.py                           # 新增: 单元测试
```

---

## 五、人工测试矩阵

每个阶段完成后，需按以下矩阵执行人工验收测试：

### 基础功能

| # | 测试项 | 前置条件 | 预期结果 |
|---|--------|---------|---------|
| 1 | 插件加载 | 启动 SP | SPsync 面板出现在侧栏 |
| 2 | 项目打开 | 打开 SP 项目 | 预设列表加载，配置恢复 |
| 3 | 项目关闭 | 关闭 SP 项目 | UI 状态清空 |
| 4 | 配置保存 | 修改路径/预设后关闭重开项目 | 配置正确恢复 |

### 纹理同步

| # | 测试项 | UDIM | 预期结果 |
|---|--------|------|---------|
| 5 | SYNC 按钮 (非UDIM) | ❌ | 纹理出现在 UE Content Browser |
| 6 | SYNC 按钮 (UDIM) | ✅ | 仅 1001 tile 导入 |
| 7 | Auto Export | ❌ | 编辑后自动导出并同步到 UE |

### 材质创建

| # | 测试项 | 材质类型 | Emissive | 预期结果 |
|---|--------|---------|----------|---------|
| 8 | 创建 Opaque 材质 | Opaque | ❌ | UE 材质实例正确创建 |
| 9 | 创建 Masked 材质 | Masked | ❌ | Blend Mode = Masked |
| 10 | 创建 Translucent 材质 | Translucent | ❌ | Blend Mode = Translucent |
| 11 | 含 Emissive 的材质 | Opaque | ✅ | Emissive 纹理连接，强度参数存在 |
| 12 | UDIM 材质创建 | (UDIM) | ❌ | Virtual Texture 采样器类型 |

### 网格导入

| # | 测试项 | Force X | 预期结果 |
|---|--------|---------|---------|
| 13 | SYNC(Mesh) 标准 | ❌ | 网格导入 + 材质分配 + 场景放置 |
| 14 | SYNC(Mesh) Force X | ✅ | 旋转 -270° (X轴) |
| 15 | 网格缩放 | - | Scale 参数生效 |

### 相机同步

| # | 测试项 | 预期结果 |
|---|--------|---------|
| 16 | View Sync 开启 | UE 视口跟随 SP 相机 |
| 17 | View Sync 关闭 | 停止同步，UE 相机不再移动 |

### 异常场景

| # | 测试项 | 预期结果 |
|---|--------|---------|
| 18 | UE 未启动时 SYNC | 弹出错误提示 |
| 19 | 路径不含 Content/ | 弹出警告 |
| 20 | 非 SPSYNCDefault 预设 + 创建材质 | 警告并取消勾选 |

---

## 六、风险缓解措施

| 风险 | 缓解措施 |
|------|---------|
| Bootstrap 注入失败（UE 连接中断后重连） | `_bootstrap_injected` 标志在连接断开时重置为 `False`；`_ensure_bootstrap()` 每次操作前检查 |
| JSON 参数包含特殊字符（路径中的引号/反斜杠） | 使用 `json.dumps()` 自动转义；UE 侧用 `json.loads()` 解析 |
| Bootstrap 代码中函数名冲突 | 所有 UE 侧函数加 `spsync_` 前缀（可选，视实际需要） |
| 阶段间回退 | 每个阶段完成后打 Git tag，人工测试不通过可回退 |
| PySide2/6 兼容性 | 重构不涉及 UI 层，无新增风险 |

---

## 七、不建议做的事

| 事项 | 原因 |
|------|------|
| 重构 `remote_execution.py` | Epic 官方代码，稳定且无需改 |
| 手动重构 `sp_sync_ui.py` | 应从 `.ui` 文件生成，保持与 Qt Designer 同步 |
| 引入 asyncio | SP 的 Python 环境不一定支持，且当前 threading 模型可控 |
| 添加 UE 侧部署步骤 | 方案 A 的核心优势就是零 UE 侧部署 |
| 一次性全部重构 | 必须分阶段，每阶段人工验收后再推进 |
