# -*- coding: utf-8 -*-
"""UE 材质参数名 ↔ SP ChannelType 映射。

纯逻辑模块，不依赖 substance_painter / unreal。
用于 sp_receive.py 将 UE 贴图参数名转换为 SP ChannelType 枚举名。
"""
from typing import Optional

# UE 材质参数名 → SP ChannelType 枚举名
# 枚举名对应 substance_painter.textureset.ChannelType 的属性名
UE_TO_SP_CHANNEL: dict[str, str] = {
    # 精确名
    "BaseColor": "BaseColor",
    "Normal": "Normal",
    "Metallic": "Metallic",
    "Roughness": "Roughness",
    "AO": "AO",
    "AmbientOcclusion": "AO",
    "Emissive": "Emissive",
    "EmissiveColor": "Emissive",
    "Opacity": "Opacity",
    "Height": "Height",
    "Specular": "Specular",
    # 带 _Texture 后缀的常见变体
    "BaseColor_Texture": "BaseColor",
    "Normal_Texture": "Normal",
    "Metallic_Texture": "Metallic",
    "Roughness_Texture": "Roughness",
    "AO_Texture": "AO",
    "AmbientOcclusion_Texture": "AO",
    "Emissive_Texture": "Emissive",
    "EmissiveColor_Texture": "Emissive",
    "Opacity_Texture": "Opacity",
    "Height_Texture": "Height",
    "Specular_Texture": "Specular",
    # 打包纹理（MRO = Metallic + Roughness + AO）
    "Packed_Texture": "Roughness",
    "Packed": "Roughness",
    "OcclusionRoughnessMetallic": "Roughness",
    "ORM": "Roughness",
    "MRO": "Roughness",
}

# SP 导出通道后缀映射（用于导出预设生成）
SP_CHANNEL_TO_SUFFIX: dict[str, str] = {
    "BaseColor": "BCO",
    "Normal": "N",
    "Metallic": "M",
    "Roughness": "R",
    "AO": "AO",
    "Emissive": "E",
    "Opacity": "O",
    "Height": "H",
    "Specular": "S",
}

# 默认 fallback 通道
DEFAULT_CHANNEL = "BaseColor"


def map_ue_to_sp(ue_param_name: str) -> str:
    """将 UE 材质参数名映射到 SP ChannelType 枚举名。

    匹配顺序：
    1. 精确匹配
    2. 大小写不敏感匹配
    3. 去掉 _Texture 后缀再匹配
    未知参数 fallback 到 DEFAULT_CHANNEL。

    >>> map_ue_to_sp("BaseColor")
    'BaseColor'
    >>> map_ue_to_sp("BaseColor_Texture")
    'BaseColor'
    >>> map_ue_to_sp("Normal_Texture")
    'Normal'
    >>> map_ue_to_sp("Packed_Texture")
    'Roughness'
    >>> map_ue_to_sp("basecolor")
    'BaseColor'
    >>> map_ue_to_sp("AmbientOcclusion")
    'AO'
    >>> map_ue_to_sp("UnknownParam")
    'BaseColor'
    """
    # 精确匹配
    if ue_param_name in UE_TO_SP_CHANNEL:
        return UE_TO_SP_CHANNEL[ue_param_name]

    # 大小写不敏感
    lower = ue_param_name.lower()
    for key, value in UE_TO_SP_CHANNEL.items():
        if key.lower() == lower:
            return value

    # 去掉 _Texture 后缀再匹配
    stripped = ue_param_name
    if stripped.endswith("_Texture") or stripped.endswith("_texture"):
        stripped = stripped.rsplit("_", 1)[0]
        if stripped in UE_TO_SP_CHANNEL:
            return UE_TO_SP_CHANNEL[stripped]
        stripped_lower = stripped.lower()
        for key, value in UE_TO_SP_CHANNEL.items():
            if key.lower() == stripped_lower:
                return value

    return DEFAULT_CHANNEL


