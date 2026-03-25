# SPsync 开发计划

> 最后更新: 2026-03-25  
> 当前版本: 0.968 (阶段五已完成)  
> 目标版本: 1.0

---

## 项目概述

SPsync 是 Adobe Substance 3D Painter 插件，通过 Epic 远程执行协议实现与 Unreal Engine 5.x 的双向同步，包括纹理导出、材质自动创建、网格导入和实时相机同步。

---

## 当前项目状态

### 代码规模

| 文件 | 行数 | 运行环境 | 状态 |
|------|------|---------|------|
| `__init__.py` | 31 | SP | ✅ 稳定 |
| `sp_sync.py` | ~130 | SP | ✅ 已重构为控制器 |
| `sp_sync_config.py` | ~60 | SP | ✅ 新增（配置持久化） |
| `sp_sync_export.py` | ~230 | SP | ✅ 新增（导出编排） |
| `sp_sync_ui.py` | 248 | SP | ✅ 稳定（自动生成） |
| `sp_sync_ue.py` | 331 | SP | ⚠️ 待重构（字符串模板注入） |
| `remote_execution.py` | 630 | SP | ✅ 稳定（Epic 官方，不改动） |
| `import_textures_ue.py` | 52 | UE 远程 | ⚠️ 待重构（含占位符模板） |
| `material_ue.py` | 70 | UE 远程 | ✅ 已是参数化函数 |
| `material_instance_ue.py` | 30 | UE 远程 | ✅ 已是参数化函数 |
| `create_material_and_connect_textures.py` | 97 | UE 远程 | ⚠️ 待重构（含占位符模板） |
| `import_mesh_ue.py` | 79 | UE 远程 | ⚠️ 待重构（字符串拼接参数） |
| `sync_camera_ue.py` | 79 | UE 远程 | ✅ 稳定（高频调用，保持直传） |
| **合计** | **2,122** | | 6 个文件待重构 |

### 已知技术债

| 编号 | 问题 | 严重度 | 涉及文件 |
|------|------|--------|---------|
| TD-01 | ~~字符串模板注入~~ | ✅ 已解决 | `sp_sync_ue.py`, 3 个 UE 脚本 |
| TD-02 | ~~隐式作用域依赖~~ | ✅ 已解决 | `sp_sync_ue.py` (bootstrap 加载顺序已文档化) |
| TD-03 | ~~上帝类~~ | ✅ 已解决 | `sp_sync.py`, `sp_sync_config.py`, `sp_sync_export.py` |
| TD-04 | ~~占位符命名冲突风险~~ | ✅ 已解决 | JSON 参数化后不再存在 |
| TD-05 | ~~无单元测试~~ | ✅ 已解决 | `utils.py` + 37 个测试用例 |
| TD-06 | ~~类属性共享可变状态~~ | ✅ 已解决 | `sp_sync_ue.py`, `sp_sync_export.py` |
| TD-07 | ~~Signal 重复绑定~~ | ✅ 已解决 | `sp_sync_ue.py` |
| TD-08 | ~~Worker 异常后双重 stop~~ | ✅ 已解决 | `sp_sync_ue.py` |
| TD-09 | ~~Emissive intensity 逗号 Bug~~ | ✅ 已解决 | `create_material_and_connect_textures.py` |
| TD-10 | ~~死代码 (ray-casting)~~ | ✅ 已解决 | `import_mesh_ue.py` |

### 功能完整性

| 功能 | 状态 | 备注 |
|------|------|------|
| 纹理同步 (非UDIM) | ✅ 正常 | |
| 纹理同步 (UDIM) | ✅ 正常 | |
| 自动导出 | ✅ 正常 | |
| 材质创建 (Opaque) | ✅ 正常 | |
| 材质创建 (Masked) | ✅ 正常 | |
| 材质创建 (Translucent) | ✅ 正常 | |
| 网格导入 + 场景放置 | ✅ 正常 | |
| 实时相机同步 | ✅ 正常 | ~30fps |
| 配置持久化 | ✅ 正常 | SP 项目元数据 |
| PySide2/6 兼容 | ✅ 正常 | 运行时检测 |

---

## 重构计划

> 详细方案见 [`doc/REFACTORING_PLAN.md`](doc/REFACTORING_PLAN.md)  
> 方案代号: **方案 A — 一次注入 + JSON 参数化调用**

### 核心思路

将当前"每次操作发送完整脚本 + 字符串替换参数"改为"连接时一次注入函数定义 + 后续只发送 JSON 参数化函数调用"。保持零 UE 侧部署要求。

### 阶段总览

```
阶段一 ──→ 阶段二 ──→ 阶段三
抽离纯逻辑   UE脚本参数化   SP主类拆分
  低风险       中风险        低中风险
```

