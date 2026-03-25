# -*- coding: utf-8 -*-
"""sp_channel_map.py 单元测试。

测试范围（🤖 全自动）：
- 5.1 通道映射字典 + fallback
- 5.2 多材质槽 / UDIM / 边界用例
"""
import pytest

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sp_channel_map import (
    UE_TO_SP_CHANNEL,
    SP_CHANNEL_TO_SUFFIX,
    DEFAULT_CHANNEL,
    map_ue_to_sp,
    map_ue_to_sp_with_bindings,
    get_export_suffix,
    get_all_sp_channels,
    CHANNEL_SUFFIX_WEIGHTS,
    parse_channel_suffix,
    resolve_packed_channels,
)


# ---------------------------------------------------------------------------
# 5.1 通道映射 + fallback
# ---------------------------------------------------------------------------
class TestMapUeToSp:
    @pytest.mark.parametrize("ue_name,expected", [
        ("BaseColor", "BaseColor"),
        ("Normal", "Normal"),
        ("Metallic", "Metallic"),
        ("Roughness", "Roughness"),
        ("AO", "AO"),
        ("Emissive", "Emissive"),
        ("Opacity", "Opacity"),
        ("Height", "Height"),
        ("Specular", "Specular"),
    ])
    def test_exact_match(self, ue_name, expected):
        assert map_ue_to_sp(ue_name) == expected

    def test_ambient_occlusion_alias(self):
        assert map_ue_to_sp("AmbientOcclusion") == "AO"

    def test_emissive_color_alias(self):
        assert map_ue_to_sp("EmissiveColor") == "Emissive"

    @pytest.mark.parametrize("ue_name", [
        "basecolor", "BASECOLOR", "BaseColor", "baseColor",
    ])
    def test_case_insensitive(self, ue_name):
        assert map_ue_to_sp(ue_name) == "BaseColor"

    def test_unknown_fallback_to_default(self):
        assert map_ue_to_sp("UnknownParam") == DEFAULT_CHANNEL
        assert map_ue_to_sp("CustomFoo") == DEFAULT_CHANNEL

    def test_empty_string_fallback(self):
        assert map_ue_to_sp("") == DEFAULT_CHANNEL

    # --- _Texture 后缀变体 ---
    @pytest.mark.parametrize("ue_name,expected", [
        ("BaseColor_Texture", "BaseColor"),
        ("Normal_Texture", "Normal"),
        ("Metallic_Texture", "Metallic"),
        ("Roughness_Texture", "Roughness"),
        ("AO_Texture", "AO"),
        ("Emissive_Texture", "Emissive"),
        ("Opacity_Texture", "Opacity"),
        ("Height_Texture", "Height"),
        ("Specular_Texture", "Specular"),
    ])
    def test_texture_suffix_direct(self, ue_name, expected):
        assert map_ue_to_sp(ue_name) == expected

    def test_texture_suffix_strip_fallback(self):
        """未直接注册但去掉 _Texture 后能匹配的参数名。"""
        assert map_ue_to_sp("Metallic_texture") == "Metallic"

    # --- 打包纹理 ---
    @pytest.mark.parametrize("ue_name", [
        "Packed_Texture", "Packed", "ORM", "MRO",
        "OcclusionRoughnessMetallic",
    ])
    def test_packed_texture(self, ue_name):
        assert map_ue_to_sp(ue_name) == "Roughness"


class TestGetExportSuffix:
    @pytest.mark.parametrize("channel,expected", [
        ("BaseColor", "BCO"),
        ("Normal", "N"),
        ("Metallic", "M"),
        ("Roughness", "R"),
        ("AO", "AO"),
        ("Emissive", "E"),
        ("Opacity", "O"),
        ("Height", "H"),
        ("Specular", "S"),
    ])
    def test_known_channels(self, channel, expected):
        assert get_export_suffix(channel) == expected

    def test_unknown_channel_fallback(self):
        assert get_export_suffix("Unknown") == "BCO"


class TestGetAllSpChannels:
    def test_returns_all_channels(self):
        channels = get_all_sp_channels()
        assert "BaseColor" in channels
        assert "Normal" in channels
        assert len(channels) == len(SP_CHANNEL_TO_SUFFIX)

    def test_no_duplicates(self):
        channels = get_all_sp_channels()
        assert len(channels) == len(set(channels))


