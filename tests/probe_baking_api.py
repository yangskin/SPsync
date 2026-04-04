# -*- coding: utf-8 -*-
"""SP 内执行的探测脚本 — 探测 Baking API、可用 baker 参数与高模入口。

使用方法：
  在 SP 中打开一个项目，然后在 SP 的
  Python 控制台（Window → Python Console）中执行：

    exec(open(r"C:\\Users\\tiany\\Documents\\Adobe\\Adobe Substance 3D Painter\\python\\plugins\\SPsync\\tests\\probe_baking_api.py", encoding="utf-8").read())

默认行为：
  - 只读探测，不会启动 bake
  - 不会改写高模路径

可选行为：
  1. 将 TEST_HIGH_POLY_PATH 改成实际高模路径，可验证高模参数是否可写
  2. 将 START_BAKE 改为 True，可实际触发一次 bake

探测项：
  1. 项目 / TextureSet 基本信息
  2. common baking parameters 及其元信息
  3. 高模相关参数候选（例如 HipolyMesh）
  4. 每个 MeshMapUsage 的 baker parameters
  5. 当前启用的 bakers / TextureSet / UV Tile
  6. 可选：写入高模路径并读回
  7. 可选：启动 bake 并打印事件
"""

TEST_HIGH_POLY_PATH = None
START_BAKE = False
TARGET_TEXTURE_SET_NAME = None
TARGET_BAKERS = ["Normal"]


def _safe_call(func, default=None):
    try:
        return func()
    except Exception:
        return default


def _sep(title=None):
    line = "=" * 72
    if title:
        print(f"\n{line}\n[PROBE] {title}\n{line}")
    else:
        print(f"\n{line}")


def _iter_mesh_map_usages(mesh_map_usage_enum):
    members = getattr(mesh_map_usage_enum, "__members__", None)
    if members:
        return sorted(members.items(), key=lambda item: item[0].lower())

    usages = []
    for name in dir(mesh_map_usage_enum):
        if name.startswith("_"):
            continue
        if name in {"name", "value"}:
            continue
        value = getattr(mesh_map_usage_enum, name)
        if callable(value):
            continue
        if not isinstance(value, mesh_map_usage_enum):
            continue
        usages.append((name, value))
    usages.sort(key=lambda item: item[0].lower())
    return usages


def _property_info(prop, _safe_call_fn=_safe_call):
    info = {
        "short_name": _safe_call_fn(prop.short_name, "?"),
        "label": _safe_call_fn(prop.label, "?"),
        "widget": _safe_call_fn(prop.widget_type, "?"),
        "value": _safe_call_fn(prop.value, "<读取失败>"),
        "meta": _safe_call_fn(prop.properties, {}),
    }
    if info["widget"] == "Combobox":
        info["enum_values"] = _safe_call_fn(prop.enum_values, {})
    return info


def _print_property_block(title, properties_dict, _property_info_fn=_property_info):
    print(f"\n[PROBE] {title} ({len(properties_dict)} 项)")
    for key in sorted(properties_dict.keys(), key=str.lower):
        prop = properties_dict[key]
        info = _property_info_fn(prop)
        print(f"  - key={key}")
        print(f"      label={info['label']}")
        print(f"      widget={info['widget']}")
        print(f"      value={info['value']}")
        meta = info["meta"] or {}
        if meta:
            compact_meta = {
                name: meta[name]
                for name in sorted(meta.keys())
                if name in {"min", "max", "step", "default", "tooltip", "extensions"}
            }
            if compact_meta:
                print(f"      meta={compact_meta}")
        if "enum_values" in info and info["enum_values"]:
            print(f"      enum_values={info['enum_values']}")


def _find_highpoly_candidates(properties_dict, _property_info_fn=_property_info):
    candidates = []
    for key, prop in properties_dict.items():
        info = _property_info_fn(prop)
        search_text = " ".join([
            str(key),
            str(info["short_name"]),
            str(info["label"]),
            str(info["widget"]),
        ]).lower()
        if any(token in search_text for token in ("hipoly", "high", "poly", "mesh", "file")):
            candidates.append((key, info))
    return candidates


