# 贴图尺寸控制 — 设计与实现

> 日期：2026-03-26  
> 状态：**M8 + M9 已完成（全管线验证通过，191 tests passed）**

---

## 1. 需求概要

在 `texture_definitions` 中为每张贴图定义 **最大尺寸**（横向 × 纵向，默认 1024×1024），流经整个管线：

| 环节 | 行为 |
|------|------|
| UE 导入贴图 | 若原始分辨率 > max，自动限制运行时分辨率 |
| UE → SP 发送 | 将 max_resolution 信息随数据传递给 SP |
| SP 创建项目 | `default_texture_resolution` 设置初始 TextureSet 分辨率 |
| SP 项目就绪后 | `TextureSet.set_resolution()` 按 config 动态调整 |
| SP 导出回 UE | `sizeLog2` + `filter.dataPaths` 控制导出尺寸 |
| 小于 max 时 | 所有环节保持原始尺寸不变 |

---

## 2. 配置格式设计

在 `texture_definitions[]` 每项中新增 `max_resolution`：

```jsonc
{
  "name": "Diffuse",
  "suffix": "D",
  // ... 现有字段 ...
  "max_resolution": 2048   // 单个 int（POT：256/512/1024/2048/4096），省略时不限制
}
```

- **类型**：`Optional[int]`（最初设计为 `{width, height}` 字典，实施中统一简化为 `int`）
- **默认值**：省略 `max_resolution` 时不限制分辨率（向后兼容）
- **POT 约束**：值必须为 2 的幂（SP `sizeLog2` 要求 log2 整数）
- **Clamp 范围**：SP 端 [128, 4096]（`_compute_default_resolution()` 和 `_compute_export_size_log2()` 统一 Clamp）

### 分辨率权威分离（M9）

`blueprint_get_size_x/y()` 返回运行时分辨率（受 `max_texture_size`/LOD 影响），而非源文件像素尺寸。解决方案：

1. `sp_bridge.py` 导出贴图到磁盘后调用 `update_texture_sizes_from_exports()` 用 PIL 读取实际文件尺寸
2. `texture_size = max(width, height)` 写入 UE→SP 数据包
3. SP 端 `_compute_default_resolution()` / `_compute_export_size_log2()` 使用 `texture_size` 并 Clamp [128, 4096]

---

## 3. UE 端 — 能力调研

### 3.1 `max_texture_size` 属性 ✅ 可行

`Texture2D` 暴露以下 Python 可写属性：

| 属性 | 类型 | 说明 |
|------|------|------|
| `max_texture_size` | int32 | 生成贴图最大分辨率上限。0 = 无限制。**单一值，限制最大维度** |

```python
texture.set_editor_property("max_texture_size", 1024)
```

- **优点**：仅一个值，最简单。引擎自动 clamp 长边到此值。
- **缺点**：宽高不独立控制。实际效果是 max(width, height) ≤ 该值。

### 3.2 `resize_during_build_x/y` 属性 ✅ 可行

| 属性 | 类型 | 说明 |
|------|------|------|
| `power_of_two_mode` | TexturePowerOfTwoSetting | 必须设为 `RESIZE_TO_SPECIFIC_RESOLUTION` |
| `resize_during_build_x` | int32 | Cook/Build 时目标宽度（0 = 保持原始） |
| `resize_during_build_y` | int32 | Cook/Build 时目标高度（0 = 保持原始） |

```python
from unreal import TexturePowerOfTwoSetting
texture.set_editor_property("power_of_two_mode",
    TexturePowerOfTwoSetting.RESIZE_TO_SPECIFIC_RESOLUTION)
texture.set_editor_property("resize_during_build_x", 1024)
texture.set_editor_property("resize_during_build_y", 1024)
```

- **优点**：宽高独立控制、精确缩放。
- **缺点**：强制缩放（不区分"大于才缩"），需要先读取原始尺寸做判断。

### 3.3 读取原始贴图尺寸 ⚠️ 运行时分辨率

