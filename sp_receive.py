# -*- coding: utf-8 -*-
"""SPsync 接收模块 — 处理从 UE AssetCustoms 发送的数据。

职责：
  ⑤ 创建 SP 项目 + 导入网格
  ⑥ 创建 Fill Layer + 通道分配
  ⑦ 配置导出预设

纯逻辑函数（可 pytest）与 SP API 函数分离。
"""
import json
from typing import Any


# ---------------------------------------------------------------------------
# 纯逻辑函数（🤖 可 pytest）
# ---------------------------------------------------------------------------

# material_info JSON 必填字段
REQUIRED_FIELDS = ("static_mesh", "static_mesh_path", "materials")
REQUIRED_TEXTURE_FIELDS = ("texture_property_name", "texture_path", "texture_export_path", "texture_name")


def match_material_to_textureset(
    material_name: str,
    textureset_names: list[str],
    slot_name: str | None = None,
) -> str | None:
    """将 UE 材质槽/材质名匹配到 SP TextureSet 名称。

    SP TextureSet 名称来源于 FBX 导入时的材质名，通常与 UE 的材质槽名(slot_name)一致。

    匹配策略（按优先级）：
    1. slot_name 精确匹配 TextureSet 名
    2. slot_name 大小写不敏感匹配
    3. material_name 精确匹配
    4. material_name 去 MI_ 前缀后匹配
    5. 大小写不敏感匹配（material_name / 去 MI_ 前缀）

    Args:
        material_name: UE 材质资产名（如 "MI_Body"）。
        textureset_names: SP TextureSet 名称列表。
        slot_name: UE 材质槽名称（如 "Body"），优先用于匹配。

    Returns:
        匹配的 TextureSet 名，或 None。

    >>> match_material_to_textureset("MI_Body", ["Body", "Weapon"], slot_name="Body")
    'Body'
    >>> match_material_to_textureset("MI_Body", ["body"], slot_name="Body")
    'body'
    >>> match_material_to_textureset("MI_Body", ["MI_Body", "MI_Weapon"])
    'MI_Body'
    >>> match_material_to_textureset("MI_Body", ["Body", "Weapon"])
    'Body'
    >>> match_material_to_textureset("MI_Unknown", ["Body", "Weapon"]) is None
    True
    """
    # ── slot_name 匹配（最高优先级）──
    if slot_name:
        # 1. slot_name 精确匹配
        if slot_name in textureset_names:
            return slot_name
        # 2. slot_name 大小写不敏感
        slot_lower = slot_name.lower()
        for ts_name in textureset_names:
            if ts_name.lower() == slot_lower:
                return ts_name

    # ── material_name fallback ──
    # 3. 精确匹配
    if material_name in textureset_names:
        return material_name

    # 4. 去掉 MI_ 前缀后匹配
    stripped = material_name
    if stripped.startswith("MI_") or stripped.startswith("mi_"):
        stripped = stripped[3:]
    if stripped != material_name and stripped in textureset_names:
        return stripped

    # 5. 大小写不敏感
    mat_lower = material_name.lower()
    stripped_lower = stripped.lower()
    for ts_name in textureset_names:
        ts_lower = ts_name.lower()
        if ts_lower == mat_lower or ts_lower == stripped_lower:
            return ts_name

    return None


def validate_ue_data(data: dict) -> list[str]:
    """校验从 UE 收到的数据包。

    Args:
        data: 解析后的 JSON 字典。

    Returns:
        错误消息列表。空列表表示校验通过。

    >>> validate_ue_data({"static_mesh": "SM", "static_mesh_path": "/Game/SM", "materials": []})
    []
    >>> errors = validate_ue_data({})
    >>> len(errors) > 0
    True
    """
    errors = []
    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"缺少必填字段: {field}")

    if "materials" in data:
        if not isinstance(data["materials"], list):
            errors.append("materials 必须是数组")
        else:
            for i, mat in enumerate(data["materials"]):
                if not isinstance(mat, dict):
                    errors.append(f"materials[{i}] 必须是对象")
                    continue
                if "material_name" not in mat:
                    errors.append(f"materials[{i}] 缺少 material_name")
                for j, tex in enumerate(mat.get("textures", [])):
                    for tf in REQUIRED_TEXTURE_FIELDS:
                        if tf not in tex:
                            errors.append(f"materials[{i}].textures[{j}] 缺少 {tf}")

    return errors


