# SP → UE 贴图回传（Round-Trip Sync）调研与设计

> 创建日期: 2026-03-25  
> 状态: 调研完成 → 待实现  
> 前置: Phase 4 (Grayscale Conversion Filter) 完成

---

## 1. 目标

实现 **UE → SP → UE** 贴图往返更新流程：

1. 从 UE 发送材质信息到 SP 时（`receive_from_ue`），将**材质定义 + UE 贴图资产路径**写入 SP 项目自定义元数据
2. 用户在 SP 编辑贴图后点击 **SYNC**，插件自动根据存储的材质定义**动态生成导出配置**（匹配 UE 原始贴图格式/打包方式）
3. 导出到临时目录，然后**推送到 UE 刷新原有贴图资产**

### 与现有流程的关系

| 流程 | 方向 | 触发 | 输出 |
|------|------|------|------|
| 现有：SP → UE（新建） | 单向 | 手选预设 + SYNC | 按 SPSYNCDefault 格式导出 → 在 UE 目标目录新建贴图/材质 |
| **新增：SP → UE（回传）** | 往返 | 自动检测 + SYNC | 按 UE 原始格式导出 → 覆盖 UE 原贴图路径 |

关键区别：回传模式**不创建新材质**，只刷新已有贴图。导出格式由 UE 传入的材质定义决定，不依赖用户选择的导出预设。

---

## 2. 可行性分析

### 2.1 SP Project Metadata 存储

**API**: `substance_painter.project.Metadata(context_name)`

| 方法 | 说明 | 验证状态 |
|------|------|---------|
| `metadata.set(key, value)` | 写入任意 JSON 可序列化值 | ✅ 已用于 string/number/bool（`sp_sync_config.py`） |
| `metadata.get(key)` | 读取值 | ✅ 已用 |
| `metadata.list()` | 列出所有 key | ✅ 已用 |

**待验证**: `set()` 是否支持嵌套 dict/list（如完整的 UE 材质定义 JSON）。SP 内部以 JSON 存储项目元数据，理论上支持。

**风险**: ⭐ 低。即使不写支持复杂对象，可以 `json.dumps()` 为字符串存储，`json.loads()` 读取。

**结论**: ✅ 可行。

### 2.2 动态导出配置生成

**API**: `substance_painter.export.export_project_textures(config)`

config 结构支持内联预设定义：

```python
config = {
    "exportPath": "/tmp/sp_sync_temp",
    "exportShaderParams": False,
    "defaultExportPreset": "RoundTrip",
    "exportPresets": [{
        "name": "RoundTrip",
        "maps": [  # 动态生成的 output maps
            {
                "fileName": "T_Body_BaseColor",
                "channels": [
                    {"destChannel": "R", "srcChannel": "R", "srcMapType": "documentMap", "srcMapName": "Base color"},
                    {"destChannel": "G", "srcChannel": "G", "srcMapType": "documentMap", "srcMapName": "Base color"},
                    {"destChannel": "B", "srcChannel": "B", "srcMapType": "documentMap", "srcMapName": "Base color"},
                ]
            },
            {
                "fileName": "T_Body_MRO",
                "channels": [
                    {"destChannel": "R", "srcChannel": "R", "srcMapType": "documentMap", "srcMapName": "Metallic"},
                    {"destChannel": "G", "srcChannel": "R", "srcMapType": "documentMap", "srcMapName": "Roughness"},
                    {"destChannel": "B", "srcChannel": "R", "srcMapType": "documentMap", "srcMapName": "Ambient occlusion"},
                ]
            }
        ]
    }],
    "exportList": [{"rootPath": "Body"}],
    "exportParameters": [{"parameters": {"fileFormat": "tga", "bitDepth": "8"}}]
}
```

**关键技术点**:

| 项目 | 说明 | 状态 |
|------|------|------|
| 内联预设定义 | `exportPresets` 可包含完全自定义的 maps | ✅ SP 官方文档支持 |
| 多通道打包 | 单个 map 可包含多个 channels，实现 MRO 重组 | ✅ SPSYNCDefault 的 _MRAS 已使用 |
| srcMapName 命名 | SP 内部通道名可能是 "Base color"（带空格）或 "BaseColor" | ⚠️ 需探测验证 |
| 文件名控制 | `fileName` 支持字面值和 `$textureSet` 等变量 | ✅ |
| per-TextureSet 导出 | `exportList` 可指定特定 TextureSet | ✅ |