### 阶段一：抽离纯逻辑 + 单元测试

- **状态**: ✅ 已完成 (2026-03-24)
- **风险**: ⭐ 低
- **目标**: 将可独立测试的纯逻辑从各模块抽离到 `utils.py`，建立测试基础

| 任务 | 状态 | 说明 |
|------|------|------|
| 创建 `utils.py` | ✅ | 11 个纯函数：路径提取、材质类型判断、Content 路径校验/转换、纹理命名、材质路径、UDIM 过滤、资产名称匹配 |
| 创建 `tests/test_utils.py` | ✅ | 37 个测试用例，全部通过 |
| `sp_sync.py` 调用 `utils` | ✅ | `_get_texture_set_material_type()` 委托 `determine_material_type()`；路径提取委托 `extract_mesh_name()`；路径校验委托 `validate_content_path()` + `content_path_to_game_path()` |
| `sp_sync_ue.py` 调用 `utils` | ✅ | `ue_import_mesh()` 中路径提取委托 `extract_mesh_name()` |
| 人工回归测试 | 🔲 | 基本流程验证（待执行） |

### 阶段二：UE 侧脚本参数化改造

- **状态**: ✅ 已完成 (2026-03-25)
- **风险**: ⭐⭐⭐ 中
- **前置**: 阶段一完成并通过人工测试
- **目标**: 消除字符串模板拼接，改为 JSON 参数化调用

| 任务 | 状态 | 说明 |
|------|------|------|
| `sp_sync_ue.py` 新增 bootstrap 机制 | ✅ | `_load_ue_scripts()` 合并 6 个脚本，`_ensure_bootstrap()` 一次注入，错误时自动重置 |
| 改造 `import_textures_ue.py` | ✅ | 去掉占位符 → `def import_textures(params_json)` 接收 JSON |
| 改造 `create_material_and_connect_textures.py` | ✅ | 去掉占位符 → `def create_material_and_connect_textures(params_json)` 接收 JSON |
| 改造 `import_mesh_ue.py` | ✅ | `import_mesh_and_swap(params_json)` 改为接收 JSON |
| `sp_sync_ue.py` 调用改为 JSON 序列化 | ✅ | `sync_ue_textures`, `sync_ue_create_material_and_connect_textures`, `ue_import_mesh` 全部改为 `json.dumps()` + `repr()` |
| `material_ue.py` 纳入统一 bootstrap | ✅ | 代码不变，通过 `_load_ue_scripts()` 合并加载 |
| `material_instance_ue.py` 纳入统一 bootstrap | ✅ | 代码不变，隐式依赖通过 bootstrap 加载顺序解决 |
| `sync_camera_ue.py` 纳入统一 bootstrap | ✅ | 移除模块级 `editor_set_game_view(True)` 副作用，保持高频直传 |
| 人工测试: 完整测试矩阵 | 🔲 | 见下方测试矩阵 |

### 阶段三：sp_sync.py 职责拆分

- **状态**: ✅ 已完成 (2026-03-25)
- **风险**: ⭐⭐ 低中
- **前置**: 阶段二完成并通过人工测试
- **目标**: 消除上帝类，职责清晰分层

| 任务 | 状态 | 说明 |
|------|------|------|
| 创建 `sp_sync_config.py` | ✅ | `SPSyncConfig` 类：`save()` / `load()` / `origin_export_path` 属性 |
| 创建 `sp_sync_export.py` | ✅ | `SPSyncExport` 类：导出编排、预设管理、纹理集追踪 |
| 精简 `sp_sync.py` | ✅ | ~130 行控制器：事件注册 + UI 绑定 + 委托到 config/export |
| 人工回归测试 | 🔲 | 配置 + 完整导出流程 |

---

## 人工测试矩阵

每个阶段完成后执行：

### 基础功能 (4 项)

| # | 测试项 | 通过 |
|---|--------|------|
| 1 | 插件加载 — SP 启动后 SPsync 面板出现 | 🔲 |
| 2 | 项目打开 — 预设列表加载，配置恢复 | 🔲 |
| 3 | 项目关闭 — UI 状态清空 | 🔲 |
| 4 | 配置保存 — 修改后关闭重开项目，配置正确恢复 | 🔲 |

### 纹理同步 (3 项)

| # | 测试项 | UDIM | 通过 |
|---|--------|------|------|
| 5 | SYNC 按钮 | ❌ | 🔲 |
| 6 | SYNC 按钮 | ✅ | 🔲 |
| 7 | Auto Export 自动触发 | ❌ | 🔲 |

### 材质创建 (5 项)

