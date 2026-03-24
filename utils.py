# -*- coding: utf-8 -*-
"""
SPsync 纯逻辑工具函数。
不依赖 Substance Painter / Unreal Engine / Qt 等外部 API。
"""
from typing import List, Tuple


def extract_mesh_name(mesh_path: str) -> str:
    """从文件路径中提取不含扩展名的文件名。

    >>> extract_mesh_name("/Game/Meshes/Chair.fbx")
    'Chair'
    >>> extract_mesh_name("C:/temp/sp_sync_temp/MyModel.fbx")
    'MyModel'
    """
    name_start = mesh_path.rfind("/") + 1
    name_end = mesh_path.rfind(".")
    if name_end <= name_start:
        return mesh_path[name_start:]
    return mesh_path[name_start:name_end]


def determine_material_type(channel_names: List[str]) -> str:
    """根据通道名列表判断材质类型。

    规则：
    - 含 Translucency → "translucency"
    - 含 Opacity (无 Translucency) → "masked"
    - 否则 → "opaque"

    与 SP 中 ChannelType 枚举的 .name 属性匹配。
    """
    material_type = "opaque"
    for channel in channel_names:
        if channel == "Opacity":
            material_type = "masked"
        if channel == "Translucency":
            material_type = "translucency"
    return material_type


def validate_content_path(path: str) -> bool:
    """校验路径是否包含 Content 目录。"""
    return "Content" in path


def content_path_to_game_path(file_path: str) -> str:
    """将本地 Content 路径转换为 UE /Game/ 路径。

    >>> content_path_to_game_path("D:/MyProject/Content/Textures/Wood")
    '/Game/Textures/Wood'
    """
    content_index = file_path.find("Content")
    if content_index == -1:
        return file_path
    return "/" + file_path[content_index:].replace("Content", "Game")


def build_texture_name(mesh_name: str, material_name: str, suffix: str) -> str:
    """构建纹理资产命名。

    >>> build_texture_name("Chair", "Wood", "BCO")
    'T_Chair_Wood_BCO'
    """
    return f"T_{mesh_name}_{material_name}_{suffix}"


def build_texture_names(mesh_name: str, material_name: str) -> dict:
    """构建一组完整的纹理资产名称。

    >>> names = build_texture_names("Chair", "Wood")
    >>> names["bco"]
    'T_Chair_Wood_BCO'
    """
    return {
        "bco": build_texture_name(mesh_name, material_name, "BCO"),
        "mras": build_texture_name(mesh_name, material_name, "MRAS"),
        "n": build_texture_name(mesh_name, material_name, "N"),
        "es": build_texture_name(mesh_name, material_name, "ES"),
    }


def build_material_path(target_path: str, mesh_name: str, material_name: str, udim: bool) -> str:
    """构建材质资产路径。

    UDIM 模式使用 M_ 前缀，非 UDIM 使用 MI_ 前缀。

    >>> build_material_path("/Game/Tex", "Chair", "Wood", False)
    '/Game/Tex/MI_Chair_Wood'
    >>> build_material_path("/Game/Tex", "Chair", "Wood", True)
    '/Game/Tex/M_Chair_Wood'
    """
    prefix = "M_" if udim else "MI_"
    return f"{target_path}/{prefix}{mesh_name}_{material_name}"


def filter_udim_paths(paths: List[str]) -> List[str]:
    """UDIM 过滤：只保留包含 1001 标记的路径（第一个 UDIM tile）。

    注意：只检查最后一个下划线之后的部分，与原始逻辑一致。

    >>> filter_udim_paths(["tex_1001.exr", "tex_1002.exr", "other.exr"])
    ['tex_1001.exr']
    """
    result = []
    for path in paths:
        tail = path[path.rfind("_"):]
        if "1001" in tail:
            result.append(path)
    return result


def parse_material_name_type(material_name_type: str) -> Tuple[str, str]:
    """解析 'MaterialName:Type' 格式的字符串。

    >>> parse_material_name_type("Wood:opaque")
    ('Wood', 'opaque')
    """
    parts = material_name_type.split(":")
    return parts[0], parts[1]


def strip_asset_extension(asset_path: str) -> str:
    """去除 UE 资产路径中的扩展名部分。

    >>> strip_asset_extension("/Game/Tex/T_Chair_Wood_BCO.T_Chair_Wood_BCO")
    '/Game/Tex/T_Chair_Wood_BCO'
    """
    dot_index = asset_path.rfind(".")
    if dot_index == -1:
        return asset_path
    return asset_path[:dot_index]


def match_asset_by_name(assets: List[str], name: str) -> str:
    """在资产列表中按名称匹配（不含扩展名）。

    >>> match_asset_by_name(["/Game/Tex/T_Chair_BCO.T_Chair_BCO"], "T_Chair_BCO")
    '/Game/Tex/T_Chair_BCO.T_Chair_BCO'
    >>> match_asset_by_name(["/Game/Tex/T_Chair_BCO.T_Chair_BCO"], "T_Chair_N") is None
    True
    """
    for asset in assets:
        asset_name = asset[asset.rfind("/") + 1 : asset.rfind(".")]
        if name == asset_name:
            return asset
    return None
