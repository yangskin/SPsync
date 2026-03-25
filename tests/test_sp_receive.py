# -*- coding: utf-8 -*-
"""sp_receive.py 纯逻辑部分单元测试。

测试范围（🤖 自动化）：
- 4.1 JSON 数据包解析 + 入参校验
- 4.2 导出配置 JSON 生成函数
"""
import json

import pytest

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sp_receive import (
    validate_ue_data,
    parse_ue_data,
    build_export_config,
    extract_channels_from_materials,
    match_material_to_textureset,
)


# ---------------------------------------------------------------------------
# 测试数据
# ---------------------------------------------------------------------------
VALID_DATA = {
    "static_mesh": "SM_Chair",
    "static_mesh_path": "/Game/Meshes/SM_Chair",
    "materials": [
        {
            "material_name": "MI_Chair_Wood",
            "material_path": "/Game/Materials/MI_Chair_Wood",
            "textures": [
                {
                    "texture_property_name": "BaseColor",
                    "texture_path": "/Game/Textures/T_Chair_Wood_BCO",
                    "texture_export_path": "C:/temp/T_Chair_Wood_BCO.tga",
                    "texture_name": "T_Chair_Wood_BCO",
                },
                {
                    "texture_property_name": "Normal",
                    "texture_path": "/Game/Textures/T_Chair_Wood_N",
                    "texture_export_path": "C:/temp/T_Chair_Wood_N.tga",
                    "texture_name": "T_Chair_Wood_N",
                },
            ],
        }
    ],
}


# ---------------------------------------------------------------------------
# 4.1 validate_ue_data
# ---------------------------------------------------------------------------
class TestValidateUeData:
    def test_valid_data_no_errors(self):
        assert validate_ue_data(VALID_DATA) == []

    def test_empty_dict(self):
        errors = validate_ue_data({})
        assert len(errors) >= 3  # 至少 3 个必填字段缺失

    def test_missing_static_mesh(self):
        data = {k: v for k, v in VALID_DATA.items() if k != "static_mesh"}
        errors = validate_ue_data(data)
        assert any("static_mesh" in e for e in errors)

    def test_missing_materials(self):
        data = {"static_mesh": "x", "static_mesh_path": "/y"}
        errors = validate_ue_data(data)
        assert any("materials" in e for e in errors)

    def test_materials_not_array(self):
        data = {"static_mesh": "x", "static_mesh_path": "/y", "materials": "wrong"}
        errors = validate_ue_data(data)
        assert any("数组" in e for e in errors)

    def test_material_missing_name(self):
        data = {
            "static_mesh": "x",
            "static_mesh_path": "/y",
            "materials": [{"textures": []}],
        }
        errors = validate_ue_data(data)
        assert any("material_name" in e for e in errors)

    def test_texture_missing_field(self):
        data = {
            "static_mesh": "x",
            "static_mesh_path": "/y",
            "materials": [
                {
                    "material_name": "M",
                    "textures": [{"texture_property_name": "BC"}],  # 缺少其他字段
                }
            ],
        }
        errors = validate_ue_data(data)
        assert len(errors) >= 1

    def test_empty_materials_valid(self):
        data = {"static_mesh": "x", "static_mesh_path": "/y", "materials": []}
        assert validate_ue_data(data) == []


class TestParseUeData:
    def test_valid_json(self):
        result = parse_ue_data(json.dumps(VALID_DATA))
        assert result["static_mesh"] == "SM_Chair"

    def test_invalid_json(self):
        with pytest.raises(ValueError, match="JSON"):
            parse_ue_data("not json")

    def test_validation_failure(self):
        with pytest.raises(ValueError, match="校验"):
            parse_ue_data("{}")