def parse_ue_data(json_str: str) -> dict:
    """解析并校验 UE 数据包。

    Args:
        json_str: JSON 字符串。

    Returns:
        解析后的字典。

    Raises:
        ValueError: JSON 解析失败或校验不通过。
    """
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON 解析失败: {exc}") from exc

    errors = validate_ue_data(data)
    if errors:
        raise ValueError(f"数据校验失败: {'; '.join(errors)}")

    return data


def build_roundtrip_metadata(data: dict) -> dict:
    """从 UE 数据包中提取回传所需的持久化字段。

    去掉 texture_export_path 等临时路径，保留材质定义 + UE 资产路径。

    Args:
        data: parse_ue_data() 返回的完整数据字典。

    Returns:
        可 JSON 序列化的精简字典，用于存入 SP 项目 Metadata。

    >>> d = {"static_mesh": "SM", "static_mesh_path": "/Game/SM", "materials": [
    ...     {"material_name": "MI", "material_slot_name": "Slot",
    ...      "config_profile": "Prop",
    ...      "parameter_bindings": {"D": "BC"},
    ...      "textures": [{"texture_property_name": "BC", "texture_path": "/Game/T",
    ...                    "texture_export_path": "C:/tmp/T.tga", "texture_name": "T"}]}
    ... ]}
    >>> rt = build_roundtrip_metadata(d)
    >>> rt["static_mesh"]
    'SM'
    >>> "texture_export_path" in rt["materials"][0]["textures"][0]
    False
    >>> rt["materials"][0]["textures"][0]["texture_path"]
    '/Game/T'
    """
    materials = []
    for mat in data.get("materials", []):
        textures = []
        for tex in mat.get("textures", []):
            textures.append({
                "texture_property_name": tex.get("texture_property_name", ""),
                "texture_path": tex.get("texture_path", ""),
                "texture_name": tex.get("texture_name", ""),
            })
        mat_entry: dict = {
            "material_name": mat.get("material_name", ""),
            "material_slot_name": mat.get("material_slot_name", ""),
            "texture_set_name": mat.get("_matched_ts_name", ""),
            "config_profile": mat.get("config_profile", data.get("config_profile", "")),
            "parameter_bindings": mat.get("parameter_bindings", {}) or data.get("parameter_bindings", {}),
            "textures": textures,
        }
        # 保留 texture_definitions（新格式通道打包信息）
        td = mat.get("texture_definitions") or data.get("texture_definitions")
        if td:
            mat_entry["texture_definitions"] = td
        materials.append(mat_entry)
    return {
        "static_mesh": data.get("static_mesh", ""),
        "static_mesh_path": data.get("static_mesh_path", ""),
        "materials": materials,
    }


# SP 导出 srcMapName 映射（与 sp_channel_map._SP_SRC_MAP_NAME 一致）
_SP_SRC_MAP_NAME: dict[str, str] = {
    "BaseColor": "basecolor",
    "Metallic": "metallic",
    "Roughness": "roughness",
    "AO": "ambientOcclusion",
    "Emissive": "emissive",
    "Opacity": "opacity",
    "Height": "height",
    "Specular": "specular",
}


def _sp_src_map_name(ch: str) -> str:
    """返回 SP 导出配置中的 srcMapName。"""
    return _SP_SRC_MAP_NAME.get(ch, ch.lower())


