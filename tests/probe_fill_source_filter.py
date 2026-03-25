# -*- coding: utf-8 -*-
"""SP 探测脚本 — 验证 Fill Layer 通道源使用 Grayscale Conversion + add_channel(AO)。

使用方法：
  1. 在 SP 中打开一个含贴图的项目（如上次测试的 T_tripo_conver 项目）
  2. 在 SP 的 Python Console（Window → Python Console）中执行：

    exec(open(r"C:\\Users\\tiany\\Documents\\Adobe\\Adobe Substance 3D Painter\\python\\plugins\\SPsync\\tests\\probe_fill_source_filter.py").read())

探测目标：
  A. fill_layer.set_source(ChannelType, filter_resource_id) — 滤镜作通道材质源
  B. SourceSubstance 图像输入连接贴图
  C. ChannelFormat 枚举发现 + add_channel(AO)
  D. 获取 Fill Layer 通道源 get_source() 的用法
"""


def probe():
    import traceback
    SEP = "=" * 60

    import substance_painter.resource as resource
    import substance_painter.layerstack as layerstack
    import substance_painter.textureset as textureset
    import substance_painter.project as project

    if not project.is_open():
        print("[PROBE] 错误：请先打开一个项目再运行此脚本。")
        return

    print(SEP)
    print("[PROBE] Fill Source + Filter + add_channel 探测开始")
    print(SEP)

    # ══════════════════════════════════════════════════════════
    # 0. 基础信息：TextureSet / Stack / 活跃通道 / 滤镜定位
    # ══════════════════════════════════════════════════════════
    print("\n[PROBE] === 0. 基础信息 ===")

    all_ts = textureset.all_texture_sets()
    if not all_ts:
        print("[PROBE] 错误：无 TextureSet。")
        return
    ts = all_ts[0]
    stack = ts.get_stack()
    print(f"  TextureSet: {ts.name()}")

    # 当前活跃通道
    try:
        # 尝试获取通道列表
        print(f"\n  --- 活跃通道 ---")
        for attr_name in dir(textureset.ChannelType):
            if attr_name.startswith("_"):
                continue
            ct = getattr(textureset.ChannelType, attr_name)
            try:
                fmt = stack.get_channel_format(ct)
                print(f"    ✅ {attr_name}: format={fmt}")
            except Exception:
                print(f"    ❌ {attr_name}: 不存在")
    except Exception as e:
        print(f"  活跃通道探测失败: {e}")

    # 查找 Grayscale Conversion Filter
    print(f"\n  --- Grayscale Conversion Filter ---")
    filter_results = resource.search('u:filter n:"Grayscale Conversion"')
    if not filter_results:
        print("  未找到 Grayscale Conversion Filter！探测中止。")
        return
    filter_res = filter_results[0]
    filter_id = filter_res.identifier()
    print(f"  滤镜: name={filter_id.name}  url={filter_id.url()}")

    # 查找项目中已有的贴图资源（用于 image input 测试）
    print(f"\n  --- 项目贴图资源 ---")
    tex_results = resource.search("u:texture")
    tex_id = None
    for r in tex_results[:10]:
        rid = r.identifier()
        print(f"    - {rid.name}  context={rid.context}")
        if tex_id is None:
            tex_id = rid  # 取第一个可用贴图
    if tex_id:
        print(f"  将使用贴图: {tex_id.name}")
    else:
        print("  ⚠ 无可用贴图资源")

    # ══════════════════════════════════════════════════════════
    # A. 测试: fill_layer.set_source(ChannelType, filter_resource_id)
    # ══════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print("[PROBE] === A. Fill Layer 通道源设为 Grayscale Filter ===")
    print("=" * 60)

    fill_a = None
    try:
        position = layerstack.InsertPosition.from_textureset_stack(stack)
        fill_a = layerstack.insert_fill(position)
        fill_a.set_name("__PROBE_A_FILTER_SOURCE__")
        print(f"  Fill Layer 创建: {fill_a.get_name()}")
    except Exception as e:
        print(f"  Fill Layer 创建失败: {e}")
        return

    # A1: 尝试 set_source(Roughness, filter_id)
    print(f"\n  --- A1: set_source(Roughness, filter_id) ---")
    try:
        ct_rough = textureset.ChannelType.Roughness
        fill_a.set_source(ct_rough, filter_id)
        print(f"  ✅ set_source 成功！(filter 作为通道源)")
    except Exception as e:
        print(f"  ❌ set_source 失败: {e}")
        traceback.print_exc()

    # A2: 尝试 get_source(ChannelType) — Fill Layer 可能有 per-channel source
    print(f"\n  --- A2: fill_layer.get_source() 探测 ---")
    try:
        source = fill_a.get_source()
        print(f"  get_source(): {type(source).__name__}")
        print(f"  source 详情: {source}")
    except Exception:
        pass
    try:
        source_ch = fill_a.get_source(textureset.ChannelType.Roughness)
        print(f"  get_source(Roughness): {type(source_ch).__name__}")
        print(f"  source 详情: {source_ch}")
    except Exception:
        pass

    # A3: 列出 fill_layer 的所有公开方法/属性
    print(f"\n  --- A3: fill_layer 公开 API ---")
    for attr in sorted(dir(fill_a)):
        if attr.startswith("_"):
            continue
        try:
            val = getattr(fill_a, attr)
            if callable(val):
                print(f"    {attr}()")
            else:
                print(f"    {attr} = {val}")
        except Exception:
            print(f"    {attr} (不可访问)")

    # ══════════════════════════════════════════════════════════
    # B. 测试: Filter Effect 内部 — image input 连接贴图
    # ══════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print("[PROBE] === B. Filter Effect + Image Input 探测 ===")
    print("=" * 60)

    fill_b = None
    filter_node = None
    try:
        position = layerstack.InsertPosition.from_textureset_stack(stack)
        fill_b = layerstack.insert_fill(position)
        fill_b.set_name("__PROBE_B_FILTER_EFFECT__")

        # 先把贴图分配到 Roughness 通道（如果有贴图的话）
        if tex_id:
            ct_rough = textureset.ChannelType.Roughness
            fill_b.set_source(ct_rough, tex_id)
            print(f"  ✅ 贴图已分配到 Roughness: {tex_id.name}")

        # 插入 Filter Effect
        effect_pos = layerstack.InsertPosition.inside_node(
            fill_b, layerstack.NodeStack.Content
        )
        filter_node = layerstack.insert_filter_effect(effect_pos, filter_id)
        print(f"  ✅ Filter Effect 插入成功: {filter_node.uid()}")
    except Exception as e:
        print(f"  设置失败: {e}")
        traceback.print_exc()

    if filter_node:
        # B1: SourceSubstance 参数
        print(f"\n  --- B1: SourceSubstance 参数 ---")
        try:
            source = filter_node.get_source()
            print(f"  type: {type(source).__name__}")
            params = source.get_parameters()
            for k, v in params.items():
                print(f"    '{k}' = {v} ({type(v).__name__})")
        except Exception as e:
            print(f"  参数读取失败: {e}")

        # B2: image_inputs — 这是关键！
        print(f"\n  --- B2: SourceSubstance image_inputs ---")
        try:
            img_in = source.image_inputs
            print(f"  image_inputs 类型: {type(img_in).__name__}")
            print(f"  image_inputs 内容: {img_in}")
            if hasattr(img_in, '__len__'):
                print(f"  image_inputs 长度: {len(img_in)}")
            if hasattr(img_in, 'items'):
                for k, v in img_in.items():
                    print(f"    '{k}' → {v} ({type(v).__name__})")
            elif hasattr(img_in, '__iter__'):
                for i, v in enumerate(img_in):
                    print(f"    [{i}] → {v} ({type(v).__name__})")
                    # 尝试获取更多信息
                    for attr in dir(v):
                        if not attr.startswith("_"):
                            try:
                                av = getattr(v, attr)
                                print(f"        .{attr} = {av}")
                            except Exception:
                                pass
        except Exception as e:
            print(f"  image_inputs 失败: {e}")
            traceback.print_exc()

        # B3: image_outputs
        print(f"\n  --- B3: SourceSubstance image_outputs ---")
        try:
            img_out = source.image_outputs
            print(f"  image_outputs: {img_out}")
        except Exception as e:
            print(f"  image_outputs 失败: {e}")

        # B4: SourceSubstance 全部公开 API
        print(f"\n  --- B4: SourceSubstance 公开 API ---")
        for attr in sorted(dir(source)):
            if attr.startswith("_"):
                continue
            try:
                val = getattr(source, attr)
                if callable(val):
                    print(f"    {attr}()")
                else:
                    print(f"    {attr} = {val!r}")
            except Exception:
                print(f"    {attr} (不可访问)")

        # B5: 尝试 channel_input=1（Custom Input）+ 设置输入图像
        print(f"\n  --- B5: channel_input=1 + image input 连接贴图 ---")
        try:
            # 先设 channel_input=1
            source.set_parameters({"channel_input": 1})
            after = source.get_parameters()
            print(f"  channel_input 设置后: {after.get('channel_input', '??')}")

            # 尝试通过 image_inputs 连接贴图
            if tex_id:
                img_in = source.image_inputs
                if img_in:
                    # 尝试各种连接方式
                    first_input = None
                    if hasattr(img_in, '__getitem__'):
                        try:
                            first_input = img_in[0]
                        except (IndexError, KeyError, TypeError):
                            pass
                    if hasattr(img_in, 'values'):
                        vals = list(img_in.values())
                        if vals:
                            first_input = vals[0]

                    if first_input is not None:
                        print(f"  第一个 image_input: {first_input} ({type(first_input).__name__})")
                        # 尝试 set_source / connect 等
                        for method_name in ["set_source", "connect", "set_image", "set_resource"]:
                            if hasattr(first_input, method_name):
                                try:
                                    getattr(first_input, method_name)(tex_id)
                                    print(f"  ✅ {method_name}(tex_id) 成功！")
                                except Exception as e2:
                                    print(f"  ❌ {method_name}(tex_id) 失败: {e2}")
                    else:
                        print(f"  ⚠ 无法获取 image_input 项")
                else:
                    print(f"  ⚠ image_inputs 为空")
        except Exception as e:
            print(f"  channel_input 设置失败: {e}")
            traceback.print_exc()

        # B6: 设置 RGBA 权重（提取 G 通道 = Roughness）
        print(f"\n  --- B6: 设置 Grayscale Weights (G=1.0) ---")
        try:
            source.set_parameters({
                "grayscale_type": 1,
                "Red": 0.0, "Green": 1.0, "Blue": 0.0, "Alpha": 0.0
            })
            after = source.get_parameters()
            print(f"  ✅ 参数设置成功:")
            for k in ["grayscale_type", "Red", "Green", "Blue", "Alpha", "channel_input"]:
                print(f"    {k} = {after.get(k, '??')}")
        except Exception as e:
            print(f"  参数设置失败: {e}")

        # B7: FilterEffectNode 的 active_channels
        print(f"\n  --- B7: filter_node.active_channels ---")
        try:
            ach = filter_node.active_channels
            print(f"  active_channels: {ach}")
        except Exception as e:
            print(f"  active_channels 失败: {e}")

    # ══════════════════════════════════════════════════════════
    # C. 测试: ChannelFormat 枚举 + add_channel(AO)
    # ══════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print("[PROBE] === C. ChannelFormat + add_channel(AO) ===")
    print("=" * 60)

    # C1: 枚举 ChannelFormat 所有值
    print(f"\n  --- C1: ChannelFormat 枚举 ---")
    try:
        fmt_class = textureset.ChannelFormat
        print(f"  type: {type(fmt_class)}")
        for attr in sorted(dir(fmt_class)):
            if attr.startswith("_"):
                continue
            try:
                val = getattr(fmt_class, attr)
                print(f"    {attr} = {val!r}")
            except Exception:
                print(f"    {attr} (不可访问)")
    except Exception as e:
        print(f"  ChannelFormat 探测失败: {e}")
        traceback.print_exc()

    # C2: 检查 AO 通道是否已存在
    print(f"\n  --- C2: AO 通道检查 ---")
    ao_exists = False
    try:
        ct_ao = textureset.ChannelType.AO
        fmt = stack.get_channel_format(ct_ao)
        print(f"  ✅ AO 通道已存在: format={fmt}")
        ao_exists = True
    except Exception as e:
        print(f"  ❌ AO 通道不存在: {e}")

    # C3: 如果 AO 不存在，尝试添加
    if not ao_exists:
        print(f"\n  --- C3: add_channel(AO) ---")

        # 尝试不同的 ChannelFormat
        formats_to_try = []
        try:
            fmt_class = textureset.ChannelFormat
            for attr in dir(fmt_class):
                if attr.startswith("_"):
                    continue
                if callable(getattr(fmt_class, attr, None)):
                    continue
                formats_to_try.append(attr)
        except Exception:
            pass

        if not formats_to_try:
            formats_to_try = ["L8", "L16", "L16F", "L32F", "sRGB8", "RGB8", "RGB16", "RGB16F", "RGB32F"]

        ct_ao = textureset.ChannelType.AO
        for fmt_name in formats_to_try:
            try:
                fmt_val = getattr(textureset.ChannelFormat, fmt_name, None)
                if fmt_val is None:
                    continue
                stack.add_channel(ct_ao, fmt_val)
                print(f"  ✅ add_channel(AO, {fmt_name}) 成功！")
                ao_exists = True
                break
            except Exception as e:
                print(f"  ❌ add_channel(AO, {fmt_name}) 失败: {e}")
    else:
        print(f"\n  --- C3: 跳过（AO 已存在）---")

    # C4: 添加后再次验证
    if ao_exists:
        print(f"\n  --- C4: AO 通道验证 ---")
        try:
            fmt = stack.get_channel_format(textureset.ChannelType.AO)
            print(f"  ✅ AO 通道 format = {fmt}")
        except Exception as e:
            print(f"  ❌ AO 验证失败: {e}")

    # ══════════════════════════════════════════════════════════
    # D. 额外: Fill Layer 的 per-channel source 探测
    # ══════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print("[PROBE] === D. Fill Layer per-channel source 模型 ===")
    print("=" * 60)

    if fill_a:
        print(f"\n  --- D1: Fill Layer A (filter 作源) 的 get_source 探测 ---")
        # 尝试不同签名的 get_source
        for method_name in ["get_source", "source", "get_channel_source"]:
            if not hasattr(fill_a, method_name):
                continue
            method = getattr(fill_a, method_name)
            if not callable(method):
                print(f"    {method_name} = {method}")
                continue
            # 无参调用
            try:
                result = method()
                print(f"    {method_name}() → {result!r} ({type(result).__name__})")
                # 如果返回值有子属性
                for attr in dir(result):
                    if not attr.startswith("_"):
                        try:
                            v = getattr(result, attr)
                            if not callable(v):
                                print(f"      .{attr} = {v!r}")
                        except Exception:
                            pass
            except Exception as e:
                print(f"    {method_name}() 失败: {e}")
            # 带 ChannelType 参数调用
            for ch_name in ["Roughness", "BaseColor", "Metallic"]:
                try:
                    ct = getattr(textureset.ChannelType, ch_name)
                    result = method(ct)
                    print(f"    {method_name}({ch_name}) → {result!r} ({type(result).__name__})")
                    if hasattr(result, 'resource_id'):
                        print(f"      .resource_id = {result.resource_id}")
                    if hasattr(result, 'get_parameters') and callable(result.get_parameters):
                        params = result.get_parameters()
                        print(f"      .get_parameters() → {params}")
                    if hasattr(result, 'image_inputs'):
                        print(f"      .image_inputs = {result.image_inputs}")
                except Exception as e:
                    print(f"    {method_name}({ch_name}) 失败: {e}")

    # ══════════════════════════════════════════════════════════
    # E. 额外: layerstack 模块 — 有哪些 insert_* 函数
    # ══════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print("[PROBE] === E. layerstack 模块公开 API ===")
    print("=" * 60)
    for attr in sorted(dir(layerstack)):
        if attr.startswith("_"):
            continue
        val = getattr(layerstack, attr)
        if callable(val):
            print(f"  {attr}()")
        else:
            print(f"  {attr} = {val!r}")

    # ══════════════════════════════════════════════════════════
    # F. NodeStack 枚举
    # ══════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print("[PROBE] === F. NodeStack 枚举 ===")
    print("=" * 60)
    try:
        for attr in sorted(dir(layerstack.NodeStack)):
            if attr.startswith("_"):
                continue
            print(f"  NodeStack.{attr} = {getattr(layerstack.NodeStack, attr)!r}")
    except Exception as e:
        print(f"  NodeStack 探测失败: {e}")

    # ══════════════════════════════════════════════════════════
    # 清理说明
    # ══════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print("[PROBE] 探测完成！")
    print(f"  测试层: __PROBE_A_FILTER_SOURCE__, __PROBE_B_FILTER_EFFECT__")
    print(f"  请手动删除测试层后反馈以上输出。")
    print("=" * 60)


try:
    probe()
except Exception as ex:
    import traceback as _tb
    print(f"[PROBE] 顶层异常: {ex}")
    _tb.print_exc()