def map_ue_to_sp_with_bindings(ue_param_name: str, parameter_bindings: dict[str, str]) -> str:
    """使用配置驱动的 parameter_bindings 将 UE 参数名映射到 SP ChannelType。

    parameter_bindings 格式: {suffix: ue_param_name}  例如 {"D": "BaseColor_Texture", "N": "Normal_Texture"}
    先构建反向映射 {ue_param_name: suffix}，再根据 suffix 查找已知的 SP 通道。

    如果 parameter_bindings 为空或无法匹配，fallback 到 map_ue_to_sp()。

    >>> map_ue_to_sp_with_bindings("BaseColor_Texture", {"D": "BaseColor_Texture", "N": "Normal_Texture"})
    'BaseColor'
    >>> map_ue_to_sp_with_bindings("Normal_Texture", {"D": "BaseColor_Texture", "N": "Normal_Texture"})
    'Normal'
    >>> map_ue_to_sp_with_bindings("Packed_Texture", {"MRO": "Packed_Texture"})
    'Roughness'
    >>> map_ue_to_sp_with_bindings("Unknown_Param", {"D": "BaseColor_Texture"})
    'BaseColor'
    >>> map_ue_to_sp_with_bindings("BaseColor_Texture", {})
    'BaseColor'
    """
    if not parameter_bindings:
        return map_ue_to_sp(ue_param_name)

    # 反向映射: ue_param_name → suffix
    reverse = {v: k for k, v in parameter_bindings.items()}
    suffix = reverse.get(ue_param_name)
    if suffix is None:
        # 大小写不敏感尝试
        lower = ue_param_name.lower()
        for v, k in reverse.items():
            if v.lower() == lower:
                suffix = k
                break

    if suffix is not None:
        # suffix → SP channel：已知 suffix 到 SP 通道的映射
        sp = _SUFFIX_TO_SP_CHANNEL.get(suffix.upper())
        if sp:
            return sp

    # fallback 到硬编码映射
    return map_ue_to_sp(ue_param_name)


# suffix → SP ChannelType（从配置 suffix 到 SP 通道名的映射）
_SUFFIX_TO_SP_CHANNEL: dict[str, str] = {
    "D": "BaseColor",
    "BCO": "BaseColor",
    "N": "Normal",
    "M": "Metallic",
    "R": "Roughness",
    "AO": "AO",
    "E": "Emissive",
    "O": "Opacity",
    "H": "Height",
    "S": "Specular",
    "MRO": "Roughness",    # Packed (Metallic+Roughness+AO)
    "ORM": "Roughness",
    "SSS": "Specular",     # SubsurfaceColor → 映射到 Specular（SP 最接近的通道）
}


def get_export_suffix(sp_channel: str) -> str:
    """获取 SP 通道对应的导出文件后缀。

    >>> get_export_suffix("BaseColor")
    'BCO'
    >>> get_export_suffix("Normal")
    'N'
    >>> get_export_suffix("Unknown")
    'BCO'
    """
    return SP_CHANNEL_TO_SUFFIX.get(sp_channel, SP_CHANNEL_TO_SUFFIX[DEFAULT_CHANNEL])


def get_all_sp_channels() -> list[str]:
    """返回所有支持的 SP 通道名列表。

    >>> "BaseColor" in get_all_sp_channels()
    True
    """
    return list(SP_CHANNEL_TO_SUFFIX.keys())


# ---------------------------------------------------------------------------
# Packed Texture 通道后缀解析
# ---------------------------------------------------------------------------

# .R / .G / .B / .A → Grayscale Conversion Filter 的 RGBA 权重
CHANNEL_SUFFIX_WEIGHTS: dict[str, dict[str, float]] = {
    "R": {"Red": 1.0, "Green": 0.0, "Blue": 0.0, "Alpha": 0.0},
    "G": {"Red": 0.0, "Green": 1.0, "Blue": 0.0, "Alpha": 0.0},
    "B": {"Red": 0.0, "Green": 0.0, "Blue": 1.0, "Alpha": 0.0},
    "A": {"Red": 0.0, "Green": 0.0, "Blue": 0.0, "Alpha": 1.0},
}