def _pick_texture_set(all_texture_sets, requested_name=None):
    if requested_name:
        for texture_set in all_texture_sets:
            if texture_set.name() == requested_name:
                return texture_set
    return all_texture_sets[0] if all_texture_sets else None


def _maybe_write_highpoly_path(baking_params, candidate_key, candidate_info, file_path):
    from pathlib import Path

    if not file_path:
        print("\n[PROBE] 未设置 TEST_HIGH_POLY_PATH，跳过高模写入测试。")
        return

    prop = baking_params.common()[candidate_key]
    qurl = Path(file_path).resolve().as_uri()

    print("\n[PROBE] 高模写入测试")
    print(f"  目标参数: {candidate_key}")
    print(f"  label: {candidate_info['label']}")
    print(f"  widget: {candidate_info['widget']}")
    print(f"  输入路径: {file_path}")
    print(f"  QUrl: {qurl}")

    try:
        baking_params.set({prop: qurl})
        readback = prop.value()
        print("  ✓ 写入成功")
        print(f"  读回值: {readback}")
    except Exception as exc:
        print(f"  ✗ 写入失败: {exc}")


def _resolve_target_bakers(mesh_map_usage_enum, target_names):
    resolved = []
    unresolved = []
    for name in target_names:
        if hasattr(mesh_map_usage_enum, name):
            resolved.append(getattr(mesh_map_usage_enum, name))
        else:
            unresolved.append(name)
    return resolved, unresolved


def _start_bake_if_requested(texture_set, baking_params, target_usages, start_bake=START_BAKE):
    import substance_painter.baking as baking
    import substance_painter.event as event
    import substance_painter.project as project

    if not start_bake:
        print("\n[PROBE] START_BAKE=False，跳过实际 bake。")
        return

    if project.is_busy():
        print("\n[PROBE] 当前 SP 处于 busy 状态，取消启动 bake。")
        return

    def _on_bake_start(evt):
        print(f"[PROBE] BakingProcessAboutToStart: stop_source={evt.stop_source}")

    def _on_bake_progress(evt):
        print(f"[PROBE] BakingProcessProgress: {evt.progress:.2%}")

    def _on_bake_end(evt):
        print(f"[PROBE] BakingProcessEnded: status={evt.status}")
        try:
            event.DISPATCHER.disconnect(event.BakingProcessAboutToStart, _on_bake_start)
        except Exception:
            pass
        try:
            event.DISPATCHER.disconnect(event.BakingProcessProgress, _on_bake_progress)
        except Exception:
            pass
        try:
            event.DISPATCHER.disconnect(event.BakingProcessEnded, _on_bake_end)
        except Exception:
            pass

    print("\n[PROBE] 启动 bake")
    print(f"  TextureSet: {texture_set.name()}")
    print(f"  Target bakers: {[str(x) for x in target_usages]}")

    try:
        baking_params.set_textureset_enabled(True)
        if target_usages:
            baking_params.set_enabled_bakers(target_usages)
        event.DISPATCHER.connect(event.BakingProcessAboutToStart, _on_bake_start)
        event.DISPATCHER.connect(event.BakingProcessProgress, _on_bake_progress)
        event.DISPATCHER.connect(event.BakingProcessEnded, _on_bake_end)
        stop_source = baking.bake_async(texture_set)
        print(f"  ✓ bake_async 已调用: stop_source={stop_source}")
    except Exception as exc:
        print(f"  ✗ bake 启动失败: {exc}")