def build_export_config(
    mesh_name: str,
    channels: list[str],
    output_path: str,
    file_format: str = "tga",
    bit_depth: int = 8,
) -> dict:
    """生成 SP 导出配置 JSON。

    Args:
        mesh_name: 网格名称（用于命名模板）。
        channels: SP 通道名列表（如 ["BaseColor", "Normal", "Metallic"]）。
        output_path: 输出目录绝对路径。
        file_format: 输出格式（tga/png/exr）。
        bit_depth: 位深度。

    Returns:
        可传给 substance_painter.export.export_project_textures() 的 config dict。

    >>> config = build_export_config("Chair", ["BaseColor", "Normal"], "C:/out")
    >>> config["exportPath"]
    'C:/out'
    >>> len(config["exportList"][0]["maps"])
    2
    """
    try:
        from .sp_channel_map import get_export_suffix
    except ImportError:
        from sp_channel_map import get_export_suffix

    # 使用 virtualMap 自动合并烘焙贴图的通道
    # AO_Mixed: SP 内置 "Unreal Engine (Packed)" 预设验证可用
    _virtual_map = {
        "Normal": "Normal_DirectX",
        "AO": "AO_Mixed",
    }

    maps = []
    for ch in channels:
        suffix = get_export_suffix(ch)
        vm = _virtual_map.get(ch)
        if ch == "Normal":
            # Normal 使用 virtualMap 获取最终法线
            ch_list = [
                {"destChannel": c, "srcChannel": c,
                 "srcMapType": "virtualMap", "srcMapName": "Normal_DirectX"}
                for c in ("R", "G", "B")
            ]
        elif ch in ("BaseColor", "Emissive"):
            # 颜色通道：R/G/B 分量映射
            ch_list = [
                {"destChannel": c, "srcChannel": c,
                 "srcMapType": "documentMap", "srcMapName": _sp_src_map_name(ch)}
                for c in ("R", "G", "B")
            ]
        elif vm:
            # AO 使用 virtualMap 合并烘焙贴图（匹配 SP 内置预设：srcChannel="L"）
            ch_list = [{
                "destChannel": "L",
                "srcChannel": "L",
                "srcMapType": "virtualMap",
                "srcMapName": vm,
            }]
        else:
            # 灰度通道
            ch_list = [
                {"destChannel": "L", "srcChannel": "L",
                 "srcMapType": "documentMap", "srcMapName": _sp_src_map_name(ch)}
            ]
        maps.append({
            "fileName": f"T_{mesh_name}_$textureSet_{suffix}",
            "channels": ch_list,
        })

    config = {
        "exportPath": output_path,
        "exportShaderParams": False,
        "defaultExportPreset": "",
        "exportParameters": [
            {
                "parameters": {
                    "fileFormat": file_format,
                    "bitDepth": str(bit_depth),
                    "dithering": False,
                    "paddingAlgorithm": "diffusion",
                }
            }
        ],
        "exportList": [
            {
                "rootPath": "",
                "filter": {"outputMaps": [m["fileName"] for m in maps]},
                "maps": maps,
            }
        ],
    }
    return config


def extract_channels_from_materials(materials: list[dict], parameter_bindings: dict[str, str] | None = None) -> list[str]:
    """从材质信息中提取所有使用的 SP 通道名（去重保序）。

    优先使用每个 material 自身的 parameter_bindings（per-material），
    其次使用传入的全局 parameter_bindings（SM fallback），
    最后使用硬编码映射。

    支持 packed channel suffix（如 "Packed_Texture.R"）：自动展开为各拆分通道。

    Args:
        materials: UE 数据包中的 materials 列表。
        parameter_bindings: 可选的全局 fallback 映射 {suffix: ue_param_name}。

    Returns:
        去重的 SP 通道名列表。

    >>> mats = [{"textures": [{"texture_property_name": "BaseColor"}, {"texture_property_name": "Normal"}]}]
    >>> extract_channels_from_materials(mats)
    ['BaseColor', 'Normal']
    """
    try:
        from .sp_channel_map import map_ue_to_sp, map_ue_to_sp_with_bindings, resolve_packed_channels
    except ImportError:
        from sp_channel_map import map_ue_to_sp, map_ue_to_sp_with_bindings, resolve_packed_channels

    seen = set()
    channels = []
    for mat in materials:
        # per-material bindings 优先，fallback 到全局
        effective_bindings = mat.get("parameter_bindings") or parameter_bindings
        tex_defs = mat.get("texture_definitions")
        for tex in mat.get("textures", []):
            prop = tex.get("texture_property_name", "")
            # 检查是否有 packed 通道拆分
            if effective_bindings:
                packed = resolve_packed_channels(prop, effective_bindings, tex_defs)
                if packed:
                    for sp_ch, _ in packed:
                        if sp_ch not in seen:
                            seen.add(sp_ch)
                            channels.append(sp_ch)
                    continue
                sp_ch = map_ue_to_sp_with_bindings(prop, effective_bindings)
            else:
                sp_ch = map_ue_to_sp(prop)
            if sp_ch not in seen:
                seen.add(sp_ch)
                channels.append(sp_ch)
    return channels


# ---------------------------------------------------------------------------
# SP API 函数（🎨 需在 SP 中人工测试）
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 模块级 — 暂存待处理的 UE 数据（事件回调使用）
# ---------------------------------------------------------------------------
_pending_ue_data: dict | None = None


