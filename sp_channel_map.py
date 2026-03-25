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
) -> list[tuple[str, dict[str, float]]]:
    """从 parameter_bindings 中解析指定贴图的所有 Packed 通道拆分。

    遍历 bindings，对每个 value 调用 parse_channel_suffix()，
    若基础贴图名匹配 texture_param_name，则收集 (sp_channel, weights)。

    Args:
        texture_param_name: UE 贴图参数名，如 "Packed_Texture"。
        parameter_bindings: 配置驱动的映射，如 {"M": "Packed_Texture.R", "R": "Packed_Texture.G"}。

    Returns:
        [(sp_channel_name, grayscale_weights), ...] — 空列表表示该贴图无 packed 拆分。

    >>> resolve_packed_channels("Packed_Texture", {"M": "Packed_Texture.R", "R": "Packed_Texture.G", "AO": "Packed_Texture.B"})
    [('Metallic', {'Red': 1.0, 'Green': 0.0, 'Blue': 0.0, 'Alpha': 0.0}), ('Roughness', {'Red': 0.0, 'Green': 1.0, 'Blue': 0.0, 'Alpha': 0.0}), ('AO', {'Red': 0.0, 'Green': 0.0, 'Blue': 1.0, 'Alpha': 0.0})]
    >>> resolve_packed_channels("BaseColor_Texture", {"D": "BaseColor_Texture", "N": "Normal_Texture"})
    []
    >>> resolve_packed_channels("Packed_Texture", {})
    []
    """
    if not parameter_bindings:
        return []

    result: list[tuple[str, dict[str, float]]] = []
    for suffix_key, binding_value in parameter_bindings.items():
        base_tex, weights = parse_channel_suffix(binding_value)
        if weights is None:
            continue
        if base_tex != texture_param_name:
            continue
        # suffix_key (如 "M") → SP 通道名 (如 "Metallic")
        sp_channel = _SUFFIX_TO_SP_CHANNEL.get(suffix_key.upper())
        if sp_channel:
            result.append((sp_channel, weights))
    return result


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
    # Normal 用 virtualMap + "Normal_DirectX"，不走此映射
}

# 颜色通道（RGB 三分量输出）
_COLOR_CHANNELS = {"BaseColor", "Normal", "Emissive"}


def build_roundtrip_export_maps(
    material: dict,
) -> list[dict]:
    """从单个 UE 材质定义生成 SP 导出 maps 配置。

    根据 parameter_bindings 和 textures，按 UE 原始贴图打包方式逆向生成
    SP export config 的 maps 列表，使导出格式与 UE 原始贴图一致。

    SP 导出 channel 格式（由 probe_export_preset.py 探查确认）：
    - srcMapName: SP 内部通道名（如 "basecolor"、"ambientOcclusion"）
    - srcChannel: 分量字符（颜色="R"/"G"/"B"，灰度="L"）
    - destChannel: 分量字符（颜色="R"/"G"/"B"，灰度="L"，packed=目标分量）
    - Normal: srcMapType="virtualMap", srcMapName="Normal_DirectX"

    Args:
        material: UE 材质定义（含 parameter_bindings 和 textures）。

    Returns:
        SP export maps 列表，每个元素是一个 map dict。

    >>> mat = {
    ...     "parameter_bindings": {"D": "BaseColor_Texture", "N": "Normal_Texture",
    ...                            "M": "Packed_Texture.R", "R": "Packed_Texture.G", "AO": "Packed_Texture.B"},
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
    if not bindings:
        return []

    # 建立 texture_property_name → texture_name 映射
    tex_name_map: dict[str, str] = {}
    for tex in textures:
        prop = tex.get("texture_property_name", "")
        if prop:
            tex_name_map[prop] = tex.get("texture_name", "")

    # 按 base_texture 分组 bindings
    # groups: {base_tex_param: [(suffix_key, channel_suffix_char_or_None), ...]}
    groups: dict[str, list[tuple[str, str | None]]] = {}
    for suffix_key, binding_value in bindings.items():
        base_tex, weights = parse_channel_suffix(binding_value)
        # weights 不为 None 表示 packed 通道
        suffix_char = None
        if weights is not None:
            # 检测是哪个通道后缀
            for ch, w in CHANNEL_SUFFIX_WEIGHTS.items():
                if w == weights:
                    suffix_char = ch
                    break
        groups.setdefault(base_tex, []).append((suffix_key, suffix_char))

    maps = []
    for base_tex, entries in groups.items():
        tex_name = tex_name_map.get(base_tex, "")
        if not tex_name:
            continue

        has_packed = any(sc is not None for _, sc in entries)
        if has_packed:
            # Packed 贴图：多个灰度通道打包到一个文件
            channels = []
            for suffix_key, suffix_char in entries:
                if suffix_char is None:
                    continue
                sp_channel = _SUFFIX_TO_SP_CHANNEL.get(suffix_key.upper())
                if not sp_channel:
                    continue
                channels.append({
                    "destChannel": suffix_char,
                    "srcChannel": "L",
                    "srcMapType": "documentMap",
                    "srcMapName": _SP_SRC_MAP_NAME.get(sp_channel, sp_channel.lower()),
                })
            if channels:
                maps.append({"fileName": tex_name, "channels": channels})
        else:
            # 普通贴图（单通道或颜色通道）
            for suffix_key, _ in entries:
                sp_channel = _SUFFIX_TO_SP_CHANNEL.get(suffix_key.upper())
                if not sp_channel:
                    continue
                if sp_channel == "Normal":
                    # Normal 使用 virtualMap 获取最终法线
                    channels = [
                        {"destChannel": c, "srcChannel": c,
                         "srcMapType": "virtualMap",
                         "srcMapName": "Normal_DirectX"}
                        for c in ("R", "G", "B")
                    ]
                elif sp_channel in _COLOR_CHANNELS:
                    # 颜色通道：R/G/B 三条映射
                    channels = [
                        {"destChannel": c, "srcChannel": c,
                         "srcMapType": "documentMap",
                         "srcMapName": _SP_SRC_MAP_NAME.get(sp_channel, sp_channel.lower())}
                        for c in ("R", "G", "B")
                    ]
                else:
                    # 灰度通道：单条 L 映射
                    channels = [{
                        "destChannel": "L",
                        "srcChannel": "L",
                        "srcMapType": "documentMap",
                        "srcMapName": _SP_SRC_MAP_NAME.get(sp_channel, sp_channel.lower()),
                    }]
                maps.append({"fileName": tex_name, "channels": channels})
    return maps


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
            "parameters": {
                "fileFormat": file_format,
                "bitDepth": bit_depth,
                "dithering": True,
                "paddingAlgorithm": "infinite",
            }
        }],
    }


def build_roundtrip_refresh_list(
    ue_defs: dict,
    exported_files: list[str],
) -> list[dict]:
    """从 UE 定义和导出文件列表构建 UE 刷新参数。

    将导出文件按文件名匹配回 UE 资产路径。

    Args:
        ue_defs: Metadata 中存储的 UE 材质定义。
        exported_files: SP 导出的文件路径列表。

    Returns:
        [{local_path, ue_folder, ue_name}, ...] 用于 refresh_textures()。

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
    for mat in ue_defs.get("materials", []):
        for tex in mat.get("textures", []):
            tex_name = tex.get("texture_name", "")
            tex_path = tex.get("texture_path", "")
            if tex_name and tex_path:
                name_to_path[tex_name] = tex_path

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

        result.append({
            "local_path": normalized,
            "ue_folder": ue_folder,
            "ue_name": file_name,
        })
    return result