```python
w = texture.blueprint_get_size_x()  # 或 get_size_x()
h = texture.blueprint_get_size_y()
```

> **注意（M9 发现）**：`blueprint_get_size_x/y()` 返回的是**运行时分辨率**，受 `max_texture_size` / LOD 设置影响。当 M8 设置了 `max_texture_size` 后，这些 API 可能返回被限制后的值（如 32×32），而非源文件的实际像素尺寸。
>
> **解决方案**：`update_texture_sizes_from_exports()` 在导出贴图到磁盘后，使用 PIL 读取导出文件的实际像素尺寸，作为 `texture_size` 的权威来源。

### 3.4 推荐方案：`max_texture_size`（简洁） + 导出后尺寸刷新

```python
def apply_max_resolution(texture, max_res):
    """设置 max_texture_size 限制运行时分辨率。"""
    if max_res and max_res > 0:
        texture.set_editor_property("max_texture_size", max_res)

def update_texture_sizes_from_exports(materials_data, export_dir):
    """导出后用 PIL 读取实际文件尺寸，覆盖 texture_size。"""
    from PIL import Image
    for mat in materials_data:
        for tex in mat.get("textures", []):
            filepath = os.path.join(export_dir, tex["filename"])
            if os.path.isfile(filepath):
                with Image.open(filepath) as img:
                    w, h = img.size
                    tex["texture_size"] = max(w, h)
```

- 对于宽高相同的常见场景（1024×1024、2048×2048）效果完美。
- 若后续需宽高不同缩放，升级到 `resize_during_build_x/y` 方案。

### 3.5 外部图像处理 ⚠️ 备选

| 方案 | 状态 | 说明 |
|------|------|------|
| Pillow (PIL) | ❌ 未安装 | UE 5.7 Python 3.11.8，pip 24.0 可用。需 `pip install Pillow` |
| UE FImageUtils | ❌ C++ only | 仅 C++ 可用，Python 不暴露 |
| OpenCV | ❌ 未安装 | 同 Pillow，需额外安装 |

**结论**：UE 原生属性已满足需求，无需安装外部库。

---

## 4. SP 端 — 能力调研

> **数据来源**：直接读取 SP Python API 源码  
> `C:\Program Files\Adobe\Adobe Substance 3D Painter\resources\python\modules\substance_painter\`

### 4.1 项目创建分辨率 ✅ 可控

`project.Settings` 支持 `default_texture_resolution` 参数：

```python
# 源自 substance_painter/project.py L258-274
settings = project.Settings(
    import_cameras=False,
    normal_map_format=project.NormalMapFormat.DirectX,
    default_texture_resolution=1024,  # ← 可在创建时指定默认分辨率
)
project.create(mesh_path, settings=settings)
```

**当前 SPsync 代码未使用此参数**（sp_receive.py L415-420 只传了 `import_cameras` 和 `normal_map_format`），可轻松补上。

### 4.2 TextureSet 分辨率 ✅ 可读可写

`TextureSet` 类（textureset.py L1012-1062）暴露完整的分辨率 API：

```python
import substance_painter.textureset as ts

# 获取当前分辨率
resolution = texture_set.get_resolution()  # → Resolution(width=2048, height=2048)
print(f"{resolution.width}x{resolution.height}")

# 设置新分辨率（必须 POT）
new_res = ts.Resolution(1024, 1024)
texture_set.set_resolution(new_res)