def parse_channel_suffix(binding_value: str) -> tuple[str, dict[str, float] | None]:
    """解析 parameter_bindings 值中的通道后缀。

    支持格式: "Packed_Texture.R" → ("Packed_Texture", {"Red":1.0, "Green":0.0, ...})
    无后缀:   "BaseColor_Texture" → ("BaseColor_Texture", None)

    Args:
        binding_value: parameter_bindings 中的值，如 "Packed_Texture.R"。

    Returns:
        (texture_param_name, channel_weights)
        channel_weights 为 None 表示不需要 Grayscale Conversion Filter。

    >>> parse_channel_suffix("Packed_Texture.R")
    ('Packed_Texture', {'Red': 1.0, 'Green': 0.0, 'Blue': 0.0, 'Alpha': 0.0})
    >>> parse_channel_suffix("Packed_Texture.G")
    ('Packed_Texture', {'Red': 0.0, 'Green': 1.0, 'Blue': 0.0, 'Alpha': 0.0})
    >>> parse_channel_suffix("Packed_Texture.B")
    ('Packed_Texture', {'Red': 0.0, 'Green': 0.0, 'Blue': 1.0, 'Alpha': 0.0})
    >>> parse_channel_suffix("Packed_Texture.A")
    ('Packed_Texture', {'Red': 0.0, 'Green': 0.0, 'Blue': 0.0, 'Alpha': 1.0})
    >>> parse_channel_suffix("BaseColor_Texture")
    ('BaseColor_Texture', None)
    >>> parse_channel_suffix("MRO_Texture.r")
    ('MRO_Texture', {'Red': 1.0, 'Green': 0.0, 'Blue': 0.0, 'Alpha': 0.0})
    >>> parse_channel_suffix("")
    ('', None)
    """
    if not binding_value:
        return (binding_value, None)

    # 检查最后两个字符是否是 ".R", ".G", ".B", ".A"
    if len(binding_value) >= 3 and binding_value[-2] == ".":
        suffix_char = binding_value[-1].upper()
        weights = CHANNEL_SUFFIX_WEIGHTS.get(suffix_char)
        if weights is not None:
            return (binding_value[:-2], dict(weights))

    return (binding_value, None)


def resolve_packed_channels(
    texture_param_name: str,
    parameter_bindings: dict[str, str],
    texture_definitions: list[dict] | None = None,
) -> list[tuple[str, dict[str, float]]]:
    """从 texture_definitions 或 parameter_bindings 中解析指定贴图的所有 Packed 通道拆分。

    优先使用 texture_definitions（通过 suffix 匹配 binding key，再读 channels 定义）；
    若无 texture_definitions 则 fallback 到旧版 .R/.G/.B 后缀解析（向后兼容）。

    Args:
        texture_param_name: UE 贴图参数名，如 "Packed_Texture"。
        parameter_bindings: 配置映射，如 {"MRO": "Packed_Texture", "D": "BaseColor_Texture"}。
        texture_definitions: 可选的 texture_definitions 列表（来自 config processing 段）。

    Returns:
        [(sp_channel_name, grayscale_weights), ...] — 空列表表示该贴图无 packed 拆分。

    >>> tex_defs = [{"suffix": "MRO", "name": "Packed_MRO", "channels": {
    ...     "R": {"from": "Metallic", "ch": "R"}, "G": {"from": "Roughness", "ch": "R"},
    ...     "B": {"from": "AmbientOcclusion", "ch": "R"}}}]
    >>> resolve_packed_channels("Packed_Texture", {"MRO": "Packed_Texture"}, tex_defs)
    [('Metallic', {'Red': 1.0, 'Green': 0.0, 'Blue': 0.0, 'Alpha': 0.0}), ('Roughness', {'Red': 0.0, 'Green': 1.0, 'Blue': 0.0, 'Alpha': 0.0}), ('AO', {'Red': 0.0, 'Green': 0.0, 'Blue': 1.0, 'Alpha': 0.0})]
    >>> resolve_packed_channels("BaseColor_Texture", {"D": "BaseColor_Texture"}, tex_defs)
    []
    >>> resolve_packed_channels("Packed_Texture", {})
    []
    """
    if not parameter_bindings:
        return []

    # 找到 binding key（suffix）→ 匹配 texture_param_name
    matched_suffix = None
    for suffix_key, binding_value in parameter_bindings.items():
        # 新格式: 值就是贴图参数名（无 .R/.G/.B）
        base_tex, weights = parse_channel_suffix(binding_value)
        if base_tex == texture_param_name:
            if weights is not None:
                # 旧格式 fallback（.R/.G/.B）— 直走旧逻辑
                matched_suffix = None
                break
            matched_suffix = suffix_key

    # ── 旧格式 fallback：.R/.G/.B 后缀 ──
    if matched_suffix is None:
        result: list[tuple[str, dict[str, float]]] = []
        for suffix_key, binding_value in parameter_bindings.items():
            base_tex, weights = parse_channel_suffix(binding_value)
            if weights is None:
                continue
            if base_tex != texture_param_name:
                continue
            sp_channel = _SUFFIX_TO_SP_CHANNEL.get(suffix_key.upper())
            if sp_channel:
                result.append((sp_channel, weights))
        return result

    # ── 新格式：从 texture_definitions 读取通道定义 ──
    if texture_definitions:
        for td in texture_definitions:
            if td.get("suffix") == matched_suffix:
                channels = td.get("channels", {})
                # 只有多源通道（不同 from）才算 packed
                sources = {
                    ch_def.get("from", "")
                    for ch_def in channels.values()
                    if isinstance(ch_def, dict) and "from" in ch_def
                }
                if len(sources) <= 1:
                    return []
                result = []
                for dest_ch, ch_def in channels.items():
                    if not isinstance(ch_def, dict) or "from" not in ch_def:
                        continue
                    source_name = ch_def["from"]
                    sp_channel = _SOURCE_TO_SP_CHANNEL.get(source_name)
                    if not sp_channel:
                        continue
                    weights = CHANNEL_SUFFIX_WEIGHTS.get(dest_ch.upper())
                    if weights:
                        result.append((sp_channel, dict(weights)))
                return result

    return []


