# -*- coding: utf-8 -*-
"""SP 内执行的探测脚本 — 探测所有可用的 virtualMap / meshMap / documentMap 名称。

使用方法：
  在 SP 中打开一个**已烘焙 mesh maps 的项目**，然后在 SP 的
  Python 控制台（Window → Python Console）中执行：

    exec(open(r"C:\\Users\\tiany\\Documents\\Adobe\\Adobe Substance 3D Painter\\python\\plugins\\SPsync\\tests\\probe_virtual_maps.py", encoding="utf-8").read())

探测项：
  1. 列出所有 TextureSet 的 document channels
  2. 尝试用不同 virtualMap 名导出预览，验证哪些名称可用
  3. 尝试用 meshMap 名导出预览，验证烘焙贴图可用性
"""


def probe():
    import json
    import os
    import traceback

    import substance_painter.export as spex
    import substance_painter.project as sppj
    import substance_painter.textureset as spts

    SEP = "=" * 60

    if not sppj.is_open():
        print("[PROBE] 错误：请先打开一个项目再运行此脚本。")
        return

    print(f"\n{SEP}")
    print("[PROBE] Virtual / Mesh / Document Map Inspector")
    print(SEP)

    # ── Step 1: 列出所有 TextureSet 和 channels ──
    ts_list = list(spts.all_texture_sets())
    print(f"\n[1] TextureSets ({len(ts_list)} 个):")
    first_ts_name = None
    for ts in ts_list:
        name = ts.name()
        if first_ts_name is None:
            first_ts_name = name
        print(f"    {name}")
        for stack in ts.all_stacks():
            channels = stack.all_channels()
            try:
                stack_label = stack.name() if callable(getattr(stack, 'name', None)) else str(stack)
            except Exception:
                stack_label = str(stack)
            print(f"      Stack: {stack_label}")
            for ch_type, ch_info in channels.items():
                ch_name = ch_type.name if hasattr(ch_type, 'name') else str(ch_type)
                print(f"        Channel: {ch_name}")

    if first_ts_name is None:
        print("[PROBE] 无 TextureSet，退出。")
        return

    export_path = os.path.join(os.environ.get("TEMP", "/tmp"), "probe_vmap")

    # ── Step 2: 测试 virtualMap 名称 ──
    virtual_map_candidates = [
        "Normal_DirectX",
        "Normal_OpenGL",
        "Mixed_AO",
        "World_Space_Normal",
        "Curvature",
        "Height",           # 测试是否存在 virtualMap Height
        "Mixed_Height",     # 测试是否存在 Mixed_Height
        "Thickness",
        "Position",
    ]

    print(f"\n[2] virtualMap 可用性测试 (TextureSet: {first_ts_name}):")
    print(SEP)
    for vm_name in virtual_map_candidates:
        config = {
            "exportShaderParams": False,
            "exportPath": export_path,
            "defaultExportPreset": "ProbeVM",
            "exportPresets": [{
                "name": "ProbeVM",
                "maps": [{
                    "fileName": f"probe_{vm_name}",
                    "channels": [
                        {"destChannel": "R", "srcChannel": "R",
                         "srcMapType": "virtualMap", "srcMapName": vm_name},
                    ],
                }],
            }],
            "exportList": [{"rootPath": first_ts_name}],
            "exportParameters": [{"parameters": {"fileFormat": "tga", "bitDepth": "8", "dithering": True, "paddingAlgorithm": "infinite"}}],
        }
        try:
            preview = spex.list_project_textures(config)
            files = []
            for k, v in preview.items():
                files.extend(v)
            print(f"    ✓ virtualMap '{vm_name}' — 可用 ({len(files)} 文件)")
        except Exception as e:
            print(f"    ✗ virtualMap '{vm_name}' — 不可用: {e}")

    # ── Step 3: 测试 meshMap 名称 ──
    mesh_map_candidates = [
        "Normal",
        "WorldSpaceNormal",
        "ID",
        "AO",
        "AmbientOcclusion",
        "Curvature",
        "Position",
        "Thickness",
        "Height",
    ]

    print(f"\n[3] meshMap 可用性测试 (TextureSet: {first_ts_name}):")
    print(SEP)
    for mm_name in mesh_map_candidates:
        config = {
            "exportShaderParams": False,
            "exportPath": export_path,
            "defaultExportPreset": "ProbeMM",
            "exportPresets": [{
                "name": "ProbeMM",
                "maps": [{
                    "fileName": f"probe_{mm_name}",
                    "channels": [
                        {"destChannel": "R", "srcChannel": "R",
                         "srcMapType": "meshMap", "srcMapName": mm_name},
                    ],
                }],
            }],
            "exportList": [{"rootPath": first_ts_name}],
            "exportParameters": [{"parameters": {"fileFormat": "tga", "bitDepth": "8", "dithering": True, "paddingAlgorithm": "infinite"}}],
        }
        try:
            preview = spex.list_project_textures(config)
            files = []
            for k, v in preview.items():
                files.extend(v)
            print(f"    ✓ meshMap '{mm_name}' — 可用 ({len(files)} 文件)")
        except Exception as e:
            print(f"    ✗ meshMap '{mm_name}' — 不可用: {e}")

    # ── Step 4: 测试 documentMap 名称 ──
    doc_map_candidates = [
        "basecolor",
        "height",
        "metallic",
        "roughness",
        "ambientOcclusion",
        "normal",
        "emissive",
        "opacity",
        "specular",
    ]

    print(f"\n[4] documentMap 可用性测试 (TextureSet: {first_ts_name}):")
    print(SEP)
    for dm_name in doc_map_candidates:
        config = {
            "exportShaderParams": False,
            "exportPath": export_path,
            "defaultExportPreset": "ProbeDM",
            "exportPresets": [{
                "name": "ProbeDM",
                "maps": [{
                    "fileName": f"probe_{dm_name}",
                    "channels": [
                        {"destChannel": "R", "srcChannel": "R",
                         "srcMapType": "documentMap", "srcMapName": dm_name},
                    ],
                }],
            }],
            "exportList": [{"rootPath": first_ts_name}],
            "exportParameters": [{"parameters": {"fileFormat": "tga", "bitDepth": "8", "dithering": True, "paddingAlgorithm": "infinite"}}],
        }
        try:
            preview = spex.list_project_textures(config)
            files = []
            for k, v in preview.items():
                files.extend(v)
            print(f"    ✓ documentMap '{dm_name}' — 可用 ({len(files)} 文件)")
        except Exception as e:
            print(f"    ✗ documentMap '{dm_name}' — 不可用: {e}")

    print(f"\n{SEP}")
    print("[PROBE] 完成")
    print(f"[PROBE] 建议: 若 virtualMap 'Mixed_AO' 可用，AO 通道可改用它来自动合并烘焙AO")
    print(f"[PROBE] 建议: 若 Height 无 virtualMap，需在图层中手动引用烘焙 Height")
    print(SEP)


probe()