# ---------------------------------------------------------------------------
# 4.2 build_export_config
# ---------------------------------------------------------------------------
class TestBuildExportConfig:
    def test_basic_structure(self):
        config = build_export_config("Chair", ["BaseColor", "Normal"], "C:/out")
        assert config["exportPath"] == "C:/out"
        assert "exportList" in config
        assert len(config["exportList"]) == 1
        assert len(config["exportList"][0]["maps"]) == 2

    def test_channel_suffixes(self):
        config = build_export_config("Chair", ["BaseColor", "Normal", "Metallic"], "C:/out")
        filenames = [m["fileName"] for m in config["exportList"][0]["maps"]]
        assert any("BCO" in fn for fn in filenames)
        assert any("_N" in fn for fn in filenames)
        assert any("_M" in fn for fn in filenames)

    def test_mesh_name_in_filename(self):
        config = build_export_config("MyMesh", ["BaseColor"], "C:/out")
        filename = config["exportList"][0]["maps"][0]["fileName"]
        assert "MyMesh" in filename

    def test_custom_format(self):
        config = build_export_config("X", ["BaseColor"], "C:/out", file_format="png", bit_depth=16)
        params = config["exportParameters"][0]["parameters"]
        assert params["fileFormat"] == "png"
        assert params["bitDepth"] == "16"

    def test_empty_channels(self):
        config = build_export_config("X", [], "C:/out")
        assert len(config["exportList"][0]["maps"]) == 0

    def test_single_channel(self):
        config = build_export_config("Rock", ["Roughness"], "D:/export")
        maps = config["exportList"][0]["maps"]
        assert len(maps) == 1
        assert "R" in maps[0]["fileName"]  # Roughness suffix

    def test_export_path_preserved(self):
        config = build_export_config("X", ["BaseColor"], "/some/path/with spaces")
        assert config["exportPath"] == "/some/path/with spaces"


class TestExtractChannelsFromMaterials:
    def test_basic(self):
        channels = extract_channels_from_materials(VALID_DATA["materials"])
        assert "BaseColor" in channels
        assert "Normal" in channels

    def test_deduplicates(self):
        mats = [
            {"textures": [
                {"texture_property_name": "BaseColor"},
                {"texture_property_name": "BaseColor"},
            ]},
        ]
        channels = extract_channels_from_materials(mats)
        assert channels.count("BaseColor") == 1

    def test_preserves_order(self):
        mats = [
            {"textures": [
                {"texture_property_name": "Normal"},
                {"texture_property_name": "BaseColor"},
            ]},
        ]
        channels = extract_channels_from_materials(mats)
        assert channels[0] == "Normal"
        assert channels[1] == "BaseColor"

    def test_maps_aliases(self):
        mats = [{"textures": [{"texture_property_name": "AmbientOcclusion"}]}]
        channels = extract_channels_from_materials(mats)
        assert channels == ["AO"]

    def test_empty_materials(self):
        assert extract_channels_from_materials([]) == []

    def test_multi_material(self):
        mats = [
            {"textures": [{"texture_property_name": "BaseColor"}]},
            {"textures": [{"texture_property_name": "Normal"}, {"texture_property_name": "Metallic"}]},
        ]
        channels = extract_channels_from_materials(mats)
        assert len(channels) == 3


class TestExtractChannelsWithBindings:
    """测试 extract_channels_from_materials 的 parameter_bindings 参数。"""

    BINDINGS = {
        "D": "BaseColor_Texture",
        "N": "Normal_Texture",
        "MRO": "Packed_Texture",
        "H": "Height_Texture",
    }

    def test_with_bindings(self):
        mats = [{"textures": [
            {"texture_property_name": "BaseColor_Texture"},
            {"texture_property_name": "Normal_Texture"},
            {"texture_property_name": "Packed_Texture"},
        ]}]
        channels = extract_channels_from_materials(mats, self.BINDINGS)
        assert "BaseColor" in channels
        assert "Normal" in channels
        assert "Roughness" in channels

    def test_none_bindings_fallback(self):
        mats = [{"textures": [{"texture_property_name": "BaseColor"}]}]
        channels = extract_channels_from_materials(mats, None)
        assert channels == ["BaseColor"]

    def test_empty_bindings_fallback(self):
        mats = [{"textures": [{"texture_property_name": "Normal_Texture"}]}]
        channels = extract_channels_from_materials(mats, {})
        assert channels == ["Normal"]


