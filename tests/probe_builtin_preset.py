# -*- coding: utf-8 -*-
"""SP 内执行的探测脚本 — dump 内置 "Unreal Engine (Packed)" 预设的完整配置。

使用方法：
  在 SP Python Console 中执行：

    exec(open(r"C:\\Users\\tiany\\Documents\\Adobe\\Adobe Substance 3D Painter\\python\\plugins\\SPsync\\tests\\probe_builtin_preset.py", encoding="utf-8").read())

目的：
  对比 SP 自带的 UE Packed 预设和我们生成的 RoundTrip 配置，
  找出 virtualMap / Normal / AO / Height 配置差异。
"""


def probe():
    import json
    import substance_painter.export as spex
    import substance_painter.project as sppj
    import substance_painter.textureset as spts

    SEP = "=" * 60

    if not sppj.is_open():
        print("[PROBE] 错误：请先打开一个项目再运行此脚本。")
        return

    print(f"\n{SEP}")
    print("[PROBE] Built-in Export Preset Inspector")
    print(SEP)

    # ── Step 1: 列出所有资源导出预设 ──
    presets = spex.list_resource_export_presets()
    print(f"\n[1] 已注册导出预设 ({len(presets)} 个):")
    target_preset = None
    for p in presets:
        name = p.resource_id.name
        is_ue = "unreal" in name.lower()
        marker = " ◄◄◄ TARGET" if is_ue and "packed" in name.lower() else ""
        print(f"    {'★' if is_ue else ' '} {name}{marker}")
        if is_ue and "packed" in name.lower():
            target_preset = p

    # ── Step 2: dump 所有含 "unreal" 的预设配置 ──
    print(f"\n[2] Unreal 相关预设详情:")
    print(SEP)
    for p in presets:
        name = p.resource_id.name
        if "unreal" not in name.lower():
            continue
        print(f"\n--- Preset: {name} ---")
        try:
            output_maps = p.list_output_maps()
            print(f"    maps 数量: {len(output_maps)}")
            for i, m in enumerate(output_maps):
                print(f"\n    map[{i}]: {json.dumps(m, indent=6, ensure_ascii=False)}")
        except Exception as e:
            print(f"    ✗ 获取失败: {e}")

    # ── Step 3: 用内置预设生成完整导出配置并 dump ──
    if target_preset is None:
        # fallback: 找任何 unreal 预设
        for p in presets:
            if "unreal" in p.resource_id.name.lower():
                target_preset = p
                break

    if target_preset is not None:
        print(f"\n\n[3] 使用内置预设 '{target_preset.resource_id.name}' 生成导出配置:")
        print(SEP)

        ts_list = list(spts.all_texture_sets())
        export_list = [{"rootPath": ts.name()} for ts in ts_list]
        if not export_list:
            export_list = [{"rootPath": ""}]

        import tempfile
        test_config = {
            "exportShaderParams": False,
            "exportPath": tempfile.gettempdir().replace('\\', '/') + "/probe_preset",
            "defaultExportPreset": target_preset.resource_id.name,
            "exportPresets": [{
                "name": target_preset.resource_id.name,
                "maps": target_preset.list_output_maps(),
            }],
            "exportList": export_list,
            "exportParameters": [{
                "parameters": {
                    "fileFormat": "tga",
                    "bitDepth": "8",
                    "dithering": True,
                    "paddingAlgorithm": "infinite",
                }
            }],
        }

        print(f"\n  完整导出 config:")
        print(json.dumps(test_config, indent=2, ensure_ascii=False))

        # 验证（不导出，只列出将生成的文件）
        try:
            preview = spex.list_project_textures(test_config)
            print(f"\n  list_project_textures 预览:")
            for k, files in preview.items():
                print(f"    TextureSet: {k}")
                for f in files:
                    print(f"      → {f}")
        except Exception as e:
            print(f"  ✗ list_project_textures 失败: {e}")
    else:
        print(f"\n[3] 未找到任何 Unreal 预设，跳过。")

    # ── Step 4: 如果有 roundtrip metadata，也 dump 生成的配置 ──
    print(f"\n\n[4] SPSync Round-Trip 配置（如有 metadata）:")
    print(SEP)
    try:
        metadata = sppj.Metadata("sp_sync")
        raw = metadata.get("ue_material_defs")
        if raw:
            import sys
            sys.path.insert(0, r"C:\Users\tiany\Documents\Adobe\Adobe Substance 3D Painter\python\plugins\SPsync")
            from sp_channel_map import build_roundtrip_export_config
            ue_defs = json.loads(raw)
            rt_config = build_roundtrip_export_config(ue_defs, "/tmp/roundtrip")
            print(f"\n  Round-Trip 导出 config:")
            print(json.dumps(rt_config, indent=2, ensure_ascii=False))
        else:
            print("  无 sp_sync.ue_material_defs metadata。")
    except Exception as e:
        print(f"  ✗ {e}")

    print(f"\n{SEP}")
    print("[PROBE] 完成")
    print(SEP)


probe()