def _compute_default_resolution(data: dict) -> int | None:
    """从 UE 数据中提取材质贴图的最大实际分辨率。

    遍历所有材质的 textures[].texture_size，返回最大值，
    并钳制到 SP 允许的范围 [128, 4096]。
    用于 project.Settings.default_texture_resolution 和 TextureSet 分辨率。
    若无 texture_size 信息则返回 None。
    """
    _SP_MIN_RES = 128
    _SP_MAX_RES = 4096
    max_val = 0
    for mat in data.get("materials", []):
        for tex in mat.get("textures", []):
            size = tex.get("texture_size")
            if isinstance(size, int) and size > 0:
                max_val = max(max_val, size)
    if max_val <= 0:
        return None
    return max(min(max_val, _SP_MAX_RES), _SP_MIN_RES)


_from_ue_pending: bool = False
_created_from_ue_session: bool = False


def reset_ue_session():
    """重置会话级 UE 标记。在项目关闭时调用。"""
    global _created_from_ue_session, _from_ue_pending
    _created_from_ue_session = False
    _from_ue_pending = False


def receive_from_ue(json_str: str, mesh_path: str) -> None:
    """从 UE 接收数据并在 SP 中执行完整的项目创建流程。

    此函数在 SP Remote Scripting 环境中执行。
    project.create() 是异步的，不能用 time.sleep() 轮询（会阻塞主线程/事件循环）。
    改用 ProjectEditionEntered 事件回调，在项目完全就绪后处理贴图。

    Args:
        json_str: UE 发送的材质信息 JSON。
        mesh_path: FBX 文件绝对路径。
    """
    global _pending_ue_data, _from_ue_pending, _created_from_ue_session
    import substance_painter.project as project
    import substance_painter.event

    _created_from_ue_session = True

    # 解析数据
    data = parse_ue_data(json_str)
    mesh_name = data["static_mesh"]
    sm_profile = data.get("config_profile", "")
    sm_has_bindings = bool(data.get("parameter_bindings"))
    print(f'[SPsync] receive_from_ue: mesh={mesh_name}, materials={len(data.get("materials", []))}')
    print(f'[SPsync]   SM fallback: config_profile={sm_profile or "(无)"}  parameter_bindings={"有" if sm_has_bindings else "无"}')

    # 日志：列出每个材质名称及其 per-material bindings
    for i, mat in enumerate(data.get("materials", [])):
        mat_name = mat.get("material_name", "?")
        slot_name = mat.get("material_slot_name", "")
        tex_count = len(mat.get("textures", []))
        mi_profile = mat.get("config_profile", "")
        mi_has_bindings = bool(mat.get("parameter_bindings"))
        print(f'[SPsync]   材质[{i}] slot={slot_name or "?"}  name={mat_name}  textures={tex_count}  profile={mi_profile or "(继承SM)"}  bindings={"有" if mi_has_bindings else "(继承SM)"}')

    # 暂存数据，等项目就绪后由回调处理
    _pending_ue_data = data

    # 注册回调：ProjectEditionEntered 在项目完全可编辑时触发（texture set 已就绪）
    substance_painter.event.DISPATCHER.connect(
        substance_painter.event.ProjectEditionEntered,
        _on_project_ready,
    )
    print('[SPsync] 已注册 ProjectEditionEntered 回调')

    _from_ue_pending = True

    # ⑤ 创建 SP 项目（异步，立即返回）
    # 从 texture_definitions 中提取最大分辨率用于项目默认设置
    default_res = _compute_default_resolution(data)
    settings_kwargs = dict(
        import_cameras=False,
        normal_map_format=project.NormalMapFormat.DirectX,
    )
    if default_res:
        settings_kwargs["default_texture_resolution"] = default_res
        print(f'[SPsync] 项目默认分辨率: {default_res}')
    settings = project.Settings(**settings_kwargs)
    print(f'[SPsync] 创建 SP 项目: {mesh_path}')
    project.create(mesh_path, settings=settings)
    print('[SPsync] project.create() 已调用，等待项目就绪...')