# ---------------------------------------------------------------------------
# 5.1 match_material_to_textureset（slot_name 优先 + 材质名 fallback）
# ---------------------------------------------------------------------------
class TestMatchMaterialToTextureset:
    """测试 slot_name 优先的材质 → TextureSet 匹配。"""

    # ── slot_name 匹配（最高优先级）──
    def test_slot_name_exact_match(self):
        """slot_name 精确匹配 TextureSet。"""
        assert match_material_to_textureset("MI_Body", ["Body", "Weapon"], slot_name="Body") == "Body"

    def test_slot_name_case_insensitive(self):
        """slot_name 大小写不敏感匹配。"""
        assert match_material_to_textureset("MI_Body", ["body"], slot_name="Body") == "body"

    def test_slot_name_priority_over_material_name(self):
        """slot_name 匹配优先于 material_name 匹配。"""
        # MI_Body 能直接匹配 "MI_Body"，但 slot_name="Body" 应优先匹配 "Body"
        result = match_material_to_textureset("MI_Body", ["MI_Body", "Body"], slot_name="Body")
        assert result == "Body"

    # ── material_name fallback（无 slot_name 时）──
    def test_material_name_exact_match(self):
        assert match_material_to_textureset("MI_Body", ["MI_Body", "MI_Weapon"]) == "MI_Body"

    def test_strip_mi_prefix(self):
        """MI_Body → Body"""
        assert match_material_to_textureset("MI_Body", ["Body", "Weapon"]) == "Body"

    def test_case_insensitive(self):
        assert match_material_to_textureset("mi_body", ["MI_Body"]) == "MI_Body"

    def test_case_insensitive_stripped(self):
        assert match_material_to_textureset("MI_BODY", ["Body"]) == "Body"

    # ── 无匹配 ──
    def test_no_match(self):
        assert match_material_to_textureset("MI_Unknown", ["Body", "Weapon"]) is None

    def test_no_match_with_slot(self):
        assert match_material_to_textureset("MI_X", ["Body"], slot_name="Arm") is None

    def test_empty_textureset_list(self):
        assert match_material_to_textureset("MI_Body", []) is None

    def test_single_textureset_no_match(self):
        """不匹配时返回 None（不是 fallback 到唯一的 TextureSet）。"""
        assert match_material_to_textureset("MI_Arm", ["Body"]) is None

    # ── slot_name 为空时退化到 material_name 匹配 ──
    def test_empty_slot_name_fallback(self):
        assert match_material_to_textureset("MI_Body", ["Body"], slot_name="") == "Body"

    def test_none_slot_name_fallback(self):
        assert match_material_to_textureset("MI_Body", ["Body"], slot_name=None) == "Body"


# ---------------------------------------------------------------------------
# 5.2 extract_channels_from_materials 的 per-material bindings
# ---------------------------------------------------------------------------
class TestExtractChannelsPerMaterialBindings:
    """测试 per-material parameter_bindings 优先级。"""

    PROP_BINDINGS = {
        "D": "BaseColor_Texture",
        "N": "Normal_Texture",
        "MRO": "Packed_Texture",
        "H": "Height_Texture",
    }

    CHAR_BINDINGS = {
        "D": "BaseColor_Texture",
        "N": "Normal_Texture",
        "MRO": "Packed_Texture",
        "SSS": "SubsurfaceColor_Texture",
    }

    def test_per_material_bindings_used(self):
        """每个材质使用自己的 parameter_bindings。"""
        mats = [
            {
                "parameter_bindings": self.PROP_BINDINGS,
                "textures": [{"texture_property_name": "Height_Texture"}],
            },
            {
                "parameter_bindings": self.CHAR_BINDINGS,
                "textures": [{"texture_property_name": "SubsurfaceColor_Texture"}],
            },
        ]
        channels = extract_channels_from_materials(mats)
        assert "Height" in channels
        assert "Specular" in channels  # SSS → Specular

    def test_per_material_overrides_global(self):
        """per-material bindings 优先于全局 fallback。"""
        mats = [
            {
                "parameter_bindings": self.CHAR_BINDINGS,
                "textures": [{"texture_property_name": "SubsurfaceColor_Texture"}],
            },
        ]
        # 全局 bindings 没有 SSS，但 per-material 有
        channels = extract_channels_from_materials(mats, self.PROP_BINDINGS)
        assert "Specular" in channels

    def test_fallback_to_global_when_no_per_material(self):
        """无 per-material bindings 时回退到全局。"""
        mats = [
            {
                "textures": [{"texture_property_name": "Height_Texture"}],
            },
        ]
        channels = extract_channels_from_materials(mats, self.PROP_BINDINGS)
        assert "Height" in channels

    def test_mixed_materials(self):
        """混合场景：部分有 per-material，部分无。"""
        mats = [
            {
                "parameter_bindings": self.CHAR_BINDINGS,
                "textures": [{"texture_property_name": "SubsurfaceColor_Texture"}],
            },
            {
                "textures": [{"texture_property_name": "Height_Texture"}],
            },
        ]
        # mat[0] 用 CHAR_BINDINGS (SSS → Specular)
        # mat[1] 无 per-material，用全局 PROP_BINDINGS (H → Height)
        channels = extract_channels_from_materials(mats, self.PROP_BINDINGS)
        assert "Specular" in channels
        assert "Height" in channels