# 批量设置所有 TextureSet
all_ts = ts.all_texture_sets()
ts.set_resolutions(all_ts, new_res)
```

| 方法 | 说明 |
|------|------|
| `TextureSet.get_resolution()` → `Resolution` | 获取当前 TextureSet 分辨率 |
| `TextureSet.set_resolution(Resolution)` | 设置 TextureSet 分辨率（POT, 范围内）|
| `set_resolutions(list[TextureSet], Resolution)` | 批量设置多个 TextureSet |
| `Resolution(width, height)` | 数据类，默认 1024×1024 |

**意义**：项目创建后仍可在 `_on_project_ready()` 回调中按 config 的 `max_resolution` 动态调整每个 TextureSet 的分辨率。

### 4.3 导出分辨率 `sizeLog2` ✅ 可行

SP `export_project_textures(config)` 的 `exportParameters` 支持 `sizeLog2`：

```python
# 源自 substance_painter/export.py L175-181
{
    "exportParameters": [
        # 全局参数（无 filter 时应用于所有 maps）
        {
            "parameters": {
                "fileFormat": "tga",
                "bitDepth": "8",
                "sizeLog2": 10,          # 单个整数 → 1024×1024
                "dithering": True,
                "paddingAlgorithm": "infinite"
            }
        },
        # Per-TextureSet 覆盖（用 filter.dataPaths 指定目标）
        {
            "filter": {"dataPaths": ["01_Head"]},
            "parameters": {
                "sizeLog2": 11           # 仅 01_Head 导出 2048
            }
        }
    ]
}
```

| log2 值 | 像素 |
|---------|------|
| 8 | 256 |
| 9 | 512 |
| 10 | 1024 |
| 11 | 2048 |
| 12 | 4096 |

- **当前状态**：SPsync 未使用 `sizeLog2`，所有贴图按 TextureSet 原始分辨率导出
- **添加后**：导出时按配置钳制尺寸
- **filter.dataPaths**：支持 per-TextureSet 设置不同导出分辨率

### 4.4 SP 分辨率控制总结

| 能力 | 支持 | API / 参数 |
|------|------|------------|
| 项目创建时默认分辨率 | ✅ | `project.Settings(default_texture_resolution=N)` |
| 运行时读取 TextureSet 分辨率 | ✅ | `TextureSet.get_resolution()` |
| 运行时设置 TextureSet 分辨率 | ✅ | `TextureSet.set_resolution(Resolution(w, h))` |
| 导出时覆盖分辨率 | ✅ | `exportParameters[].parameters.sizeLog2` |
| 导出时 per-TextureSet 分辨率 | ✅ | `exportParameters[].filter.dataPaths` |
| 宽高独立控制（TextureSet） | ✅ | `Resolution(width, height)` |
| POT 约束 | 必须 | 宽高必须为 2 的幂 |

### 4.5 Per-Texture 分辨率的限制

SP 分辨率控制粒度是 **per-TextureSet**，同一 TextureSet 的所有 maps（Diffuse, Normal, MRO 等）共享同一分辨率。

**若需不同贴图不同分辨率**：
1. 方案 A：为每种尺寸分别调用 `export_project_textures()`（会增加导出次数）
2. **方案 B（推荐）**：TextureSet 按最大 `max_resolution` 工作+导出，UE 端再按各贴图独立 `max_texture_size` 精确限制

### 4.6 导入资源分辨率 ℹ️ 无需控制

UE → SP 发送的 texture resource 被 `import_project_resource()` 导入。资源按原始文件尺寸导入，SP Fill Layer 引用这些资源但渲染在 TextureSet 自身分辨率上。**无需在 SP 导入端限制资源分辨率**。

---

## 5. 整体数据流

```
                     max_resolution 定义于:
                     texture_definitions[].max_resolution
                               │
          ┌────────────────────┼────────────────────┐
          ▼                    ▼                    ▼
    ┌───────────┐       ┌───────────┐        ┌───────────┐
    │ UE Import │       │  UE→SP    │        │  SP→UE    │
    │           │       │  Send     │        │  Export    │
    └─────┬─────┘       └─────┬─────┘        └─────┬─────┘
          │                   │                    │
  set_editor_property    传递 config           sizeLog2
  ("max_texture_size")   中的 max_resolution    per-TextureSet
          │                   │                    │
          ▼                   ▼                    ▼
  Runtime 限制分辨率     SP 端两步设定:      导出时钳制尺寸
  (Cook/Package)        ① project.Settings    export_config
                          (default_texture     sizeLog2 + filter
                           _resolution)
                        ② TextureSet
                          .set_resolution()
                              │                    │
                              ▼                    ▼
                       SP 内按设定分辨率    UE refresh_textures
                       工作和渲染          + max_texture_size