# texture_definitions 中 "from" 值 → SP ChannelType 映射
_SOURCE_TO_SP_CHANNEL: dict[str, str] = {
    "BaseColor": "BaseColor",
    "Normal": "Normal",
    "Metallic": "Metallic",
    "Roughness": "Roughness",
    "AmbientOcclusion": "AO",
    "AO": "AO",
    "Emissive": "Emissive",
    "Opacity": "Opacity",
    "Height": "Height",
    "Specular": "Specular",
    "SubsurfaceColor": "Specular",
}


# ---------------------------------------------------------------------------
# Round-Trip Sync — 导出配置生成器
# ---------------------------------------------------------------------------

# SP 导出 API srcMapName 映射（由 probe_export_preset.py 探查验证）
# 内部通道名 → SP 导出配置中的 srcMapName
_SP_SRC_MAP_NAME: dict[str, str] = {
    "BaseColor": "basecolor",
    "Metallic": "metallic",
    "Roughness": "roughness",
    "AO": "ambientOcclusion",
    "Emissive": "emissive",
    "Opacity": "opacity",
    "Height": "height",
    "Specular": "specular",
    # Normal / AO / Height 优先走 virtualMap，见 _VIRTUAL_MAP_CHANNELS
}

# 使用 virtualMap 自动合并烘焙贴图的通道
# AO_Mixed: SP 内置 "Unreal Engine (Packed)" 预设验证可用
# Height: 无可靠 virtualMap（Mixed_Height 不在 Converted maps 中），使用 documentMap
_VIRTUAL_MAP_CHANNELS: dict[str, str] = {
    "Normal": "Normal_DirectX",
    "AO": "AO_Mixed",
}

# 颜色通道（RGB 三分量输出）
_COLOR_CHANNELS = {"BaseColor", "Normal", "Emissive"}


