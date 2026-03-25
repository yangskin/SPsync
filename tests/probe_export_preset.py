# -*- coding: utf-8 -*-
"""SP 内执行的探测脚本 — 将 SPSYNCDefault.spexp 预设转换为 JSON 并打印。

使用方法：
  在 SP 中打开一个项目（任意项目即可），然后在 SP 的
  Python 控制台（Window → Python Console）中执行：

    exec(open(r"C:\\Users\\tiany\\Documents\\Adobe\\Adobe Substance 3D Painter\\python\\plugins\\SPsync\\tests\\probe_export_preset.py", encoding="utf-8").read())

探测项：
  1. 导入 SPSYNCDefault.spexp 为会话资源
  2. 列出所有可用导出预设
  3. 找到 SPSYNCDefault 预设
  4. 调用 list_output_maps() 获取 maps 结构
  5. 用 list_project_textures() 预览导出配置（如有项目打开）
  6. 打印完整 JSON 格式供参考
"""


def probe():
    import json
    import os
    import traceback

    import substance_painter.export as spex
    import substance_painter.project as sppj
    import substance_painter.resource as spres
    import substance_painter.textureset as spts

    SEP = "=" * 60

    # ── 前置检查 ──
    if not sppj.is_open():
        print("[PROBE] 错误：请先打开一个项目再运行此脚本。")
        return

    print(f"\n{SEP}")
    print("[PROBE] Export Preset Inspector")
    print(SEP)

    # ── Step 1: 导入预设 ──
    # exec() 环境下无 __file__，使用已知绝对路径
    plugin_root = r"C:\Users\tiany\Documents\Adobe\Adobe Substance 3D Painter\python\plugins\SPsync"
    preset_path = os.path.join(plugin_root, "assets", "export-presets", "SPSYNCDefault.spexp")
    print(f"\n[1] 预设文件: {preset_path}")
    print(f"    存在: {os.path.isfile(preset_path)}")

    try:
        spres.import_session_resource(preset_path, spres.Usage.EXPORT)
        print("    导入成功")
    except Exception as e:
        print(f"    导入失败: {e}")
        # 可能已经导入过，继续

    # ── Step 2: 列出所有预设 ──
    presets = spex.list_resource_export_presets()
    print(f"\n[2] 可用导出预设 ({len(presets)} 个):")
    for i, p in enumerate(presets):
        print(f"    [{i}] {p.resource_id.name}  (context={p.resource_id.context})")

    # ── Step 3: 找到 SPSYNCDefault ──
    target = None
    for p in presets:
        if p.resource_id.name == "SPSYNCDefault":
            target = p
            break

    if target is None:
        print("\n[PROBE] 未找到 SPSYNCDefault 预设！")
        # 尝试打印第一个预设作为参考
        if presets:
            target = presets[0]
            print(f"    使用第一个预设作为参考: {target.resource_id.name}")
        else:
            return

    # ── Step 4: list_output_maps() ──
    print(f"\n[3] 预设 '{target.resource_id.name}' 的 maps 结构:")
    print(SEP)
    try:
        maps = target.list_output_maps()
        print(json.dumps(maps, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"    list_output_maps() 失败: {e}")
        traceback.print_exc()
        maps = []

    # ── Step 5: 也打印其他几个常用预设的 maps 做对比 ──
    compare_names = ["PBR Metallic Roughness", "Unreal Engine 4 (Packed)"]
    for name in compare_names:
        for p in presets:
            if p.resource_id.name == name:
                print(f"\n[对比] 预设 '{name}' 的 maps 结构:")
                print(SEP)
                try:
                    ref_maps = p.list_output_maps()
                    print(json.dumps(ref_maps, indent=2, ensure_ascii=False))
                except Exception as e:
                    print(f"    失败: {e}")
                break

    # ── Step 6: 用 list_project_textures 预览 ──
    if maps:
        print(f"\n[4] list_project_textures() 预览:")
        print(SEP)
        # 获取第一个 TextureSet 名
        ts_list = [ts.name() for ts in spts.all_texture_sets()]
        if ts_list:
            config = {
                "exportShaderParams": False,
                "exportPath": os.path.join(os.environ.get("TEMP", "/tmp"), "probe_export"),
                "defaultExportPreset": target.resource_id.name,
                "exportPresets": [{
                    "name": target.resource_id.name,
                    "maps": maps,
                }],
                "exportList": [{"rootPath": ts_list[0]}],
                "exportParameters": [{
                    "parameters": {
                        "fileFormat": "tga",
                        "bitDepth": "8",
                    }
                }],
            }
            print(f"    TextureSet: {ts_list[0]}")
            print(f"    导出配置:")
            print(json.dumps(config, indent=2, ensure_ascii=False))
            try:
                preview = spex.list_project_textures(config)
                print(f"\n    预览结果:")
                for k, v in preview.items():
                    print(f"    Stack {k}:")
                    for f in v:
                        print(f"      {f}")
            except Exception as e:
                print(f"    预览失败: {e}")
                traceback.print_exc()

    # ── Step 7: 尝试用 inline 预设格式也做一次，确认格式差异 ──
    print(f"\n[5] 对比: 用 inline 手写预设 (basecolor R/G/B) 预览:")
    print(SEP)
    ts_list = [ts.name() for ts in spts.all_texture_sets()]
    if ts_list:
        inline_config = {
            "exportShaderParams": False,
            "exportPath": os.path.join(os.environ.get("TEMP", "/tmp"), "probe_export"),
            "defaultExportPreset": "InlineTest",
            "exportPresets": [{
                "name": "InlineTest",
                "maps": [{
                    "fileName": "T_test_$textureSet_D",
                    "channels": [
                        {"destChannel": "R", "srcChannel": "R",
                         "srcMapType": "documentMap", "srcMapName": "basecolor"},
                        {"destChannel": "G", "srcChannel": "G",
                         "srcMapType": "documentMap", "srcMapName": "basecolor"},
                        {"destChannel": "B", "srcChannel": "B",
                         "srcMapType": "documentMap", "srcMapName": "basecolor"},
                    ],
                }],
            }],
            "exportList": [{"rootPath": ts_list[0]}],
            "exportParameters": [{
                "parameters": {"fileFormat": "tga", "bitDepth": "8"}
            }],
        }
        try:
            preview2 = spex.list_project_textures(inline_config)
            print(f"    ✓ inline R/G/B 格式有效")
            for k, v in preview2.items():
                print(f"    Stack {k}:")
                for f in v:
                    print(f"      {f}")
        except ValueError as e:
            print(f"    ✗ inline R/G/B 格式无效: {e}")

    print(f"\n{SEP}")
    print("[PROBE] 完成")
    print(SEP)


probe()