def _on_project_ready(state) -> None:
    """ProjectEditionEntered 回调 — 项目完全就绪，处理贴图。

    三阶段流程（性能优化：I/O 与计算分离）：
      Phase 0 — 预处理：匹配 TextureSet、解析 packed 通道、预热 Filter 缓存
      Phase 1 — 批量导入：集中所有贴图 import_project_resource()（全局去重）
      Phase 2 — 批量创建图层：从缓存取资源引用，零 I/O 创建 Fill Layer
    """
    global _pending_ue_data, _from_ue_pending
    import substance_painter.event
    import substance_painter.project
    import substance_painter.resource as resource
    import substance_painter.textureset as textureset
    import substance_painter.layerstack as layerstack

    # 断开回调，避免重复触发
    substance_painter.event.DISPATCHER.disconnect(
        substance_painter.event.ProjectEditionEntered,
        _on_project_ready,
    )

    # 持久化 from_ue 标记到项目 metadata
    substance_painter.project.Metadata("sp_sync").set("from_ue", True)
    _from_ue_pending = False

    if _pending_ue_data is None:
        print('[SPsync] _on_project_ready: 无待处理数据')
        return

    data = _pending_ue_data
    _pending_ue_data = None
    print(f'[SPsync] 项目就绪，开始处理贴图...（材质数: {len(data.get("materials", []))}）')

    try:
        from .sp_channel_map import map_ue_to_sp, map_ue_to_sp_with_bindings, resolve_packed_channels
    except ImportError:
        from sp_channel_map import map_ue_to_sp, map_ue_to_sp_with_bindings, resolve_packed_channels

    # SM 级别 fallback bindings
    sm_bindings = data.get("parameter_bindings", {})

    # ── 建立 TextureSet 名称映射 ──
    all_ts = textureset.all_texture_sets()
    ts_name_map: dict[str, Any] = {}  # TextureSet.name() → TextureSet
    for ts in all_ts:
        ts_name_map[ts.name()] = ts
    ts_names = list(ts_name_map.keys())
    print(f'[SPsync] TextureSets ({len(ts_names)}): {ts_names}')

    # ── 根据 texture_definitions 设置 TextureSet 分辨率 ──
    default_res = _compute_default_resolution(data)
    if default_res:
        try:
            resolution = textureset.Resolution(default_res, default_res)
            for ts in all_ts:
                ts.set_resolution(resolution)
            print(f'[SPsync] TextureSet 分辨率已设置: {default_res}x{default_res}')
        except Exception as e:
            print(f'[SPsync] ⚠ 设置 TextureSet 分辨率失败: {e}')

    # =========================================================================
    # Phase 0 — 预处理：匹配 TextureSet + 解析 packed 通道 + 预热 Filter 缓存
    # =========================================================================
    print('[SPsync] Phase 0: 预处理...')

    # 预热 Grayscale Conversion Filter 缓存（避免在图层创建循环中首次查询）
    _find_grayscale_filter(resource)
    _needs_filter_retry = (_grayscale_filter_id is None)

    # 每个材质的预处理结果
    # mat_prep: [{mat, mat_bindings, resolve_channel, packed_tex_map, stack, matched_ts}, ...]
    mat_prep_list: list[dict] = []

    for mat in data.get("materials", []):
        mat_name = mat.get("material_name", "?")
        slot_name = mat.get("material_slot_name", "")

        # per-material bindings 优先，fallback 到 SM 级别
        mat_bindings = mat.get("parameter_bindings", {}) or sm_bindings
        mat_profile = mat.get("config_profile", data.get("config_profile", ""))

        # 匹配 TextureSet（优先用 slot_name）
        matched_ts_name = match_material_to_textureset(mat_name, ts_names, slot_name=slot_name or None)
        if matched_ts_name is None:
            # 单 TextureSet 时直接使用
            if len(all_ts) == 1:
                matched_ts_name = ts_names[0]
                print(f'[SPsync] ── 材质: {mat_name} (slot={slot_name}) → 唯一 TextureSet: {matched_ts_name} ──')
            else:
                print(f'[SPsync] ⚠ 材质 {mat_name} (slot={slot_name}) 无法匹配 TextureSet，跳过')
                continue
        else:
            print(f'[SPsync] ── 材质: {mat_name} (slot={slot_name}) → TextureSet: {matched_ts_name}  profile={mat_profile or "(无)"}  bindings={"有" if mat_bindings else "无"} ──')

        # 记录匹配到的 TextureSet 名称，供 Roundtrip Metadata 使用
        mat["_matched_ts_name"] = matched_ts_name

        # 获取对应的 stack
        matched_ts = ts_name_map[matched_ts_name]
        try:
            stacks = matched_ts.all_stacks()
            if not stacks:
                print(f'[SPsync] ⚠ TextureSet {matched_ts_name} 无 stack，跳过')
                continue
            stack = stacks[0]
        except Exception as e:
            print(f'[SPsync] ⚠ 获取 TextureSet {matched_ts_name} 的 stack 失败: {e}')
            continue

        # 构建映射函数
        if mat_bindings:
            def resolve_channel(prop_name: str, _b=mat_bindings) -> str:
                return map_ue_to_sp_with_bindings(prop_name, _b)
        else:
            def resolve_channel(prop_name: str) -> str:
                return map_ue_to_sp(prop_name)

        # per-material texture_definitions
        mat_tex_defs = mat.get("texture_definitions") or data.get("texture_definitions")

        # ── 预解析 packed 通道拆分 ──
        packed_tex_map: dict[str, list[tuple[str, dict[str, float]]]] = {}
        if mat_bindings:
            for tex_info in mat.get("textures", []):
                prop_name = tex_info.get("texture_property_name", "")
                if prop_name and prop_name not in packed_tex_map:
                    channels_list = resolve_packed_channels(prop_name, mat_bindings, mat_tex_defs)
                    if channels_list:
                        packed_tex_map[prop_name] = channels_list
            if packed_tex_map:
                print(f'[SPsync]   Packed 贴图检测: {list(packed_tex_map.keys())}')

        mat_prep_list.append({
            "mat": mat,
            "mat_bindings": mat_bindings,
            "resolve_channel": resolve_channel,
            "packed_tex_map": packed_tex_map,
            "stack": stack,
            "matched_ts": matched_ts,
        })

    # Phase 1-2 + 后处理委托给可延迟的函数
    _run_phases_1_2(
        data, mat_prep_list, resource, textureset, layerstack,
        needs_filter_retry=_needs_filter_retry,
    )