def build_roundtrip_export_maps(
    material: dict,
) -> list[dict]:
    """从单个 UE 材质定义生成 SP 导出 maps 配置。

    根据 parameter_bindings + texture_definitions，按 UE 原始贴图打包方式逆向生成
    SP export config 的 maps 列表，使导出格式与 UE 原始贴图一致。

    支持两种格式：
    - 新格式：parameter_bindings 使用纯贴图名（如 "MRO": "Packed_Texture"），
      配合 texture_definitions 中的 channels 定义推导打包关系。
    - 旧格式（向后兼容）：parameter_bindings 值含 .R/.G/.B 后缀。

    Args:
        material: UE 材质定义（含 parameter_bindings, textures, 可选 texture_definitions）。

    Returns:
        SP export maps 列表，每个元素是一个 map dict。

    >>> mat = {
    ...     "parameter_bindings": {"D": "BaseColor_Texture", "N": "Normal_Texture",
    ...                            "MRO": "Packed_Texture"},
    ...     "texture_definitions": [
    ...         {"suffix": "MRO", "name": "Packed_MRO", "channels": {
    ...             "R": {"from": "Metallic", "ch": "R"},
    ...             "G": {"from": "Roughness", "ch": "R"},
    ...             "B": {"from": "AmbientOcclusion", "ch": "R"}}}],
    ...     "textures": [
    ...         {"texture_property_name": "BaseColor_Texture", "texture_name": "T_Body_BaseColor", "texture_path": "/Game/T_Body_BaseColor"},
    ...         {"texture_property_name": "Normal_Texture", "texture_name": "T_Body_Normal", "texture_path": "/Game/T_Body_Normal"},
    ...         {"texture_property_name": "Packed_Texture", "texture_name": "T_Body_MRO", "texture_path": "/Game/T_Body_MRO"},
    ...     ]
    ... }
    >>> maps = build_roundtrip_export_maps(mat)
    >>> len(maps)
    3
    >>> names = [m["fileName"] for m in maps]
    >>> "T_Body_BaseColor" in names
    True
    >>> "T_Body_MRO" in names
    True
    >>> mro = [m for m in maps if m["fileName"] == "T_Body_MRO"][0]
    >>> len(mro["channels"])
    3
    """
    bindings = material.get("parameter_bindings", {})
    textures = material.get("textures", [])
    tex_defs = material.get("texture_definitions", [])
    if not bindings:
        return []

    # 建立 texture_property_name → texture_name 映射
    tex_name_map: dict[str, str] = {}
    for tex in textures:
        prop = tex.get("texture_property_name", "")
        if prop:
            tex_name_map[prop] = tex.get("texture_name", "")

    # 建立 suffix → texture_definition 映射
    td_by_suffix: dict[str, dict] = {}
    for td in tex_defs:
        s = td.get("suffix", "")
        if s:
            td_by_suffix[s] = td

    # 按 base_texture 分组 bindings
    groups: dict[str, list[tuple[str, str | None]]] = {}
    for suffix_key, binding_value in bindings.items():
        base_tex, weights = parse_channel_suffix(binding_value)
        suffix_char = None
        if weights is not None:
            # 旧格式 .R/.G/.B — 检测通道后缀
            for ch, w in CHANNEL_SUFFIX_WEIGHTS.items():
                if w == weights:
                    suffix_char = ch
                    break
            groups.setdefault(base_tex, []).append((suffix_key, suffix_char))
        else:
            # 新格式：从 texture_definitions 推导打包关系
            td = td_by_suffix.get(suffix_key)
            if td:
                channels = td.get("channels", {})
                sources = {
                    ch_def.get("from", "")
                    for ch_def in channels.values()
                    if isinstance(ch_def, dict) and "from" in ch_def
                }
                if len(sources) > 1:
                    # 多源 = packed 贴图
                    for dest_ch, ch_def in channels.items():
                        if not isinstance(ch_def, dict) or "from" not in ch_def:
                            continue
                        source_name = ch_def["from"]
                        sp_channel = _SOURCE_TO_SP_CHANNEL.get(source_name)
                        if sp_channel:
                            # 用 source_name 作为伪 suffix_key，dest_ch 作为 packed 通道
                            groups.setdefault(base_tex, []).append(
                                (f"_src_{source_name}", dest_ch.upper()))
                else:
                    groups.setdefault(base_tex, []).append((suffix_key, None))
            else:
                groups.setdefault(base_tex, []).append((suffix_key, None))

    maps = []
    for base_tex, entries in groups.items():
        tex_name = tex_name_map.get(base_tex, "")
        if not tex_name:
            continue

        has_packed = any(sc is not None for _, sc in entries)
        if has_packed:
            channels = []
            for suffix_key, suffix_char in entries:
                if suffix_char is None:
                    continue
                # 新格式伪 key: "_src_Metallic" → sp_channel="Metallic"
                if suffix_key.startswith("_src_"):
                    source_name = suffix_key[5:]
                    sp_channel = _SOURCE_TO_SP_CHANNEL.get(source_name)
                else:
                    sp_channel = _SUFFIX_TO_SP_CHANNEL.get(suffix_key.upper())
                if not sp_channel:
                    continue
                vm = _VIRTUAL_MAP_CHANNELS.get(sp_channel)
                if vm:
                    channels.append({
                        "destChannel": suffix_char,
                        "srcChannel": "L",
                        "srcMapType": "virtualMap",
                        "srcMapName": vm,
                    })
                else:
                    channels.append({
                        "destChannel": suffix_char,
                        "srcChannel": "L",
                        "srcMapType": "documentMap",
                        "srcMapName": _SP_SRC_MAP_NAME.get(sp_channel, sp_channel.lower()),
                    })
            if channels:
                maps.append({"fileName": tex_name, "channels": channels})
        else:
            for suffix_key, _ in entries:
                sp_channel = _SUFFIX_TO_SP_CHANNEL.get(suffix_key.upper())
                if not sp_channel:
                    continue
                vm = _VIRTUAL_MAP_CHANNELS.get(sp_channel)
                if sp_channel == "Normal":
                    channels = [
                        {"destChannel": c, "srcChannel": c,
                         "srcMapType": "virtualMap",
                         "srcMapName": "Normal_DirectX"}
                        for c in ("R", "G", "B")
                    ]
                elif sp_channel in _COLOR_CHANNELS:
                    channels = [
                        {"destChannel": c, "srcChannel": c,
                         "srcMapType": "documentMap",
                         "srcMapName": _SP_SRC_MAP_NAME.get(sp_channel, sp_channel.lower())}
                        for c in ("R", "G", "B")
                    ]
                elif vm:
                    # AO 使用 virtualMap 合并烘焙贴图（匹配 SP 内置预设：srcChannel="L"）
                    channels = [{
                        "destChannel": "L",
                        "srcChannel": "L",
                        "srcMapType": "virtualMap",
                        "srcMapName": vm,
                    }]
                else:
                    channels = [{
                        "destChannel": "L",
                        "srcChannel": "L",
                        "srcMapType": "documentMap",
                        "srcMapName": _SP_SRC_MAP_NAME.get(sp_channel, sp_channel.lower()),
                    }]
                maps.append({"fileName": tex_name, "channels": channels})
    return maps