# ---------------------------------------------------------------------------
# 5.2 映射表完整性
# ---------------------------------------------------------------------------
class TestMappingConsistency:
    def test_all_sp_channels_have_suffix(self):
        """所有 UE→SP 映射的 SP 通道都有对应的导出后缀。"""
        for sp_channel in UE_TO_SP_CHANNEL.values():
            assert sp_channel in SP_CHANNEL_TO_SUFFIX, f"SP channel {sp_channel} 缺少导出后缀"

    def test_default_channel_exists(self):
        assert DEFAULT_CHANNEL in SP_CHANNEL_TO_SUFFIX


# ---------------------------------------------------------------------------
# 5.3 配置驱动映射 map_ue_to_sp_with_bindings
# ---------------------------------------------------------------------------
class TestMapUeToSpWithBindings:
    """测试 parameter_bindings 驱动的动态通道映射。"""

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

    @pytest.mark.parametrize("param,expected", [
        ("BaseColor_Texture", "BaseColor"),
        ("Normal_Texture", "Normal"),
        ("Packed_Texture", "Roughness"),
        ("Height_Texture", "Height"),
    ])
    def test_prop_bindings(self, param, expected):
        assert map_ue_to_sp_with_bindings(param, self.PROP_BINDINGS) == expected

    @pytest.mark.parametrize("param,expected", [
        ("BaseColor_Texture", "BaseColor"),
        ("Normal_Texture", "Normal"),
        ("Packed_Texture", "Roughness"),
        ("SubsurfaceColor_Texture", "Specular"),
    ])
    def test_char_bindings(self, param, expected):
        assert map_ue_to_sp_with_bindings(param, self.CHAR_BINDINGS) == expected

    def test_empty_bindings_fallback(self):
        """空 bindings 应 fallback 到硬编码映射。"""
        assert map_ue_to_sp_with_bindings("BaseColor_Texture", {}) == "BaseColor"
        assert map_ue_to_sp_with_bindings("Normal", {}) == "Normal"

    def test_unknown_param_fallback(self):
        """bindings 中无匹配时 fallback 到硬编码映射。"""
        assert map_ue_to_sp_with_bindings("Emissive_Texture", self.PROP_BINDINGS) == "Emissive"

    def test_completely_unknown_param(self):
        """完全未知的参数名 fallback 到 DEFAULT_CHANNEL。"""
        assert map_ue_to_sp_with_bindings("FooBar", self.PROP_BINDINGS) == DEFAULT_CHANNEL

    def test_case_insensitive_match(self):
        """bindings 匹配应支持大小写不敏感。"""
        assert map_ue_to_sp_with_bindings("basecolor_texture", self.PROP_BINDINGS) == "BaseColor"


# ---------------------------------------------------------------------------
# 5.4 parse_channel_suffix（通道后缀解析）
# ---------------------------------------------------------------------------
class TestParseChannelSuffix:
    """测试 parse_channel_suffix 通道后缀解析。"""

    @pytest.mark.parametrize("value,expected_tex,expected_channel", [
        ("Packed_Texture.R", "Packed_Texture", "R"),
        ("Packed_Texture.G", "Packed_Texture", "G"),
        ("Packed_Texture.B", "Packed_Texture", "B"),
        ("Packed_Texture.A", "Packed_Texture", "A"),
    ])
    def test_valid_suffixes(self, value, expected_tex, expected_channel):
        tex, weights = parse_channel_suffix(value)
        assert tex == expected_tex
        assert weights is not None
        assert weights == CHANNEL_SUFFIX_WEIGHTS[expected_channel]

    def test_lowercase_suffix(self):
        """小写后缀 .r/.g/.b/.a 也应识别。"""
        tex, weights = parse_channel_suffix("MRO_Texture.r")
        assert tex == "MRO_Texture"
        assert weights == CHANNEL_SUFFIX_WEIGHTS["R"]

    def test_no_suffix(self):
        """无后缀返回 (原值, None)。"""
        tex, weights = parse_channel_suffix("BaseColor_Texture")
        assert tex == "BaseColor_Texture"
        assert weights is None

    def test_empty_string(self):
        tex, weights = parse_channel_suffix("")
        assert tex == ""
        assert weights is None

    def test_single_char(self):
        """单字符不应匹配。"""
        tex, weights = parse_channel_suffix("R")
        assert tex == "R"
        assert weights is None

    def test_dot_only(self):
        """只有 . 不应匹配。"""
        tex, weights = parse_channel_suffix(".R")
        assert tex == ".R"
        assert weights is None

    def test_invalid_channel_letter(self):
        """无效通道字母（如 .X）不应匹配。"""
        tex, weights = parse_channel_suffix("Packed.X")
        assert tex == "Packed.X"
        assert weights is None

    def test_dot_in_middle(self):
        """中间有 . 但结尾也有 .R 应只取结尾。"""
        tex, weights = parse_channel_suffix("My.Texture.R")
        assert tex == "My.Texture"
        assert weights == CHANNEL_SUFFIX_WEIGHTS["R"]

    def test_weights_are_copies(self):
        """返回的权重字典应是独立副本。"""
        _, w1 = parse_channel_suffix("A.R")
        _, w2 = parse_channel_suffix("B.R")
        assert w1 is not w2
        w1["Red"] = 999
        assert CHANNEL_SUFFIX_WEIGHTS["R"]["Red"] == 1.0