**待验证**: 
1. `srcMapName` 的确切格式（"Base color" vs "BaseColor" vs "base_color"）
2. 灰度通道（Metallic/Roughness 等）作为 src 时，`srcChannel` 应为 "R" 还是 "L"
3. AO 通道的 srcMapName（"AO" vs "Ambient occlusion" vs "AmbientOcclusion"）

**风险**: ⭐⭐ 低中。核心 API 已有使用先例，需探测确认通道名格式。

**结论**: ✅ 可行。

### 2.3 UE 端贴图刷新

**现有能力**: `import_textures_ue.py` 的 `import_textures()` 已支持覆盖式重导入：

```python
if asset_library.do_assets_exist([file_path]):
    # 保留 sRGB / compression / lod_group 设置
    current_texture = asset_library.load_asset(file_path)
    srgb = current_texture.get_editor_property("srgb")
    # ... 重导入后恢复设置 ...
```

**需要扩展**: 当前 `import_textures()` 将所有文件导入同一目录。回传模式需要**按原路径逐个刷新**。

方案：新增 `refresh_textures()` 函数（不修改现有函数），接受每个文件的目标 UE 路径：

```python
def refresh_textures(params_json):
    """根据存储的 UE 路径刷新贴图资产。"""
    params = json.loads(params_json)
    for item in params["textures"]:
        local_path = item["local_path"]
        ue_folder = item["ue_folder"]       # e.g. "/Game/Textures"
        ue_name = item["ue_name"]           # e.g. "T_Body_BaseColor"
        ue_asset_path = ue_folder + "/" + ue_name
        
        if asset_library.do_assets_exist([ue_asset_path]):
            # 保留原 sRGB/compression 设置并重导入
            ...
```

**风险**: ⭐ 低。现有代码已覆盖重导入逻辑，只需支持多路径。

**结论**: ✅ 可行。

---

## 3. 数据架构

### 3.1 Metadata 存储 Schema

使用 `substance_painter.project.Metadata("sp_sync")` 存储，key = `"ue_material_defs"`。

```jsonc
{
  // 网格信息
  "static_mesh": "SM_Body",
  "static_mesh_path": "/Game/Meshes/SM_Body",
  
  // 材质列表（每个材质对应一个 TextureSet）
  "materials": [
    {
      "material_name": "MI_Body",
      "material_slot_name": "Body",
      "config_profile": "Prop",
      // parameter_bindings: 纯 suffix → MI 参数名绑定
      "parameter_bindings": {
        "D": "BaseColor_Texture",
        "N": "Normal_Texture",
        "MRO": "Packed_Texture"
      },
      // texture_definitions: 通道打包定义（来自 config processing 段）
      "texture_definitions": [
        {
          "suffix": "MRO",
          "name": "Packed_MRO",
          "channels": {
            "R": {"from": "Metallic", "ch": "R"},
            "G": {"from": "Roughness", "ch": "R"},
            "B": {"from": "AmbientOcclusion", "ch": "R"}
          }
        }
      ],
      // 贴图列表（含 UE 资产路径，用于回传定位）
      "textures": [
        {
          "texture_property_name": "BaseColor_Texture",
          "texture_path": "/Game/Textures/T_Body_BaseColor",
          "texture_name": "T_Body_BaseColor"
        },
        {
          "texture_property_name": "Normal_Texture",
          "texture_path": "/Game/Textures/T_Body_Normal",
          "texture_name": "T_Body_Normal"
        },
        {
          "texture_property_name": "Packed_Texture",
          "texture_path": "/Game/Textures/T_Body_MRO",
          "texture_name": "T_Body_MRO"
        }
      ]
    }
  ]
}
```

写入时机：`_on_project_ready()` 处理完贴图后。  
读取时机：SYNC 按钮触发导出前。

### 3.2 导出映射算法

从存储的 `parameter_bindings` + `texture_definitions` + `textures` 逆向生成 SP 导出 maps：

```
输入: parameter_bindings = {"D": "BaseColor_Texture", "MRO": "Packed_Texture", "N": "Normal_Texture"}
       texture_definitions = [{"suffix": "MRO", "channels": {"R": {"from": "Metallic"}, "G": {"from": "Roughness"}, "B": {"from": "AmbientOcclusion"}}}]
       textures = [{prop: "BaseColor_Texture", name: "T_Body_BaseColor"}, ...]

步骤:
  1. 遍历 bindings + texture_definitions，检测打包关系：
     BaseColor_Texture → [("D", None)]               # 无 texture_definitions 匹配 = 完整通道
     Normal_Texture    → [("N", None)]
     Packed_Texture    → MRO suffix → texture_definitions channels → 多源 packed

  2. 对每个分组，查找对应 texture_name：
     BaseColor_Texture → "T_Body_BaseColor"
     Packed_Texture    → "T_Body_MRO"

  3. 生成 export map：
     T_Body_BaseColor: channels=[{dest:"R", src:"R", map:"basecolor"}, ...]
     T_Body_MRO:       channels=[{dest:"R", src:"L", map:"metallic"}, {dest:"G", src:"L", map:"roughness"}, {dest:"B", src:"L", map:"ambientOcclusion"}]
     T_Body_Normal:    channels=[{dest:"R", src:"R", map:"Normal_DirectX"}, ...]

输出: SP export config 的 maps 数组
```