def _compute_export_size_log2(ue_defs: dict) -> int | None:
    """从材质贴图的实际分辨率中提取最大值并计算 log2。

    遍历 textures[].texture_size，返回最大值的 log2，
    并钳制到 SP 允许的范围 [128, 4096]（即 log2 ∈ [7, 12]）。

    Returns:
        sizeLog2（int）或 None（无 texture_size 信息时）。

    >>> _compute_export_size_log2({"materials": [{"textures": [{"texture_size": 2048}]}]})
    11
    >>> _compute_export_size_log2({"materials": [{"textures": [{"texture_size": 32}]}]})
    7
    >>> _compute_export_size_log2({"materials": [{"textures": [{"texture_name": "T"}]}]}) is None
    True
    """
    import math
    _SP_MIN_RES = 128
    _SP_MAX_RES = 4096
    max_val = 0
    for mat in ue_defs.get("materials", []):
        for tex in mat.get("textures", []):
            size = tex.get("texture_size")
            if isinstance(size, int) and size > 0:
                max_val = max(max_val, size)
    if max_val <= 0:
        return None
    clamped = max(min(max_val, _SP_MAX_RES), _SP_MIN_RES)
    return int(math.log2(clamped))


def build_roundtrip_export_config(
    ue_defs: dict,
    export_path: str,
    file_format: str = "tga",
    bit_depth: str = "8",
) -> dict:
    """从完整 UE 材质定义生成 SP 导出配置。

    Args:
        ue_defs: Metadata 中存储的完整 UE 材质定义。
        export_path: 导出目录绝对路径。
        file_format: 输出格式。
        bit_depth: 位深度。

    Returns:
        可传给 substance_painter.export.export_project_textures() 的 config。

    >>> defs = {"materials": [{
    ...     "material_slot_name": "Body",
    ...     "parameter_bindings": {"D": "BaseColor_Texture"},
    ...     "textures": [{"texture_property_name": "BaseColor_Texture",
    ...                   "texture_name": "T_Body_BC", "texture_path": "/Game/T"}]
    ... }]}
    >>> cfg = build_roundtrip_export_config(defs, "/tmp/out")
    >>> cfg["exportPath"]
    '/tmp/out'
    >>> len(cfg["exportPresets"][0]["maps"])
    1
    """
    all_maps = []
    export_list = []
    for mat in ue_defs.get("materials", []):
        maps = build_roundtrip_export_maps(mat)
        all_maps.extend(maps)
        # 优先用记录的 TextureSet 名称，再 fallback 到 slot_name
        root = mat.get("texture_set_name") or mat.get("material_slot_name", "")
        if root:
            export_list.append({"rootPath": root})

    export_params: dict = {
        "fileFormat": file_format,
        "bitDepth": bit_depth,
        "dithering": True,
        "paddingAlgorithm": "infinite",
    }

    # 从 texture_definitions 中提取最大分辨率，注入 sizeLog2
    size_log2 = _compute_export_size_log2(ue_defs)
    if size_log2 is not None:
        export_params["sizeLog2"] = size_log2

    return {
        "exportShaderParams": False,
        "exportPath": export_path,
        "defaultExportPreset": "SPSyncRoundTrip",
        "exportPresets": [{
            "name": "SPSyncRoundTrip",
            "maps": all_maps,
        }],
        "exportList": export_list if export_list else [{"rootPath": ""}],
        "exportParameters": [{
            "parameters": export_params,
        }],
    }