# ---------------------------------------------------------------------------
# 5.5 resolve_packed_channels（Packed Texture 通道拆分解析）
# ---------------------------------------------------------------------------
class TestResolvePackedChannels:
    """测试 resolve_packed_channels。"""

    # ── 新格式测试数据 ──
    MRO_BINDINGS = {
        "D": "BaseColor_Texture",
        "N": "Normal_Texture",
        "MRO": "Packed_Texture",
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

    # ── 旧格式测试数据（向后兼容）──
    LEGACY_BINDINGS = {
        "D": "BaseColor_Texture",
        "N": "Normal_Texture",
        "M": "Packed_Texture.R",
        "R": "Packed_Texture.G",
        "AO": "Packed_Texture.B",
    }

    # ── 新格式测试 ──
    def test_mro_packed_texture(self):
        """MRO Packed Texture 应解析出 3 个通道（新格式 texture_definitions）。"""
        result = resolve_packed_channels("Packed_Texture", self.MRO_BINDINGS, self.MRO_TEX_DEFS)
        assert len(result) == 3
        sp_channels = {ch for ch, _ in result}
        assert sp_channels == {"Metallic", "Roughness", "AO"}

    def test_mro_weights(self):
        """验证每个通道的权重正确（新格式）。"""
        result = resolve_packed_channels("Packed_Texture", self.MRO_BINDINGS, self.MRO_TEX_DEFS)
        result_dict = {ch: w for ch, w in result}
        assert result_dict["Metallic"]["Red"] == 1.0
        assert result_dict["Metallic"]["Green"] == 0.0
        assert result_dict["Roughness"]["Green"] == 1.0
        assert result_dict["Roughness"]["Red"] == 0.0
        assert result_dict["AO"]["Blue"] == 1.0
        assert result_dict["AO"]["Red"] == 0.0

    def test_non_packed_texture(self):
        """无通道后缀的贴图应返回空列表。"""
        result = resolve_packed_channels("BaseColor_Texture", self.MRO_BINDINGS, self.MRO_TEX_DEFS)
        assert result == []

    def test_empty_bindings(self):
        result = resolve_packed_channels("Packed_Texture", {})
        assert result == []

    def test_no_matching_texture(self):
        result = resolve_packed_channels("OtherTexture", self.MRO_BINDINGS, self.MRO_TEX_DEFS)
        assert result == []

    # ── 旧格式向后兼容测试 ──
    def test_legacy_mro_packed(self):
        """旧格式 .R/.G/.B 应仍然能解析（无 texture_definitions）。"""
        result = resolve_packed_channels("Packed_Texture", self.LEGACY_BINDINGS)
        assert len(result) == 3
        sp_channels = {ch for ch, _ in result}
        assert sp_channels == {"Metallic", "Roughness", "AO"}

    def test_legacy_weights(self):
        """旧格式权重验证。"""
        result = resolve_packed_channels("Packed_Texture", self.LEGACY_BINDINGS)
        result_dict = {ch: w for ch, w in result}
        assert result_dict["Metallic"]["Red"] == 1.0
        assert result_dict["Roughness"]["Green"] == 1.0
        assert result_dict["AO"]["Blue"] == 1.0

    def test_alpha_channel(self):
        """测试 .A 通道提取（旧格式）。"""
        bindings = {"O": "Packed_Texture.A"}
        result = resolve_packed_channels("Packed_Texture", bindings)
        assert len(result) == 1
        assert result[0][0] == "Opacity"
        assert result[0][1]["Alpha"] == 1.0

    def test_single_channel_extraction(self):
        """单通道提取（旧格式）。"""
        bindings = {"M": "MRO_Texture.R"}
        result = resolve_packed_channels("MRO_Texture", bindings)
        assert len(result) == 1
        assert result[0][0] == "Metallic"

    def test_no_tex_defs_new_format_returns_empty(self):
        """新格式 bindings 但无 texture_definitions 时返回空列表。"""
        result = resolve_packed_channels("Packed_Texture", self.MRO_BINDINGS)
        assert result == []