```

---

## 6. 开发计划

### Phase 1：配置格式扩展（影响：Config 文件 + 解析代码）

1. 在 `texture_definitions[]` 每项中增加可选 `max_resolution` 字段
2. 解析时默认 `{"width": 1024, "height": 1024}`
3. 验证：值必须为 2 的幂（256–4096）
4. 更新 Character.jsonc / Prop.jsonc 等现有配置为期望值

**涉及文件**：
- `Plugins/AssetCustoms/Content/Config/AssetCustoms/*.jsonc`（配置）
- `Plugins/AssetCustoms/Content/Python/…/sp_bridge.py`（解析逻辑）

### Phase 2：UE 导入端（影响：import_textures_ue.py）

1. `import_textures()` / `refresh_textures()` 接收 `max_resolution` 参数
2. 导入后读取 `get_size_x()`/`get_size_y()`，判断是否超限
3. 超限时 `set_editor_property("max_texture_size", cap)`
4. 未超限保持 `max_texture_size = 0`

**涉及文件**：
- `SPsync/import_textures_ue.py`

### Phase 3：UE→SP 数据传递 + SP 项目分辨率设定（影响：sp_bridge.py + sp_receive.py）

1. `sp_bridge.py` 在发送给 SP 的 JSON 中携带每个 texture_definition 的 `max_resolution`
2. `sp_receive.py` 在 `project.create()` 时传入 `default_texture_resolution`：
   - 取所有 texture_definitions 中 max_resolution 的最大值
3. `_on_project_ready()` 回调中用 `TextureSet.set_resolution()` 按 config 动态设定分辨率
4. 存入项目 metadata（供导出时使用）

**涉及文件**：
- `Plugins/AssetCustoms/Content/Python/…/sp_bridge.py`（发送端）
- `SPsync/sp_receive.py`（接收端：project.create + set_resolution + metadata）

### Phase 4：SP 导出端（影响：sp_channel_map.py + sp_sync_export.py）

1. `build_roundtrip_export_config()` 从 ue_defs 中读取 `max_resolution`
2. 计算 sizeLog2：取各 TextureSet 的 max_resolution，转为 log2 整数
3. 利用 `filter.dataPaths` 支持 per-TextureSet 不同导出分辨率
4. 注入到 `exportParameters[].parameters.sizeLog2`
5. 仅当 sizeLog2 ≤ 当前 TextureSet 分辨率时才注入（避免放大）

**涉及文件**：
- `SPsync/sp_channel_map.py`（export config 构建）
- `SPsync/sp_sync_export.py`（常规导出可选支持）

### Phase 5：测试 & 验证

1. 单元测试：config 解析默认值、POT 验证、sizeLog2 计算
2. 集成测试：mock texture 尺寸 → assert max_texture_size 设置
3. E2E 验证：实际 4K 贴图 → 导入 → 发送 SP → 导出 → 回到 UE，对比尺寸

---

## 7. 风险与注意事项

| 风险 | 影响 | 缓解 |
|------|------|------|
| SP 分辨率粒度是 per-TextureSet | 同一 TextureSet 所有 maps 分辨率相同 | TextureSet 取各贴图 max_resolution 的最大值，UE 端独立限制 |
| `max_texture_size` 仅影响 Cook/Runtime，编辑器内仍显示全分辨率 | 内存占用不变 | 若需编辑器内也限制，需 `resize_during_build` 方案 |
| POT 约束 | 非 POT 值在 SP 中无法表达 | 配置层强制 POT 校验 |
| SP 项目分辨率小于 max_resolution 时 sizeLog2 会放大 | 导出可能超实际 | 添加 min(project_res, max_res) 逻辑 |
| 向后兼容 | 已有配置无 `max_resolution` 字段 | 解析时默认 1024×1024 |