> **向后兼容**: 旧格式 `.R/.G/.B` 后缀（如 `"M": "Packed_Texture.R"`）仍然可以被正确解析。

**通道分类规则**:

| 类型 | SP 通道 | 导出方式 | destChannel |
|------|---------|---------|-------------|
| 颜色通道 | BaseColor, Normal, Emissive | 逐 R/G/B 输出 | R, G, B |
| 灰度通道 | Metallic, Roughness, AO, Height, Specular, Opacity | 读 R 分量 | 由打包位置决定 |
| 打包通道 | 多个灰度通道 → 同一文件 | 每通道占一个 dest | R/G/B/A |

### 3.3 UE 刷新参数格式

导出完成后发送到 UE 的 JSON：

```json
{
  "textures": [
    {
      "local_path": "C:/temp/sp_sync_temp/T_Body_BaseColor.tga",
      "ue_folder": "/Game/Textures",
      "ue_name": "T_Body_BaseColor"
    },
    {
      "local_path": "C:/temp/sp_sync_temp/T_Body_MRO.tga",
      "ue_folder": "/Game/Textures", 
      "ue_name": "T_Body_MRO"
    }
  ]
}
```

---

## 4. 实现路径

### Phase 5A: Metadata 存储（SP 侧）

**文件**: `sp_receive.py`

在 `_on_project_ready()` 末尾，处理完贴图后将 UE 数据存入 SP 项目元数据：

```python
# _on_project_ready() 末尾
import substance_painter.project
metadata = substance_painter.project.Metadata("sp_sync")
# 只存储回传必需的字段（去掉 texture_export_path 等临时路径）
roundtrip_data = _build_roundtrip_metadata(data)
metadata.set("ue_material_defs", json.dumps(roundtrip_data))
```

新增纯逻辑函数 `_build_roundtrip_metadata(data)` 提取需要持久化的字段。

**测试**: 
- 单元测试: `_build_roundtrip_metadata()` 输入输出
- 探测脚本: 验证 Metadata.set/get 对 JSON 字符串的往返一致性

### Phase 5B: 动态导出配置生成器（纯逻辑）

**文件**: `sp_channel_map.py`（新增函数）

```python
def build_roundtrip_export_maps(
    material: dict,
) -> list[dict]:
    """从 UE 材质定义生成 SP 导出 maps 配置。
    
    根据 parameter_bindings + texture_definitions 推导打包关系。
    支持新格式（texture_definitions）和旧格式（.R/.G/.B 后缀）。
    """
```

核心算法：
1. 遍历 `parameter_bindings`，结合 `texture_definitions` 推导打包关系
2. 匹配 `material["textures"]` 获取文件名
3. 按上面 §3.2 的规则生成 channels 数组

```python
def build_roundtrip_export_config(
    ue_defs: dict,
    export_path: str,
    file_format: str = "tga",
    bit_depth: str = "8",
) -> dict:
    """从完整 UE 定义生成 SP export_project_textures() 可用的 config。"""
```

**测试**: 纯逻辑函数，可完整 pytest。

### Phase 5C: UE 刷新脚本

**文件**: `import_textures_ue.py`（新增函数，不修改现有函数）

```python
def refresh_textures(params_json):
    """根据 UE 原始路径刷新贴图资产。保留 sRGB/compression 等原有设置。"""
```

纳入 bootstrap 加载链，通过 `sp_sync_ue.py` 调用。

**文件**: `sp_sync_ue.py`（新增方法）

```python
def sync_ue_refresh_textures(self, refresh_items: list[dict], callback: callable = None):
    """发送贴图刷新命令到 UE。"""
```

### Phase 5D: SYNC 按钮集成

**文件**: `sp_sync_export.py`

修改 `sync_textures()` 和 `export_end_event()`：

```python
def sync_textures(self):
    # 检查是否有 UE 回传定义
    ue_defs = self._load_ue_material_defs()
    if ue_defs is not None:
        self._sync_roundtrip(ue_defs)
    else:
        self._sync_preset()  # 现有流程
```

