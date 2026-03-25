# -*- coding: utf-8 -*-
"""Round-Trip Sync 纯逻辑函数单元测试。

测试范围（🤖 全自动）：
- build_roundtrip_metadata()  — 元数据提取
- build_roundtrip_export_maps()  — 导出 maps 生成
- build_roundtrip_export_config()  — 完整导出配置
- build_roundtrip_refresh_list()  — UE 刷新参数构建
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from sp_receive import build_roundtrip_metadata
from sp_channel_map import (
    build_roundtrip_export_maps,
    build_roundtrip_export_config,
    build_roundtrip_refresh_list,
)


# ---------------------------------------------------------------------------
# 测试数据
# ---------------------------------------------------------------------------
UE_DATA_FULL = {
    "static_mesh": "SM_Body",
    "static_mesh_path": "/Game/Meshes/SM_Body",
    "config_profile": "Prop",
    "parameter_bindings": {"D": "BaseColor_Texture", "N": "Normal_Texture"},
    "materials": [
        {
            "material_name": "MI_Body",
            "material_slot_name": "Body",
            "config_profile": "Prop",
            "parameter_bindings": {
                "D": "BaseColor_Texture",
                "N": "Normal_Texture",
                "MRO": "Packed_Texture",
            },
            "texture_definitions": [
                {
                    "suffix": "MRO",
                    "name": "Packed_MRO",
                    "channels": {
                        "R": {"from": "Metallic", "ch": "R"},
                        "G": {"from": "Roughness", "ch": "R"},
                        "B": {"from": "AmbientOcclusion", "ch": "R"},
                    },
                }
            ],
            "textures": [
                {
                    "texture_property_name": "BaseColor_Texture",
                    "texture_path": "/Game/Textures/T_Body_BaseColor",
                    "texture_export_path": "C:/tmp/exports/T_Body_BaseColor.tga",
                    "texture_name": "T_Body_BaseColor",
                },
                {
                    "texture_property_name": "Normal_Texture",
                    "texture_path": "/Game/Textures/T_Body_Normal",
                    "texture_export_path": "C:/tmp/exports/T_Body_Normal.tga",
                    "texture_name": "T_Body_Normal",
                },
                {
                    "texture_property_name": "Packed_Texture",
                    "texture_path": "/Game/Textures/T_Body_MRO",
                    "texture_export_path": "C:/tmp/exports/T_Body_MRO.tga",
                    "texture_name": "T_Body_MRO",
                },
            ],
        }
    ],
}


# ---------------------------------------------------------------------------
# build_roundtrip_metadata
# ---------------------------------------------------------------------------
class TestBuildRoundtripMetadata:
    def test_keeps_essential_fields(self):
        rt = build_roundtrip_metadata(UE_DATA_FULL)
        assert rt["static_mesh"] == "SM_Body"
        assert rt["static_mesh_path"] == "/Game/Meshes/SM_Body"
        assert len(rt["materials"]) == 1

    def test_strips_export_path(self):
        rt = build_roundtrip_metadata(UE_DATA_FULL)
        tex = rt["materials"][0]["textures"][0]
        assert "texture_export_path" not in tex
        assert tex["texture_path"] == "/Game/Textures/T_Body_BaseColor"
        assert tex["texture_name"] == "T_Body_BaseColor"

    def test_preserves_bindings(self):
        rt = build_roundtrip_metadata(UE_DATA_FULL)
        mat = rt["materials"][0]
        assert mat["parameter_bindings"]["MRO"] == "Packed_Texture"
        assert mat["config_profile"] == "Prop"

    def test_preserves_texture_definitions(self):
        """texture_definitions 应保留到 roundtrip metadata 中。"""
        rt = build_roundtrip_metadata(UE_DATA_FULL)
        mat = rt["materials"][0]
        td = mat.get("texture_definitions")
        assert td is not None
        assert len(td) == 1
        assert td[0]["suffix"] == "MRO"
        assert "R" in td[0]["channels"]

    def test_stores_texture_set_name(self):
        """_matched_ts_name 应存为 texture_set_name。"""
        data_with_ts = {
            "static_mesh": "SM",
            "static_mesh_path": "/Game/SM",
            "materials": [{
                "material_name": "MI",
                "material_slot_name": "SlotA",
                "_matched_ts_name": "ActualTS",
                "textures": [],
            }],
        }
        rt = build_roundtrip_metadata(data_with_ts)
        assert rt["materials"][0]["texture_set_name"] == "ActualTS"

    def test_texture_set_name_empty_without_match(self):
        rt = build_roundtrip_metadata(UE_DATA_FULL)
        # UE_DATA_FULL 没有 _matched_ts_name，应为空字符串
        assert rt["materials"][0]["texture_set_name"] == ""

    def test_inherits_sm_bindings(self):
        """per-material bindings 为空时，fallback 到 SM 级别。"""
        data = {
            "static_mesh": "SM",
            "static_mesh_path": "/Game/SM",
            "parameter_bindings": {"D": "BC"},
            "materials": [
                {
                    "material_name": "MI",
                    "textures": [{"texture_property_name": "BC", "texture_path": "/Game/T", "texture_name": "T"}],
                }
            ],
        }
        rt = build_roundtrip_metadata(data)
        assert rt["materials"][0]["parameter_bindings"] == {"D": "BC"}

    def test_empty_materials(self):
        data = {"static_mesh": "SM", "static_mesh_path": "/Game/SM", "materials": []}
        rt = build_roundtrip_metadata(data)
        assert rt["materials"] == []


# ---------------------------------------------------------------------------
# build_roundtrip_export_maps
# ---------------------------------------------------------------------------
class TestBuildRoundtripExportMaps:
    def test_packed_texture_mro(self):
        mat = UE_DATA_FULL["materials"][0]
        # 复用含 per-material bindings 的材质
        maps = build_roundtrip_export_maps(mat)
        names = [m["fileName"] for m in maps]
        # 应生成 3 个 map: BaseColor, Normal, MRO
        assert "T_Body_BaseColor" in names
        assert "T_Body_Normal" in names
        assert "T_Body_MRO" in names

    def test_packed_channels_count(self):
        mat = UE_DATA_FULL["materials"][0]
        maps = build_roundtrip_export_maps(mat)
        mro = [m for m in maps if m["fileName"] == "T_Body_MRO"][0]
        # MRO 应有 3 个通道（M→R, R→G, AO→B）
        assert len(mro["channels"]) == 3
        dest_channels = {ch["destChannel"] for ch in mro["channels"]}
        assert dest_channels == {"R", "G", "B"}
        # 灰度源 srcChannel 应为 "L"，srcMapName 小写
        assert all(ch["srcChannel"] == "L" for ch in mro["channels"])
        names = {ch["srcMapName"] for ch in mro["channels"]}
        assert names == {"metallic", "roughness", "ambientOcclusion"}

    def test_color_channel_rgb(self):
        mat = UE_DATA_FULL["materials"][0]
        maps = build_roundtrip_export_maps(mat)
        bc = [m for m in maps if m["fileName"] == "T_Body_BaseColor"][0]
        # BaseColor 应有 R/G/B 三通道，srcChannel 为分量字符，srcMapName 小写
        assert len(bc["channels"]) == 3
        dest = {ch["destChannel"] for ch in bc["channels"]}
        assert dest == {"R", "G", "B"}
        assert all(ch["srcChannel"] == ch["destChannel"] for ch in bc["channels"])
        assert all(ch["srcMapName"] == "basecolor" for ch in bc["channels"])
        assert all(ch["srcMapType"] == "documentMap" for ch in bc["channels"])

    def test_normal_channel_rgb(self):
        mat = UE_DATA_FULL["materials"][0]
        maps = build_roundtrip_export_maps(mat)
        n = [m for m in maps if m["fileName"] == "T_Body_Normal"][0]
        # Normal 应用 virtualMap + Normal_DirectX
        assert len(n["channels"]) == 3
        dest = {ch["destChannel"] for ch in n["channels"]}
        assert dest == {"R", "G", "B"}
        assert all(ch["srcChannel"] == ch["destChannel"] for ch in n["channels"])
        assert all(ch["srcMapType"] == "virtualMap" for ch in n["channels"])
        assert all(ch["srcMapName"] == "Normal_DirectX" for ch in n["channels"])

    def test_empty_bindings(self):
        mat = {"parameter_bindings": {}, "textures": []}
        assert build_roundtrip_export_maps(mat) == []

    def test_no_bindings_key(self):
        mat = {"textures": []}
        assert build_roundtrip_export_maps(mat) == []

    def test_simple_grayscale(self):
        """单独灰度通道（非打包）。"""
        mat = {
            "parameter_bindings": {"H": "Height_Texture"},
            "textures": [{"texture_property_name": "Height_Texture", "texture_name": "T_Height", "texture_path": "/Game/T"}],
        }
        maps = build_roundtrip_export_maps(mat)
        assert len(maps) == 1
        assert maps[0]["fileName"] == "T_Height"
        assert len(maps[0]["channels"]) == 1
        ch = maps[0]["channels"][0]
        assert ch["destChannel"] == "L"
        assert ch["srcChannel"] == "L"
        assert ch["srcMapName"] == "height"


# ---------------------------------------------------------------------------
# build_roundtrip_export_config
# ---------------------------------------------------------------------------
class TestBuildRoundtripExportConfig:
    def test_basic_structure(self):
        rt = build_roundtrip_metadata(UE_DATA_FULL)
        cfg = build_roundtrip_export_config(rt, "/tmp/out")
        assert cfg["exportPath"] == "/tmp/out"
        assert cfg["defaultExportPreset"] == "SPSyncRoundTrip"
        assert len(cfg["exportPresets"]) == 1
        assert cfg["exportPresets"][0]["name"] == "SPSyncRoundTrip"

    def test_export_list(self):
        rt = build_roundtrip_metadata(UE_DATA_FULL)
        # UE_DATA_FULL 无 _matched_ts_name，fallback 到 material_slot_name
        cfg = build_roundtrip_export_config(rt, "/tmp/out")
        assert any(e["rootPath"] == "Body" for e in cfg["exportList"])

    def test_export_list_prefers_texture_set_name(self):
        """有 texture_set_name 时优先使用，而非 material_slot_name。"""
        defs = {"materials": [{
            "material_slot_name": "SlotA",
            "texture_set_name": "RealTS",
            "parameter_bindings": {"D": "BC_Tex"},
            "textures": [{"texture_property_name": "BC_Tex",
                          "texture_name": "T_BC", "texture_path": "/Game/T"}],
        }]}
        cfg = build_roundtrip_export_config(defs, "/tmp/out")
        assert cfg["exportList"][0]["rootPath"] == "RealTS"

    def test_maps_count(self):
        rt = build_roundtrip_metadata(UE_DATA_FULL)
        cfg = build_roundtrip_export_config(rt, "/tmp/out")
        maps = cfg["exportPresets"][0]["maps"]
        # 3 maps: BaseColor, Normal, MRO
        assert len(maps) == 3

    def test_custom_format(self):
        rt = build_roundtrip_metadata(UE_DATA_FULL)
        cfg = build_roundtrip_export_config(rt, "/tmp/out", file_format="png", bit_depth="16")
        params = cfg["exportParameters"][0]["parameters"]
        assert params["fileFormat"] == "png"
        assert params["bitDepth"] == "16"


# ---------------------------------------------------------------------------
# build_roundtrip_refresh_list
# ---------------------------------------------------------------------------
class TestBuildRoundtripRefreshList:
    def test_matches_exported_files(self):
        rt = build_roundtrip_metadata(UE_DATA_FULL)
        files = [
            "C:/tmp/sp_sync_temp/T_Body_BaseColor.tga",
            "C:/tmp/sp_sync_temp/T_Body_Normal.tga",
            "C:/tmp/sp_sync_temp/T_Body_MRO.tga",
        ]
        result = build_roundtrip_refresh_list(rt, files)
        assert len(result) == 3
        names = {r["ue_name"] for r in result}
        assert names == {"T_Body_BaseColor", "T_Body_Normal", "T_Body_MRO"}

    def test_skips_unknown_files(self):
        rt = build_roundtrip_metadata(UE_DATA_FULL)
        files = ["C:/tmp/T_Unknown.tga"]
        result = build_roundtrip_refresh_list(rt, files)
        assert len(result) == 0

    def test_extracts_ue_folder(self):
        rt = build_roundtrip_metadata(UE_DATA_FULL)
        files = ["C:/tmp/T_Body_BaseColor.tga"]
        result = build_roundtrip_refresh_list(rt, files)
        assert result[0]["ue_folder"] == "/Game/Textures"
        assert result[0]["ue_name"] == "T_Body_BaseColor"

    def test_handles_backslash_paths(self):
        rt = build_roundtrip_metadata(UE_DATA_FULL)
        files = ["C:\\tmp\\T_Body_BaseColor.tga"]
        result = build_roundtrip_refresh_list(rt, files)
        assert len(result) == 1
        assert "/" in result[0]["local_path"]  # 应已规范化