# ---------------------------------------------------------------------------
# 延迟重试最大次数与间隔（ms）
# ---------------------------------------------------------------------------
_FILTER_RETRY_MAX = 15
_FILTER_RETRY_INTERVAL_MS = 200


def _run_phases_1_2(
    data: dict,
    mat_prep_list: list,
    resource,
    textureset,
    layerstack,
    *,
    needs_filter_retry: bool = False,
    _attempt: int = 0,
) -> None:
    """Phase 1-2 + 后处理。

    若 Grayscale Conversion Filter 尚未就绪且存在 packed 贴图需求，
    通过 QTimer.singleShot 延迟重试（非阻塞），最多 _FILTER_RETRY_MAX 次。
    """
    # --- 检查是否有 packed 通道需要滤镜 ---
    has_packed = any(prep["packed_tex_map"] for prep in mat_prep_list)

    if needs_filter_retry and has_packed:
        # 再次尝试（事件循环已让出，搜索索引可能已加载）
        _find_grayscale_filter(resource)
        if _grayscale_filter_id is None:
            _attempt += 1
            if _attempt < _FILTER_RETRY_MAX:
                print(f'[SPsync] ⏳ Grayscale Conversion Filter 尚未就绪，'
                      f'{_FILTER_RETRY_INTERVAL_MS}ms 后重试...（{_attempt}/{_FILTER_RETRY_MAX}）')
                from PySide6.QtCore import QTimer
                QTimer.singleShot(
                    _FILTER_RETRY_INTERVAL_MS,
                    lambda: _run_phases_1_2(
                        data, mat_prep_list, resource, textureset, layerstack,
                        needs_filter_retry=True, _attempt=_attempt,
                    ),
                )
                return  # 让出事件循环
            else:
                print(f'[SPsync] ⚠ Grayscale Conversion Filter 仍未就绪'
                      f'（已等待 {_attempt * _FILTER_RETRY_INTERVAL_MS}ms），'
                      f'Packed 通道拆分将跳过')
        else:
            print(f'[SPsync] Grayscale Conversion Filter 就绪'
                  f'（第 {_attempt + 1} 次延迟后）')

    # =========================================================================
    # Phase 1 — 批量导入：收集所有贴图路径（全局去重），集中 I/O
    # =========================================================================
    print('[SPsync] Phase 1: 批量导入贴图...')

    # 全局资源缓存（跨材质去重）
    imported_resources: dict[str, Any] = {}

    # 收集所有需要导入的贴图路径（去重）
    all_export_paths: set[str] = set()
    for prep in mat_prep_list:
        for tex_info in prep["mat"].get("textures", []):
            export_path = tex_info.get("texture_export_path", "")
            if export_path:
                all_export_paths.add(export_path)

    print(f'[SPsync]   共 {len(all_export_paths)} 张贴图需导入')

    # 集中执行所有导入（I/O 密集阶段）
    for export_path in all_export_paths:
        try:
            res = resource.import_project_resource(
                export_path, resource.Usage.TEXTURE
            )
            imported_resources[export_path] = res
            print(f'[SPsync]   资源导入成功: {res.identifier()}')
        except Exception as e:
            print(f'[SPsync]   资源导入失败: {export_path} — {e}')

    print(f'[SPsync]   导入完成: {len(imported_resources)}/{len(all_export_paths)} 成功')

    # =========================================================================
    # Phase 2 — 批量创建图层：从缓存取资源引用，零 I/O
    # =========================================================================
    print('[SPsync] Phase 2: 创建图层...')

    for prep in mat_prep_list:
        mat = prep["mat"]
        packed_tex_map = prep["packed_tex_map"]
        stack = prep["stack"]
        resolve_channel = prep["resolve_channel"]
        matched_ts = prep["matched_ts"]

        for tex_info in mat.get("textures", []):
            export_path = tex_info.get("texture_export_path", "")
            if not export_path:
                print(f'[SPsync] 跳过无导出路径的贴图: {tex_info.get("texture_name", "?")}')
                continue

            prop_name = tex_info["texture_property_name"]
            tex_name = tex_info["texture_name"]

            # 从全局缓存取资源引用（Phase 1 已导入）
            res = imported_resources.get(export_path)
            if res is None:
                print(f'[SPsync]   跳过未成功导入的贴图: {tex_name}')
                continue

            # ── Packed Texture 通道拆分流程 ──
            if prop_name in packed_tex_map:
                packed_channels = packed_tex_map[prop_name]
                print(f'[SPsync]   Packed 贴图: {tex_name} → 拆分为 {len(packed_channels)} 个通道')
                for sp_ch_name, weights in packed_channels:
                    _create_fill_with_filter(
                        layerstack, textureset, resource, stack,
                        res, tex_name, sp_ch_name, weights,
                    )
                continue

            # ── 普通贴图流程 ──
            sp_channel_name = resolve_channel(prop_name)
            print(f'[SPsync]   贴图: {tex_name} → param={prop_name} → channel={sp_channel_name}')

            # 获取通道类型并确保存在
            try:
                channel_type = getattr(textureset.ChannelType, sp_channel_name)
            except AttributeError:
                print(f'[SPsync]   未知通道类型: {sp_channel_name}')
                continue
            _ensure_channel_exists(stack, textureset, channel_type, sp_channel_name)

            # 创建 Fill Layer
            try:
                position = layerstack.InsertPosition.from_textureset_stack(stack)
                fill_layer = layerstack.insert_fill(position)
                fill_layer.set_name(f"{tex_name}_{sp_channel_name}")
                print(f'[SPsync]   Fill Layer 创建成功')
            except Exception as e:
                print(f'[SPsync]   Fill Layer 创建失败: {e}')
                continue

            # 分配贴图到通道
            try:
                fill_layer.set_source(channel_type, res.identifier())
                print(f'[SPsync]   通道分配成功: {sp_channel_name}')
            except Exception as e:
                print(f'[SPsync]   通道分配失败: {e}')

    # ⑦ 配置导出预设
    mesh_name = data["static_mesh"]
    channels = extract_channels_from_materials(data.get("materials", []))
    output_dir = _compute_export_path(data)
    export_config = build_export_config(mesh_name, channels, output_dir)

    # ⑧ 存储 UE 材质定义到 SP 项目 Metadata（用于 Round-Trip Sync）
    try:
        import substance_painter.project
        roundtrip_data = build_roundtrip_metadata(data)
        metadata = substance_painter.project.Metadata("sp_sync")
        metadata.set("ue_material_defs", json.dumps(roundtrip_data, ensure_ascii=False))
        print(f'[SPsync] UE 材质定义已写入 Metadata（{len(roundtrip_data.get("materials", []))} 个材质）')
    except Exception as e:
        print(f'[SPsync] ⚠ Metadata 写入失败: {e}')

    print(f'[SPsync] 贴图处理完成')