# ---------------------------------------------------------------------------
# 5.3 extract_channels_from_materials — packed channel suffix 展开
# ---------------------------------------------------------------------------
class TestExtractChannelsPackedSuffix:
    """测试 extract_channels_from_materials 的 packed channel suffix 展开。"""

    # ── 新格式：parameter_bindings + texture_definitions ──
    NEW_BINDINGS = {
        "D": "BaseColor_Texture",
        "N": "Normal_Texture",
        "MRO": "Packed_Texture",
        "H": "Height_Texture",
    }
    MRO_TEX_DEFS = [
        {
            "suffix": "MRO",
            "name": "Packed_MRO",
            "channels": {
                "R": {"from": "Metallic", "ch": "R"},
                "G": {"from": "Roughness", "ch": "R"},
                "B": {"from": "AmbientOcclusion", "ch": "R"},
            },
        }
    ]

    # ── 旧格式：.R/.G/.B 后缀 ──
    LEGACY_BINDINGS = {
        "D": "BaseColor_Texture",
        "N": "Normal_Texture",
        "M": "Packed_Texture.R",
        "R": "Packed_Texture.G",
        "AO": "Packed_Texture.B",
        "H": "Height_Texture",
    }

    def test_packed_texture_expands_new_format(self):
        """新格式：Packed Texture 应展开为 Metallic + Roughness + AO。"""
        mats = [{"textures": [
            {"texture_property_name": "Packed_Texture"},
        ], "parameter_bindings": self.NEW_BINDINGS,
           "texture_definitions": self.MRO_TEX_DEFS}]
        channels = extract_channels_from_materials(mats)
        assert "Metallic" in channels
        assert "Roughness" in channels
        assert "AO" in channels

    def test_packed_plus_normal_new_format(self):
        """新格式：Packed + 普通贴图混合。"""
        mats = [{"textures": [
            {"texture_property_name": "BaseColor_Texture"},
            {"texture_property_name": "Normal_Texture"},
            {"texture_property_name": "Packed_Texture"},
            {"texture_property_name": "Height_Texture"},
        ], "parameter_bindings": self.NEW_BINDINGS,
           "texture_definitions": self.MRO_TEX_DEFS}]
        channels = extract_channels_from_materials(mats)
        assert "BaseColor" in channels
        assert "Normal" in channels
        assert "Metallic" in channels
        assert "Roughness" in channels
        assert "AO" in channels
        assert "Height" in channels

    def test_packed_deduplicates_new_format(self):
        """新格式：多材质共用相同 packed 贴图不应产生重复通道。"""
        mat_data = {"textures": [{"texture_property_name": "Packed_Texture"}],
                    "parameter_bindings": self.NEW_BINDINGS,
                    "texture_definitions": self.MRO_TEX_DEFS}
        mats = [mat_data, mat_data]
        channels = extract_channels_from_materials(mats)
        assert channels.count("Metallic") == 1
        assert channels.count("Roughness") == 1
        assert channels.count("AO") == 1

    # ── 旧格式向后兼容 ──
    def test_packed_texture_expands_legacy(self):
        """旧格式 .R/.G/.B 仍能展开。"""
        mats = [{"textures": [
            {"texture_property_name": "Packed_Texture"},
        ], "parameter_bindings": self.LEGACY_BINDINGS}]
        channels = extract_channels_from_materials(mats)
        assert "Metallic" in channels
        assert "Roughness" in channels
        assert "AO" in channels

    def test_packed_plus_normal_legacy(self):
        """旧格式 Packed + 普通贴图混合。"""
        mats = [{"textures": [
            {"texture_property_name": "BaseColor_Texture"},
            {"texture_property_name": "Normal_Texture"},
            {"texture_property_name": "Packed_Texture"},
            {"texture_property_name": "Height_Texture"},
        ], "parameter_bindings": self.LEGACY_BINDINGS}]
        channels = extract_channels_from_materials(mats)
        assert "BaseColor" in channels
        assert "Normal" in channels
        assert "Metallic" in channels
        assert "Roughness" in channels
        assert "AO" in channels
        assert "Height" in channels

    def test_non_packed_bindings_unchanged(self):
        """无后缀的普通 bindings 行为不变。"""
        old_bindings = {
            "D": "BaseColor_Texture",
            "N": "Normal_Texture",
            "MRO": "Packed_Texture",
            "H": "Height_Texture",
        }
        mats = [{"textures": [
            {"texture_property_name": "Packed_Texture"},
        ], "parameter_bindings": old_bindings}]
        channels = extract_channels_from_materials(mats)
        # 无 texture_definitions 时，MRO 走 map_ue_to_sp_with_bindings → Roughness
        assert "Roughness" in channels