| # | 测试项 | 类型 | Emissive | 通过 |
|---|--------|------|----------|------|
| 8 | Opaque 材质 | Opaque | ❌ | 🔲 |
| 9 | Masked 材质 | Masked | ❌ | 🔲 |
| 10 | Translucent 材质 | Translucent | ❌ | 🔲 |
| 11 | 含 Emissive | Opaque | ✅ | 🔲 |
| 12 | UDIM 材质 | UDIM | ❌ | 🔲 |

### 网格导入 (3 项)

| # | 测试项 | Force X | 通过 |
|---|--------|---------|------|
| 13 | SYNC(Mesh) 标准 | ❌ | 🔲 |
| 14 | SYNC(Mesh) Force X | ✅ | 🔲 |
| 15 | 缩放参数生效 | — | 🔲 |

### 相机同步 (2 项)

| # | 测试项 | 通过 |
|---|--------|------|
| 16 | View Sync 开启 | 🔲 |
| 17 | View Sync 关闭 | 🔲 |

### 异常场景 (3 项)

| # | 测试项 | 通过 |
|---|--------|------|
| 18 | UE 未启动时 SYNC | 🔲 |
| 19 | 路径不含 Content/ | 🔲 |
| 20 | 非 SPSYNCDefault 预设 + 创建材质 | 🔲 |

---

## 不改动的模块

| 模块 | 原因 |
|------|------|
| `remote_execution.py` | Epic 官方协议实现，630 行，稳定可靠 |
| `sp_sync_ui.py` | 从 `.ui` 文件生成，应通过 Qt Designer 维护 |
| `__init__.py` | 入口极简，无需改动 |

---

## 阶段四：Grayscale Conversion Filter 通道拆分

- **状态**: ✅ 已完成 (2026-03-25)
- **风险**: ⭐⭐ 低中
- **前置**: M7 Phase 5 完成 + PoC 探测脚本验证通过（8/8）
- **目标**: 支持 Packed Texture (MRO/ORM) 在 SP 中自动拆分为独立通道

### 背景

当前 `parameter_bindings` 将 Packed Texture 整包映射到单一通道（如 `"MRO": "Packed_Texture"` → Roughness），
无法将 R/G/B 通道分别映射到 Metallic/Roughness/AO。

通过 SP 内置的 **Grayscale Conversion** 滤镜，在 Fill Layer 上插入 Filter Effect 并设置 RGBA 权重，可从 Packed Texture 提取任意单通道。

### PoC 验证结论

| 项目 | 结果 |
|------|------|
| `resource.search('u:filter n:"Grayscale Conversion"')` | ✅ 1 exact match |
| `insert_filter_effect(InsertPosition.inside_node(...), filter_id)` | ✅ 成功创建 |
| `FilterEffectNode.get_source()` → `SourceSubstance` | ✅ 可访问 |
| `SourceSubstance.get_parameters()` | ✅ 返回 9 个参数 |
| `SourceSubstance.set_parameters({"Red": 1.0, ...})` | ✅ 写入 + 读回一致 |
| 参数类型约束 | int 参数必须传 int（不可传 float） |

### 已确认的 Filter 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `grayscale_type` | int | 0 | 0=Desaturation, **1=Channels Weights**, 2=Average, 3=Max, 4=Min |
| `Red` | float | 0.33 | R 通道权重 [0,1] |
| `Green` | float | 0.33 | G 通道权重 [0,1] |
| `Blue` | float | 0.33 | B 通道权重 [0,1] |
| `Alpha` | float | 0.0 | A 通道权重 [0,1] |
| `channel_input` | int | 0 | 0=Current Channel, 1=Custom Input |
| `invert` | int | 0 | 0/1 布尔 |
| `balance` | float | 0.5 | [0,1] |
| `contrast` | float | 0.0 | [0,1] |

### 实施任务

| 任务 | 状态 | 文件 | 说明 |
|------|------|------|------|
| 15a: 通道后缀解析 | ✅ | `sp_channel_map.py` | `parse_channel_suffix()` + `resolve_packed_channels()` |
| 15b: Filter as per-channel source | ✅ | `sp_receive.py` | `_create_fill_with_filter()` 重写为 set_source(ch, filter) 方式 |
| 15c: 动态通道添加 | ✅ | `sp_receive.py` | `_ensure_channel_exists()` — stack.add_channel(AO, L8) |
| 15d: 集成测试 | 🔲 | E2E | MRO → M/R/AO 三通道拆分验证（待 E2E 重测） |

---

## 阶段五：Round-Trip Sync（SP → UE 贴图回传）

- **状态**: ✅ 已完成 (2026-03-25)
- **风险**: ⭐⭐ 低中
- **前置**: 阶段四完成
- **目标**: 实现 UE→SP→UE 贴图往返更新，点击 SYNC 自动按 UE 原始格式导出并刷新 UE 贴图
- **详细设计**: [`doc/ROUNDTRIP_SYNC.md`](doc/ROUNDTRIP_SYNC.md)