# ---------------------------------------------------------------------------
# Grayscale Conversion Filter 通道拆分辅助
# ---------------------------------------------------------------------------

# 单通道格式：探测确认 L8 对所有灰度通道有效
_DEFAULT_CHANNEL_FORMAT_NAME = "L8"
# 颜色通道应使用 sRGB8 格式
_COLOR_CHANNEL_FORMAT_NAME = "sRGB8"
# 需要 sRGB 颜色格式的通道集合
_COLOR_CHANNELS = {"BaseColor", "Emissive"}


def _ensure_channel_exists(stack, textureset, channel_type, channel_name: str) -> None:
    """确保 TextureSet Stack 中存在指定通道，不存在则添加。

    颜色通道（BaseColor, Emissive）使用 sRGB8，灰度通道使用 L8。
    """
    try:
        fmt_name = _COLOR_CHANNEL_FORMAT_NAME if channel_name in _COLOR_CHANNELS else _DEFAULT_CHANNEL_FORMAT_NAME
        fmt = getattr(textureset.ChannelFormat, fmt_name)
        stack.add_channel(channel_type, fmt)
        print(f'[SPsync]     通道添加: {channel_name} ({fmt_name})')
    except Exception:
        # 通道已存在或添加失败（已存在是正常的）
        pass