def build_roundtrip_refresh_list(
    ue_defs: dict,
    exported_files: list[str],
) -> list[dict]:
    """从 UE 定义和导出文件列表构建 UE 刷新参数。

    将导出文件按文件名匹配回 UE 资产路径。
    若 texture_definitions 中定义了 max_resolution，会附加 max_texture_size 字段。

    Args:
        ue_defs: Metadata 中存储的 UE 材质定义。
        exported_files: SP 导出的文件路径列表。

    Returns:
        [{local_path, ue_folder, ue_name, max_texture_size?}, ...] 用于 refresh_textures()。

    >>> defs = {"materials": [{
    ...     "textures": [{"texture_name": "T_BC", "texture_path": "/Game/Tex/T_BC"}]
    ... }]}
    >>> files = ["C:/tmp/T_BC.tga", "C:/tmp/T_Unknown.tga"]
    >>> result = build_roundtrip_refresh_list(defs, files)
    >>> len(result)
    1
    >>> result[0]["ue_name"]
    'T_BC'
    >>> result[0]["ue_folder"]
    '/Game/Tex'
    """
    # 建立 texture_name → texture_path 映射
    name_to_path: dict[str, str] = {}
    # 建立 texture_name → max_texture_size 映射（通过 property_name → suffix → texture_def）
    name_to_max_size: dict[str, int] = {}
    for mat in ue_defs.get("materials", []):
        bindings = mat.get("parameter_bindings", {}) or ue_defs.get("parameter_bindings", {})
        tex_defs = mat.get("texture_definitions") or ue_defs.get("texture_definitions") or []
        # 建立 suffix → max_resolution 映射
        suffix_to_max_res: dict[str, int] = {}
        for td in tex_defs:
            suffix = td.get("suffix", "")
            max_res = td.get("max_resolution")
            if suffix and max_res:
                if isinstance(max_res, int):
                    suffix_to_max_res[suffix] = max_res
                elif isinstance(max_res, dict):
                    # 兼容旧格式
                    suffix_to_max_res[suffix] = max(max_res.get("width", 0), max_res.get("height", 0))
        # bindings: suffix → property_name；反转为 property_name → suffix
        prop_to_suffix: dict[str, str] = {}
        for suffix, prop_name in bindings.items():
            # 去掉 .R/.G/.B/.A 通道后缀
            base_prop = prop_name.split(".")[0]
            prop_to_suffix[base_prop] = suffix
        for tex in mat.get("textures", []):
            tex_name = tex.get("texture_name", "")
            tex_path = tex.get("texture_path", "")
            if tex_name and tex_path:
                name_to_path[tex_name] = tex_path
            # 查找 max_texture_size
            prop_name = tex.get("texture_property_name", "")
            suffix = prop_to_suffix.get(prop_name, "")
            max_res = suffix_to_max_res.get(suffix)
            if max_res and tex_name:
                name_to_max_size[tex_name] = max_res

    result = []
    for file_path in exported_files:
        # 从文件路径提取文件名（不含扩展名）
        normalized = file_path.replace("\\", "/")
        name_start = normalized.rfind("/") + 1
        name_end = normalized.rfind(".")
        if name_end <= name_start:
            file_name = normalized[name_start:]
        else:
            file_name = normalized[name_start:name_end]

        ue_path = name_to_path.get(file_name)
        if ue_path is None:
            continue

        # 提取 UE 目录
        folder_end = ue_path.rfind("/")
        ue_folder = ue_path[:folder_end] if folder_end > 0 else ue_path

        item = {
            "local_path": normalized,
            "ue_folder": ue_folder,
            "ue_name": file_name,
        }
        max_size = name_to_max_size.get(file_name)
        if max_size:
            item["max_texture_size"] = max_size
        result.append(item)
    return result