### 核心思路

```
UE 发送材质信息 ──→ SP 创建项目 + 存入 Metadata
                         ↓ 用户编辑
                    SYNC 按钮触发
                         ↓
              检测 Metadata 中有 UE 定义?
               是 ↓                否 ↓
           回传模式               预设模式（现有流程）
               ↓
    动态生成导出配置（匹配 UE 原始贴图格式）
               ↓
    导出到临时目录 → 推送到 UE 原始路径 → 刷新贴图
```

### 实施任务

| 任务 | 状态 | 文件 | 说明 |
|------|------|------|------|
| 5A: Metadata 存储 | ✅ | `sp_receive.py` | `_build_roundtrip_metadata()` 写入 UE 材质定义到 SP 项目元数据 |
| 5B: 导出配置生成器 | ✅ | `sp_channel_map.py` | `build_roundtrip_export_maps/config/refresh_list()` 纯逻辑 + pytest |
| 5C: UE 刷新脚本 | ✅ | `import_textures_ue.py`, `sp_sync_ue.py` | `refresh_textures()` + `sync_ue_refresh_textures()` 按原路径刷新 |
| 5D: SYNC 集成 | ✅ | `sp_sync_export.py` | `sync_textures(roundtrip)` 参数 + 自动检测元数据 |
| 5E: 探测验证 | ✅ | `tests/probe_*.py` | srcMapName 格式验证，AO→ambientOcclusion 确认 |
| 5F: 集成测试 | ✅ | `tests/test_roundtrip.py` | 185 passed（含 roundtrip 导出配置 + metadata + refresh list） |

### 文件变更范围（已完成）

| 文件 | 变更 |
|------|------|
| `sp_receive.py` | 修改：`_build_roundtrip_metadata()` 写入 metadata |
| `sp_channel_map.py` | 新增函数：`build_roundtrip_export_maps/config/refresh_list()`，`_SP_SRC_MAP_NAME` 查找表 |
| `sp_sync_export.py` | 修改：`sync_textures(roundtrip)` 参数 + roundtrip 模式分支 |
| `import_textures_ue.py` | 新增函数：`refresh_textures()` |
| `sp_sync_ue.py` | 新增方法：`sync_ue_refresh_textures()` |
| `create_material_and_connect_textures.py` | Bug Fix：emissive BCO fallback 修复 |
| `tests/test_roundtrip.py` | 新增测试 |

---

## 变更日志

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-03-24 | 0.964 | 项目初始状态记录；制定重构计划（方案 A） |
| 2026-03-24 | 0.964+ | 阶段一完成：创建 `utils.py`（11 个纯函数）+ `tests/test_utils.py`（37 个测试用例）；`sp_sync.py` 和 `sp_sync_ue.py` 已委托调用 |
| 2026-03-25 | 0.964++ | 阶段二完成：UE 侧脚本参数化改造。`import_textures_ue.py`/`create_material_and_connect_textures.py`/`import_mesh_ue.py` 去掉占位符改为 JSON 入参；`sp_sync_ue.py` 新增 bootstrap 一次注入机制 + JSON 序列化调用；`sync_camera_ue.py` 移除模块级副作用 |
| 2026-03-25 | 0.964+++ | 阶段三完成：sp_sync.py 上帝类拆分为 controller / config / export 三个文件 |
| 2026-03-25 | 0.965 | 稳定性优化：修复 emissive intensity 逗号 Bug、类属性可变状态共享、Signal 重复绑定、Worker 异常流、清理死代码、解耦导出事件、UE 脚本依赖文档化、提取导出配置工厂方法 |
| 2026-03-25 | 0.966 | 阶段四（Grayscale Conversion）：15a/15b/15c 完成，`_create_fill_with_filter()` 重写为 per-channel source 方式，`_ensure_channel_exists()` 新增，162 测试通过 |
| 2026-03-25 | — | 阶段五设计完成：Round-Trip Sync 调研与实现路径，详见 `doc/ROUNDTRIP_SYNC.md` |
| 2026-03-25 | 0.967 | 阶段五完成：Round-Trip Sync 5A-5D 全部实现。Metadata 存储 + 动态导出配置 + UE 刷新脚本 + SYNC 集成 |
| 2026-03-25 | 0.968 | Bug Fix 轮：BaseColor 导出黑色（srcMapName/srcChannel 格式）、AO srcMapName（"ao"→"ambientOcclusion"）、标准导出 metallic（roundtrip 自动检测 bypass）、Emissive BCO fallback 修复。185 测试通过 |