# Grayscale Conversion Filter 搜索查询
_GRAYSCALE_FILTER_QUERY = 'u:filter n:"Grayscale Conversion"'
# 缓存已找到的 Filter ResourceID（模块级，避免重复搜索）
_grayscale_filter_id = None


def _find_grayscale_filter(resource):
    """查找 Grayscale Conversion Filter 的 ResourceID（带缓存，单次尝试）。"""
    global _grayscale_filter_id
    if _grayscale_filter_id is not None:
        return _grayscale_filter_id
    results = resource.search(_GRAYSCALE_FILTER_QUERY)
    if not results:
        return None
    _grayscale_filter_id = results[0].identifier()
    print(f'[SPsync] Grayscale Conversion Filter: {_grayscale_filter_id}')
    return _grayscale_filter_id


def _create_fill_with_filter(
    layerstack, textureset, resource, stack,
    tex_resource, tex_name: str, sp_channel_name: str,
    grayscale_weights: dict[str, float],
) -> bool:
    """创建 Fill Layer，以 Grayscale Conversion 滤镜作为通道材质源实现通道拆分。

    架构：
      Fill Layer (Split mode)
        └─ set_source(ChannelType, grayscale_filter_id)
             ├─ SourceSubstance.set_source("input", packed_tex)  # 连接贴图
             └─ set_parameters({grayscale_type:1, RGBA weights})  # 权重提取

    Args:
        layerstack: substance_painter.layerstack 模块。
        textureset: substance_painter.textureset 模块。
        resource: substance_painter.resource 模块。
        stack: 目标 TextureSet 的 Stack。
        tex_resource: 已导入的贴图资源。
        tex_name: 贴图显示名。
        sp_channel_name: 目标 SP 通道名（如 "Metallic"）。
        grayscale_weights: Grayscale Conversion 的 RGBA 权重。

    Returns:
        True 成功，False 失败。
    """
    # 查找 Grayscale Conversion Filter
    filter_id = _find_grayscale_filter(resource)
    if filter_id is None:
        return False

    # 确保目标通道存在
    try:
        channel_type = getattr(textureset.ChannelType, sp_channel_name)
    except AttributeError:
        print(f'[SPsync]     未知通道类型: {sp_channel_name}')
        return False

    _ensure_channel_exists(stack, textureset, channel_type, sp_channel_name)

    # 创建 Fill Layer
    try:
        position = layerstack.InsertPosition.from_textureset_stack(stack)
        fill_layer = layerstack.insert_fill(position)
        fill_layer.set_name(f"{tex_name}_{sp_channel_name}")
    except Exception as e:
        print(f'[SPsync]     Fill Layer 创建失败 ({sp_channel_name}): {e}')
        return False

    # 设置 Grayscale Conversion 滤镜作为通道材质源（Split mode）
    try:
        fill_layer.set_source(channel_type, filter_id)
    except Exception as e:
        print(f'[SPsync]     滤镜源设置失败 ({sp_channel_name}): {e}')
        return False

    # 获取 SourceSubstance，连接贴图到滤镜 input
    try:
        source = fill_layer.get_source(channel_type)
        source.set_source("input", tex_resource.identifier())
    except Exception as e:
        print(f'[SPsync]     贴图连接失败 ({sp_channel_name}): {e}')
        return False

    # 设置 Grayscale Conversion 参数（RGBA 权重提取）
    try:
        source.set_parameters({
            "grayscale_type": 1,  # Channels Weights
            **grayscale_weights,
        })
        print(f'[SPsync]     通道拆分成功: {sp_channel_name} weights={grayscale_weights}')
    except Exception as e:
        print(f'[SPsync]     滤镜参数设置失败 ({sp_channel_name}): {e}')
        return False

    return True


def _compute_export_path(data: dict) -> str:
    """根据 UE 数据计算 SP 导出路径。

    尝试将 UE 贴图所在路径转换为本地文件系统路径。
    """
    # 使用第一个贴图的导出路径所在目录作为输出目录
    import os
    for mat in data.get("materials", []):
        for tex in mat.get("textures", []):
            export_path = tex.get("texture_export_path", "")
            if export_path:
                return os.path.dirname(export_path)
    return ""