回传流程：
1. 读取 metadata 中的 `ue_material_defs`
2. 调用 `build_roundtrip_export_config()` 生成配置
3. `export_project_textures(config)` 导出到 temp
4. `export_end_event` 中检测回传模式 → 调用 `sync_ue_refresh_textures()` 而非 `sync_ue_textures()`

### Phase 5E: 探测验证 + 集成测试

**探测脚本** (在 SP Python Console 执行):
1. Metadata 复杂对象存储验证
2. export 导出 srcMapName 通道名格式确认
3. per-TextureSet 导出验证

**E2E 测试**:
1. UE 发送 MI → SP 接收并创建项目 → 验证 metadata 已写入
2. 在 SP 编辑贴图 → SYNC → 验证导出文件格式正确
3. 验证 UE 贴图资产已刷新（sRGB/compression 保持）

---

## 5. 待验证项（需探测脚本）

| # | 验证项 | 优先级 | 说明 |
|---|--------|--------|------|
| P1 | Metadata 存储 JSON 字符串长度限制 | 高 | 多材质场景下 JSON 可能较长 |
| P2 | `srcMapName` 通道名格式 | 高 | "Base color" vs "BaseColor" — 直接影响导出正确性 |
| P3 | 灰度通道 srcChannel | 中 | Metallic 等单通道，srcChannel 用 "R" 还是 "L" |
| P4 | `export_project_textures` 内联预设 | 中 | 确认不注册资源预设也能使用自定义 maps |
| P5 | per-TextureSet 文件命名 | 中 | `fileName` 不含 `$textureSet` 时，多 Set 导出是否冲突 |

**建议**: 先执行 P2 探测脚本确认通道名格式，再实现 Phase 5B。

### 探测脚本草案（P2: srcMapName 格式）

```python
"""probe_export_channel_names.py — 探测 SP 导出时 srcMapName 的正确格式"""
import substance_painter.export as export
import substance_painter.textureset as ts

# 获取当前活动预设的 maps 定义
presets = export.list_resource_export_presets()
for p in presets:
    if "SPSYNCDefault" in p.resource_id.name:
        maps = p.list_output_maps()
        print(f"=== Preset: {p.resource_id.name} ===")
        for m in maps:
            print(f"  Map: {m}")
        break

# 尝试最小化导出验证 srcMapName
all_sets = ts.all_texture_sets()
if all_sets:
    stack = all_sets[0].all_stacks()[0]
    channels = stack.all_channels()
    print(f"\n=== Stack channels ===")
    for ch_type, ch_info in channels.items():
        print(f"  ChannelType={ch_type}, name={ch_type.name}, value={ch_type.value}")
```

---

## 6. 风险与规避

| 风险 | 等级 | 规避 |
|------|------|------|
| Metadata 不支持复杂 JSON | 低 | fallback: `json.dumps()` 存为字符串 |
| srcMapName 格式不确定 | 中 | 先执行探测脚本，确认后硬编码映射表 |
| 多材质不同 bindings | 低 | 当前设计已按材质分组处理 |
| UE 贴图路径已变更 | 低 | 资产不存在时 fallback 到新建导入 |
| 导出文件格式不匹配 UE 期望 | 低 | 默认 tga 8bit，后续可从 UE 数据推断 |
| SP 项目未保存时 metadata 丢失 | — | SP 标准行为，非插件可控；文档提示用户保存 |

---

## 7. 文件变更总览

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `sp_receive.py` | 修改 | `_on_project_ready()` 末尾写入 metadata |
| `sp_channel_map.py` | 新增函数 | `build_roundtrip_export_maps()`, `build_roundtrip_export_config()` |
| `sp_sync_export.py` | 修改 | `sync_textures()` 添加回传模式检测 |
| `import_textures_ue.py` | 新增函数 | `refresh_textures()` |
| `sp_sync_ue.py` | 新增方法 | `sync_ue_refresh_textures()` |
| `tests/test_roundtrip.py` | 新增 | 纯逻辑函数测试 |

---

## 8. 实施顺序建议

```
5A (metadata 存储) ──→ 5B (导出生成器) ──→ 5C (UE 刷新) ──→ 5D (SYNC 集成) ──→ 5E (测试)
      │                      │                                      │
      └── 探测: P1           └── 探测: P2, P3, P4                   └── E2E
```

先完成 5A + 5B 的纯逻辑部分（可 pytest），再接入 SP API（需探测确认），最后集成。
