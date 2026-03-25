# -*- coding: utf-8 -*-
"""SP 内执行的探测脚本 — 验证 Grayscale Conversion 滤镜 API 可行性。

使用方法：
  在 SP 中打开一个项目（任意项目即可），然后在 SP 的
  Python 控制台（Window → Python Console）中执行：

    exec(open(r"<此文件路径>").read())

  或直接粘贴全部内容执行。

探测项：
  1. resource.search — 尝试多种查询语法找到 Grayscale Conversion
  2. insert_filter_effect — 在当前 TextureSet 的第一个 stack 中插入
  3. FilterEffectNode.set_source — 绑定滤镜并获取 SourceSubstance
  4. SourceSubstance.get_parameters / get_properties — 打印参数名和值
  5. set_parameters — 验证参数可写性
  6. 清理 — 删除测试节点（可选）
"""
def probe():
    import traceback
    SEP = "=" * 60
    import substance_painter.resource as resource
    import substance_painter.layerstack as layerstack
    import substance_painter.textureset as textureset
    import substance_painter.project as project

    # ── 前置检查 ──
    if not project.is_open():
        print("[PROBE] 错误：请先打开一个项目再运行此脚本。")
        return

    print(SEP)
    print("[PROBE] Grayscale Conversion Filter API 探测开始")
    print(SEP)

    # ══════════════════════════════════════════════════════════
    # 1. resource.search — 尝试多种查询语法
    # ══════════════════════════════════════════════════════════
    print("\n[PROBE] === 1. resource.search 查询 Grayscale Conversion ===")

    queries = [
        'u:filter n:"Grayscale Conversion"',
        'u:filter n:Grayscale Conversion',
        'u:filter Grayscale',
        'u:filter grayscale',
        's:starter_assets u:filter',
        'u:filter',
    ]

    filter_res = None
    for q in queries:
        try:
            results = resource.search(q)
            names = [r.identifier().name for r in results]
            print(f"  查询: '{q}'")
            print(f"    结果数: {len(results)}")
            if results:
                for r in results[:10]:  # 最多显示10个
                    rid = r.identifier()
                    print(f"    - name={rid.name}  context={rid.context}  url={rid.url()}")
                # 找 Grayscale Conversion
                for r in results:
                    if "grayscale" in r.identifier().name.lower():
                        filter_res = r
                        print(f"    >>> 找到目标: {r.identifier().name}")
        except Exception as e:
            print(f"  查询: '{q}' → 异常: {e}")

    if filter_res is None:
        print("\n[PROBE] 未找到 Grayscale Conversion 滤镜！尝试列出所有 filter 类型资源...")
        try:
            all_filters = resource.search("u:filter")
            print(f"  所有 filter 资源数: {len(all_filters)}")
            for r in all_filters[:30]:
                rid = r.identifier()
                print(f"    - name={rid.name}  context={rid.context}")
        except Exception as e:
            print(f"  列出 filter 失败: {e}")
        print("[PROBE] 探测中止：无法找到滤镜资源。")
        return

    filter_id = filter_res.identifier()
    print(f"\n[PROBE] 使用滤镜: name={filter_id.name}  url={filter_id.url()}")

    # ══════════════════════════════════════════════════════════
    # 2. 获取当前 TextureSet 和 Stack
    # ══════════════════════════════════════════════════════════
    print("\n[PROBE] === 2. 获取 TextureSet / Stack ===")
    texture_sets = textureset.all_texture_sets()
    if not texture_sets:
        print("[PROBE] 错误：当前项目无 TextureSet。")
        return

    ts = texture_sets[0]
    stack = ts.get_stack()
    print(f"  TextureSet: {ts.name()}")
    print(f"  Stack: {stack}")

    # ══════════════════════════════════════════════════════════
    # 3. 创建 Fill Layer（作为滤镜的宿主）
    # ══════════════════════════════════════════════════════════
    print("\n[PROBE] === 3. 创建测试 Fill Layer ===")
    try:
        position = layerstack.InsertPosition.from_textureset_stack(stack)
        fill_layer = layerstack.insert_fill(position)
        fill_layer.set_name("__PROBE_TEST_FILL__")
        print(f"  Fill Layer 创建成功: uid={fill_layer.uid()}, name={fill_layer.get_name()}")
        print(f"  Fill Layer type: {fill_layer.get_type()}")
    except Exception as e:
        print(f"  Fill Layer 创建失败: {e}")
        traceback.print_exc()
        return

    # ══════════════════════════════════════════════════════════
    # 4. 在 Fill Layer 内部插入 Filter Effect
    # ══════════════════════════════════════════════════════════
    print("\n[PROBE] === 4. 插入 Filter Effect ===")
    filter_node = None
    try:
        # Filter Effect 必须插入到 Layer 的 Content 内部
        effect_position = layerstack.InsertPosition.inside_node(
            fill_layer, layerstack.NodeStack.Content
        )
        filter_node = layerstack.insert_filter_effect(effect_position, filter_id)
        print(f"  Filter Effect 插入成功!")
        print(f"    type: {type(filter_node).__name__}")
        print(f"    uid: {filter_node.uid()}")
        print(f"    node_type: {filter_node.get_type()}")
    except Exception as e:
        print(f"  Filter Effect 插入失败: {e}")
        traceback.print_exc()

        # 备用：尝试在 stack 顶层插入
        print("  尝试备用位置（stack 顶层）...")
        try:
            effect_position = layerstack.InsertPosition.from_textureset_stack(stack)
            filter_node = layerstack.insert_filter_effect(effect_position, filter_id)
            print(f"  备用位置插入成功! type={type(filter_node).__name__}")
        except Exception as e2:
            print(f"  备用位置也失败: {e2}")
            traceback.print_exc()

        # 再备用：空 filter 后 set_source
        if filter_node is None:
            print("  尝试插入空 filter 后 set_source...")
            try:
                effect_position = layerstack.InsertPosition.inside_node(
                    fill_layer, layerstack.NodeStack.Content
                )
                filter_node = layerstack.insert_filter_effect(effect_position)
                filter_node.set_source(filter_id)
                print(f"  空 filter + set_source 成功!")
            except Exception as e3:
                print(f"  空 filter + set_source 失败: {e3}")
                traceback.print_exc()
                return

    # ══════════════════════════════════════════════════════════
    # 5. 获取 SourceSubstance 并读取参数
    # ══════════════════════════════════════════════════════════
    print("\n[PROBE] === 5. 读取 SourceSubstance 参数 ===")
    try:
        source = filter_node.get_source()
        print(f"  get_source() 返回: {type(source).__name__}")
        print(f"  resource_id: {source.resource_id}")
    except Exception as e:
        print(f"  get_source() 失败: {e}")
        traceback.print_exc()
        source = None

    if source is not None:
        # get_parameters
        print("\n  --- get_parameters() ---")
        try:
            params = source.get_parameters()
            print(f"  参数数量: {len(params)}")
            for k, v in params.items():
                print(f"    '{k}' = {v}  (type={type(v).__name__})")
        except Exception as e:
            print(f"  get_parameters() 失败: {e}")
            traceback.print_exc()

        # get_properties（更详细）
        print("\n  --- get_properties() ---")
        try:
            props = source.get_properties()
            print(f"  属性数量: {len(props)}")
            for k, prop in props.items():
                try:
                    val = prop.value()
                    label = prop.label()
                    wtype = prop.widget_type()
                    short = prop.short_name()
                    meta = prop.properties()
                    print(f"    '{k}':")
                    print(f"      label='{label}', short='{short}', widget='{wtype}'")
                    print(f"      value={val} (type={type(val).__name__})")
                    print(f"      meta={meta}")
                except Exception as pe:
                    print(f"    '{k}': 读取失败: {pe}")
        except Exception as e:
            print(f"  get_properties() 失败: {e}")
            traceback.print_exc()

        # image_inputs / image_outputs
        print("\n  --- image_inputs / image_outputs ---")
        try:
            inputs = source.image_inputs
            outputs = source.image_outputs
            print(f"  image_inputs: {inputs}")
            print(f"  image_outputs: {outputs}")
        except Exception as e:
            print(f"  inputs/outputs 失败: {e}")

    # ══════════════════════════════════════════════════════════
    # 6. 尝试 set_parameters
    # ══════════════════════════════════════════════════════════
    print("\n[PROBE] === 6. set_parameters 写入测试 ===")
    if source is not None:
        try:
            params = source.get_parameters()
            param_keys = list(params.keys())
            print(f"  参数 keys: {param_keys}")

            # 只测试 RGBA 四个 float 参数：R=1 提取红通道
            new_vals = {"Red": 1.0, "Green": 0.0, "Blue": 0.0, "Alpha": 0.0}
            if True:
                if new_vals:
                    print(f"  写入: {new_vals}")
                    source.set_parameters(new_vals)

                    # 回读验证
                    after = source.get_parameters()
                    print(f"  回读: {after}")
                    print(f"  写入成功!")
                else:
                    print(f"  无数值型参数可写入")
            else:
                print(f"  参数不足，跳过写入测试")
        except Exception as e:
            print(f"  set_parameters 失败: {e}")
            traceback.print_exc()

    # ══════════════════════════════════════════════════════════
    # 7. 探测 active_channels
    # ══════════════════════════════════════════════════════════
    print("\n[PROBE] === 7. FilterEffectNode active_channels ===")
    try:
        channels = filter_node.active_channels
        print(f"  active_channels: {channels}")
    except Exception as e:
        print(f"  active_channels 失败: {e}")

    # ══════════════════════════════════════════════════════════
    # 8. 清理（可选 — 注释掉则保留测试节点供目视检查）
    # ══════════════════════════════════════════════════════════
    print("\n[PROBE] === 8. 清理 ===")
    # 取消注释以下行可删除测试节点：
    # try:
    #     fill_layer.delete()
    #     print("  测试节点已删除")
    # except Exception as e:
    #     print(f"  删除失败: {e}")
    print("  保留测试节点供目视检查（手动删除 __PROBE_TEST_FILL__ 层即可）")

    print(f"\n{SEP}")
    print("[PROBE] 探测完成！请将以上输出反馈。")
    print(SEP)


# 执行
try:
    probe()
except Exception as ex:
    import traceback as _tb
    print(f"[PROBE] 顶层异常: {ex}")
    _tb.print_exc()
