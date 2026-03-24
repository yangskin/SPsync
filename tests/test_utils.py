# -*- coding: utf-8 -*-
"""
SPsync utils 模块单元测试。
运行: python -m pytest tests/test_utils.py -v
"""
import sys
import os

# 将插件根目录加入 sys.path，使 utils 可直接 import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import (
    extract_mesh_name,
    determine_material_type,
    validate_content_path,
    content_path_to_game_path,
    build_texture_name,
    build_texture_names,
    build_material_path,
    filter_udim_paths,
    parse_material_name_type,
    strip_asset_extension,
    match_asset_by_name,
)


# ========== extract_mesh_name ==========

class TestExtractMeshName:
    def test_standard_fbx_path(self):
        assert extract_mesh_name("/Game/Meshes/Chair.fbx") == "Chair"

    def test_windows_style_path(self):
        assert extract_mesh_name("C:/temp/sp_sync_temp/MyModel.fbx") == "MyModel"

    def test_deep_path(self):
        assert extract_mesh_name("/a/b/c/d/Weapon.obj") == "Weapon"

    def test_no_extension(self):
        assert extract_mesh_name("/Game/Meshes/Chair") == "Chair"

    def test_multiple_dots(self):
        assert extract_mesh_name("/Game/Meshes/My.Model.fbx") == "My.Model"

    def test_filename_only(self):
        assert extract_mesh_name("Chair.fbx") == "Chair"


# ========== determine_material_type ==========

class TestDetermineMaterialType:
    def test_opaque_no_special_channels(self):
        assert determine_material_type(["BaseColor", "Normal", "Roughness"]) == "opaque"

    def test_opaque_empty(self):
        assert determine_material_type([]) == "opaque"

    def test_masked_with_opacity(self):
        assert determine_material_type(["BaseColor", "Opacity", "Normal"]) == "masked"

    def test_translucency_takes_priority(self):
        # Translucency 出现在 Opacity 之后，应覆盖为 translucency
        assert determine_material_type(["Opacity", "Translucency"]) == "translucency"

    def test_translucency_alone(self):
        assert determine_material_type(["BaseColor", "Translucency"]) == "translucency"

    def test_opacity_after_translucency_becomes_masked(self):
        # 按照原始逻辑，遍历顺序决定结果：后出现的 Opacity 会覆盖 translucency
        # 这反映了原始代码的行为（非 if-elif）
        assert determine_material_type(["Translucency", "Opacity"]) == "masked"


# ========== validate_content_path ==========

class TestValidateContentPath:
    def test_valid_path(self):
        assert validate_content_path("D:/MyProject/Content/Textures") is True

    def test_invalid_path(self):
        assert validate_content_path("D:/MyProject/Assets/Textures") is False

    def test_empty_path(self):
        assert validate_content_path("") is False


# ========== content_path_to_game_path ==========

class TestContentPathToGamePath:
    def test_standard_conversion(self):
        assert content_path_to_game_path("D:/MyProject/Content/Textures/Wood") == "/Game/Textures/Wood"

    def test_content_root(self):
        assert content_path_to_game_path("D:/Project/Content") == "/Game"

    def test_no_content_returns_original(self):
        assert content_path_to_game_path("D:/Other/Path") == "D:/Other/Path"


# ========== build_texture_name / build_texture_names ==========

class TestBuildTextureName:
    def test_single_name(self):
        assert build_texture_name("Chair", "Wood", "BCO") == "T_Chair_Wood_BCO"

    def test_single_name_normal(self):
        assert build_texture_name("Chair", "Wood", "N") == "T_Chair_Wood_N"

    def test_full_set(self):
        names = build_texture_names("Chair", "Wood")
        assert names["bco"] == "T_Chair_Wood_BCO"
        assert names["mras"] == "T_Chair_Wood_MRAS"
        assert names["n"] == "T_Chair_Wood_N"
        assert names["es"] == "T_Chair_Wood_ES"

    def test_full_set_with_spaces_in_name(self):
        names = build_texture_names("My_Chair", "Dark_Wood")
        assert names["bco"] == "T_My_Chair_Dark_Wood_BCO"


# ========== build_material_path ==========

class TestBuildMaterialPath:
    def test_non_udim(self):
        assert build_material_path("/Game/Tex", "Chair", "Wood", False) == "/Game/Tex/MI_Chair_Wood"

    def test_udim(self):
        assert build_material_path("/Game/Tex", "Chair", "Wood", True) == "/Game/Tex/M_Chair_Wood"


# ========== filter_udim_paths ==========

class TestFilterUdimPaths:
    def test_filters_to_1001_only(self):
        paths = [
            "C:/temp/T_Mesh_Mat_BCO.1001.exr",
            "C:/temp/T_Mesh_Mat_BCO.1002.exr",
            "C:/temp/T_Mesh_Mat_BCO.1003.exr",
        ]
        result = filter_udim_paths(paths)
        assert len(result) == 1
        assert "1001" in result[0]

    def test_non_udim_paths_excluded(self):
        paths = ["C:/temp/T_Mesh_Mat_BCO.exr"]
        assert filter_udim_paths(paths) == []

    def test_mixed_paths(self):
        paths = [
            "C:/temp/T_Mesh_Mat_BCO.1001.exr",
            "C:/temp/T_Mesh_Mat_N.1001.exr",
            "C:/temp/T_Mesh_Mat_N.1002.exr",
        ]
        result = filter_udim_paths(paths)
        assert len(result) == 2

    def test_empty_list(self):
        assert filter_udim_paths([]) == []

    def test_underscore_1001_pattern(self):
        # 原始代码检查 path[path.rfind("_"):] 中是否包含 1001
        paths = ["C:/temp/T_Mesh_Mat_BCO_1001.exr"]
        result = filter_udim_paths(paths)
        assert len(result) == 1


# ========== parse_material_name_type ==========

class TestParseMaterialNameType:
    def test_opaque(self):
        name, mtype = parse_material_name_type("Wood:opaque")
        assert name == "Wood"
        assert mtype == "opaque"

    def test_masked(self):
        name, mtype = parse_material_name_type("Glass:masked")
        assert name == "Glass"
        assert mtype == "masked"

    def test_translucency(self):
        name, mtype = parse_material_name_type("Water:translucency")
        assert name == "Water"
        assert mtype == "translucency"


# ========== strip_asset_extension ==========

class TestStripAssetExtension:
    def test_standard(self):
        assert strip_asset_extension("/Game/Tex/T_Chair_BCO.T_Chair_BCO") == "/Game/Tex/T_Chair_BCO"

    def test_no_extension(self):
        assert strip_asset_extension("/Game/Tex/T_Chair_BCO") == "/Game/Tex/T_Chair_BCO"


# ========== match_asset_by_name ==========

class TestMatchAssetByName:
    def test_found(self):
        assets = [
            "/Game/Tex/T_Chair_BCO.T_Chair_BCO",
            "/Game/Tex/T_Chair_N.T_Chair_N",
        ]
        result = match_asset_by_name(assets, "T_Chair_BCO")
        assert result == "/Game/Tex/T_Chair_BCO.T_Chair_BCO"

    def test_not_found(self):
        assets = ["/Game/Tex/T_Chair_BCO.T_Chair_BCO"]
        assert match_asset_by_name(assets, "T_Chair_N") is None

    def test_empty_list(self):
        assert match_asset_by_name([], "anything") is None
