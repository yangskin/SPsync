# SP 端性能优化方案

## 背景

UE→SP "Send to SP" 流程在 `parameter_bindings` 重构后速度明显变慢。  
SP 端进度条（`project.create()` 的 mesh 加载）理论上应该很快完成，  
但进度条之后的 `_on_project_ready()` 回调中贴图处理耗时显著增加。

---

## 瓶颈分析

### 当前流程（`_on_project_ready` 内部）

```
for 材质 in materials:
    匹配 TextureSet
    for 贴图 in 材质.textures:
        导入贴图资源 (import_project_resource)  ← 阻塞 I/O
        if packed:
            for 通道 in packed_channels:
                确保通道存在 (add_channel)
                创建 Fill Layer
                设置 Filter + 权重
        else:
            确保通道存在
            创建 Fill Layer
            分配贴图
```

**问题：导入 (I/O) 和创建 (计算) 交错执行，无法批量优化。**

### 具体瓶颈

| # | 瓶颈 | 当前行为 | 影响 |
|---|------|----------|------|
| 1 | 贴图导入与图层创建交错 | per-texture: 导入 → 立即创建图层 | I/O 阻塞穿插在计算中 |
| 2 | `imported_resources` 缓存 per-material | 不跨材质共享，多材质共享同一贴图时重复导入 | 多材质场景浪费 |
| 3 | Grayscale Filter 首次查询在图层创建循环内 | 首次 `resource.search()` 发生在 packed 通道处理时 | 增加首个 packed 通道延迟 |
| 4 | `_ensure_channel_exists` 未跟踪已添加通道 | 每次调用都尝试 `add_channel()` + 捕获异常 | 异常开销 × 通道数 |

---

## 优化方案：三阶段分离

### 新流程

```
Phase 0 — 预处理：
    匹配所有材质 → TextureSet
    解析所有 packed 通道映射
    预热 Grayscale Filter 缓存

Phase 1 — 批量导入（全局缓存）：
    收集所有材质的所有贴图路径（去重）
    for 贴图路径 in 去重集合:
        import_project_resource()  ← 集中 I/O
    → 全局 imported_resources dict

Phase 2 — 批量创建图层：
    for 材质 in materials:
        预创建所有需要的通道 (batch add_channel)
        for 贴图 in 材质.textures:
            从全局缓存取资源引用（无 I/O）
            创建 Fill Layer + 分配/Filter
```

### 改动范围

**仅修改 `sp_receive.py` 的 `_on_project_ready()` 函数内部流程。**

- 不改任何函数签名或外部接口
- 不改 `_create_fill_with_filter()`、`_ensure_channel_exists()`、`_find_grayscale_filter()` 的实现
- 不改 UE 端任何代码

### 预期收益

| 优化 | 效果 |
|------|------|
| 全局资源缓存 | 跨材质去重，减少重复 `import_project_resource()` 调用 |
| I/O 与计算分离 | 导入集中执行，图层创建阶段零 I/O 等待 |
| Filter 预热 | 消除首个 packed 通道的额外延迟 |
| 通道跟踪 | 避免 `add_channel()` 重复捕获异常 |

---

## 实施状态

- [x] Phase 0 + 1 + 2 三阶段重构 `_on_project_ready()`
- [x] SPsync 191 项测试全部通过
- [ ] E2E 验证（需在 UE + SP 中测试）

### 后续（UE 端优化，暂不实施）

- [ ] `_load_config_for_sp()` 加 profile 缓存（消除 N+1 次重复文件读取）
- [ ] `texture_definitions` 只放 SM 顶层（减少 JSON 体积 ~70%）
- [ ] `run_asset_export_tasks` 批量导出 API（减少 Python↔C++ 调用次数）