def probe(
    _sep_fn=_sep,
    _safe_call_fn=_safe_call,
    _pick_texture_set_fn=_pick_texture_set,
    _print_property_block_fn=_print_property_block,
    _find_highpoly_candidates_fn=_find_highpoly_candidates,
    _resolve_target_bakers_fn=_resolve_target_bakers,
    _maybe_write_highpoly_path_fn=_maybe_write_highpoly_path,
    _start_bake_if_requested_fn=_start_bake_if_requested,
    target_texture_set_name=TARGET_TEXTURE_SET_NAME,
    target_bakers=TARGET_BAKERS,
    test_high_poly_path=TEST_HIGH_POLY_PATH,
):
    import substance_painter.baking as baking
    import substance_painter.project as project
    import substance_painter.textureset as textureset
    import traceback

    _sep_fn("Baking API Inspector")

    if not project.is_open():
        print("[PROBE] 错误：请先打开一个项目再运行此脚本。")
        return

    print(f"[PROBE] is_open={project.is_open()}")
    print(f"[PROBE] is_busy={project.is_busy()}")
    print(f"[PROBE] is_in_edition_state={project.is_in_edition_state()}")

    all_texture_sets = list(textureset.all_texture_sets())
    print(f"[PROBE] TextureSet 数量: {len(all_texture_sets)}")
    for index, texture_set in enumerate(all_texture_sets):
        resolution = _safe_call_fn(texture_set.get_resolution)
        res_text = f"{resolution.width}x{resolution.height}" if resolution else "?"
        print(f"  [{index}] {texture_set.name()}  resolution={res_text}")

    texture_set = _pick_texture_set_fn(all_texture_sets, target_texture_set_name)
    if texture_set is None:
        print("[PROBE] 错误：当前项目无可用 TextureSet。")
        return

    print(f"\n[PROBE] 目标 TextureSet: {texture_set.name()}")

    try:
        baking_params = baking.BakingParameters.from_texture_set(texture_set)
    except Exception as exc:
        print(f"[PROBE] 获取 BakingParameters 失败: {exc}")
        traceback.print_exc()
        return

    common_params = baking_params.common()
    _print_property_block_fn("Common Baking Parameters", common_params)

    highpoly_candidates = _find_highpoly_candidates_fn(common_params)
    print(f"\n[PROBE] 高模相关 common 参数候选: {len(highpoly_candidates)}")
    for key, info in highpoly_candidates:
        print(f"  - key={key}  label={info['label']}  widget={info['widget']}  value={info['value']}")

    usages = _iter_mesh_map_usages(textureset.MeshMapUsage)
    print(f"\n[PROBE] MeshMapUsage 成员: {[name for name, _ in usages]}")

    print("\n[PROBE] 当前开关状态")
    print(f"  TextureSet enabled: {baking_params.is_textureset_enabled()}")
    print(f"  Curvature method: {baking_params.get_curvature_method()}")
    print(f"  Enabled bakers: {baking_params.get_enabled_bakers()}")
    print(f"  Enabled UV Tiles: {baking_params.get_enabled_uv_tiles()}")

    for usage_name, usage_value in usages:
        print(f"\n[PROBE] Baker: {usage_name}")
        try:
            print(f"  enabled={baking_params.is_baker_enabled(usage_value)}")
            baker_params = baking_params.baker(usage_value)
            _print_property_block_fn(f"Baker Parameters / {usage_name}", baker_params)
            candidates = _find_highpoly_candidates_fn(baker_params)
            if candidates:
                print(f"  [候选] 与高模/文件相关的 baker 参数:")
                for key, info in candidates:
                    print(f"    - key={key}  label={info['label']}  widget={info['widget']}  value={info['value']}")
        except Exception as exc:
            print(f"  跳过该 usage，读取 baker 参数失败: {exc}")

    if highpoly_candidates:
        candidate_key, candidate_info = highpoly_candidates[0]
        _maybe_write_highpoly_path_fn(baking_params, candidate_key, candidate_info, test_high_poly_path)
    else:
        print("\n[PROBE] 未在 common 参数中找到明显的高模入口，请人工检查上面的参数表。")

    target_usages, unresolved = _resolve_target_bakers_fn(textureset.MeshMapUsage, target_bakers)
    if unresolved:
        print(f"\n[PROBE] 未识别的 TARGET_BAKERS: {unresolved}")

    _start_bake_if_requested_fn(texture_set, baking_params, target_usages)

    _sep_fn("完成")


probe()