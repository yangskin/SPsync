# -*- coding: utf-8 -*-
"""SP probe script - Verify texture connection to Grayscale Filter input on Fill Layer.

Execute in SP Python Console:
  exec(open(r"C:\\Users\\tiany\\Documents\\Adobe\\Adobe Substance 3D Painter\\python\\plugins\\SPsync\\tests\\probe_filter_input_connect.py", encoding="utf-8").read())

Goal: Verify the complete pipeline:
  1. Create Fill Layer
  2. set_source(ChannelType, grayscale_filter_id) - filter as channel source
  3. get_source(ChannelType) -> SourceSubstance
  4. source.set_source("input", texture_resource_id) - connect packed texture
  5. set_parameters for RGBA weights
  6. Visual verification
"""


def probe():
    import traceback
    SEP = "=" * 60

    import substance_painter.resource as resource
    import substance_painter.layerstack as layerstack
    import substance_painter.textureset as textureset
    import substance_painter.project as project

    if not project.is_open():
        print("[PROBE2] ERROR: Open a project first.")
        return

    print(SEP)
    print("[PROBE2] Filter Input Connection Test")
    print(SEP)

    # -- Setup --
    all_ts = textureset.all_texture_sets()
    ts = all_ts[0]
    stack = ts.get_stack()
    print(f"  TextureSet: {ts.name()}")

    # Find filter
    filter_results = resource.search('u:filter n:"Grayscale Conversion"')
    if not filter_results:
        print("  No Grayscale Conversion filter found!")
        return
    filter_id = filter_results[0].identifier()
    print(f"  Filter: {filter_id.name}")

    # Find a texture (prefer one with RGB data)
    tex_results = resource.search("u:texture")
    tex_id = tex_results[0].identifier() if tex_results else None
    if not tex_id:
        print("  No texture found!")
        return
    print(f"  Texture: {tex_id.name}")

    # Ensure Roughness channel exists
    try:
        stack.add_channel(textureset.ChannelType.Roughness, textureset.ChannelFormat.L8)
        print("  Added Roughness channel")
    except Exception:
        print("  Roughness channel already exists or add failed (ok)")

    # ============================================================
    # TEST 1: set_source on fill layer -> SourceSubstance -> set_source("input", tex)
    # ============================================================
    print(f"\n{SEP}")
    print("[PROBE2] === TEST 1: source.set_source() signatures ===")
    print(SEP)

    pos = layerstack.InsertPosition.from_textureset_stack(stack)
    fill = layerstack.insert_fill(pos)
    fill.set_name("__PROBE2_TEST1__")

    # Step 1: Set filter as Roughness source
    ct_rough = textureset.ChannelType.Roughness
    fill.set_source(ct_rough, filter_id)
    print("  1. set_source(Roughness, filter_id) OK")

    # Step 2: Get SourceSubstance
    source = fill.get_source(ct_rough)
    print(f"  2. get_source(Roughness) -> {type(source).__name__}({source.uid()})")
    print(f"     image_inputs: {source.image_inputs}")

    # Step 3: Try various set_source signatures
    print(f"\n  --- 3. Trying source.set_source() signatures ---")

    # 3a: set_source("input", tex_id)
    print(f"\n  3a: source.set_source('input', tex_id)")
    try:
        source.set_source("input", tex_id)
        print(f"      OK!")
        # Verify with get_source
        try:
            inner = source.get_source("input")
            print(f"      get_source('input') -> {inner!r}")
        except Exception as e:
            print(f"      get_source('input') failed: {e}")
    except Exception as e:
        print(f"      FAILED: {e}")
        traceback.print_exc()

    # 3b: set_source("custom_input", tex_id)
    print(f"\n  3b: source.set_source('custom_input', tex_id)")
    try:
        source.set_source("custom_input", tex_id)
        print(f"      OK!")
        try:
            inner = source.get_source("custom_input")
            print(f"      get_source('custom_input') -> {inner!r}")
        except Exception as e:
            print(f"      get_source('custom_input') failed: {e}")
    except Exception as e:
        print(f"      FAILED: {e}")

    # 3c: set_source(tex_id) - no input name
    print(f"\n  3c: source.set_source(tex_id)")
    try:
        source.set_source(tex_id)
        print(f"      OK!")
    except Exception as e:
        print(f"      FAILED: {e}")

    # Step 4: Set parameters
    print(f"\n  --- 4. Set Grayscale Weights (R=1.0 extract Red) ---")
    try:
        source.set_parameters({
            "grayscale_type": 1,
            "Red": 1.0, "Green": 0.0, "Blue": 0.0, "Alpha": 0.0
        })
        after = source.get_parameters()
        print(f"      grayscale_type={after.get('grayscale_type')}")
        print(f"      R={after.get('Red')} G={after.get('Green')} B={after.get('Blue')} A={after.get('Alpha')}")
        print(f"      channel_input={after.get('channel_input')}")
        print("      OK!")
    except Exception as e:
        print(f"      FAILED: {e}")

    # ============================================================
    # TEST 2: Full pipeline - 3 channels from same texture
    # ============================================================
    print(f"\n{SEP}")
    print("[PROBE2] === TEST 2: Full MRO Pipeline (3 layers, 1 texture) ===")
    print(SEP)

    channels_config = [
        ("Metallic", {"Red": 1.0, "Green": 0.0, "Blue": 0.0, "Alpha": 0.0}),
        ("Roughness", {"Red": 0.0, "Green": 1.0, "Blue": 0.0, "Alpha": 0.0}),
        ("AO", {"Red": 0.0, "Green": 0.0, "Blue": 1.0, "Alpha": 0.0}),
    ]

    # Ensure channels exist
    for ch_name, _ in channels_config:
        ct = getattr(textureset.ChannelType, ch_name)
        try:
            stack.add_channel(ct, textureset.ChannelFormat.L8)
            print(f"  Added channel: {ch_name}")
        except Exception:
            print(f"  Channel {ch_name} exists or add failed (ok)")

    # Import a test texture (use existing project resource)
    print(f"\n  Using texture: {tex_id.name}")

    for ch_name, weights in channels_config:
        print(f"\n  --- Creating {ch_name} layer ---")
        try:
            ct = getattr(textureset.ChannelType, ch_name)

            # Create Fill Layer
            pos = layerstack.InsertPosition.from_textureset_stack(stack)
            layer = layerstack.insert_fill(pos)
            layer.set_name(f"__PROBE2_MRO_{ch_name}__")

            # Set filter as channel source
            layer.set_source(ct, filter_id)
            print(f"    set_source({ch_name}, filter) OK")

            # Get SourceSubstance and connect texture
            src = layer.get_source(ct)
            print(f"    image_inputs: {src.image_inputs}")

            # Try input first, then custom_input
            connected = False
            for input_name in ["input", "custom_input"]:
                if input_name in src.image_inputs:
                    try:
                        src.set_source(input_name, tex_id)
                        print(f"    set_source('{input_name}', tex) OK")
                        connected = True
                        break
                    except Exception as e:
                        print(f"    set_source('{input_name}', tex) FAILED: {e}")

            if not connected:
                print(f"    WARNING: Could not connect texture!")

            # Set weights
            src.set_parameters({
                "grayscale_type": 1,
                **weights,
            })
            after_params = src.get_parameters()
            print(f"    Weights: R={after_params['Red']:.1f} G={after_params['Green']:.1f} B={after_params['Blue']:.1f}")
            print(f"    OK!")

        except Exception as e:
            print(f"    FAILED: {e}")
            traceback.print_exc()

    # ============================================================
    # TEST 3: Verify get_source("input") readback
    # ============================================================
    print(f"\n{SEP}")
    print("[PROBE2] === TEST 3: Verify SourceSubstance sub-source readback ===")
    print(SEP)

    # Use the first test layer
    try:
        src_test = fill.get_source(ct_rough)
        for input_name in src_test.image_inputs:
            try:
                inner = src_test.get_source(input_name)
                print(f"  get_source('{input_name}') -> {inner!r} ({type(inner).__name__})")
                if inner is not None:
                    for attr in ["resource_id", "image_inputs", "uid"]:
                        try:
                            v = getattr(inner, attr)
                            if callable(v):
                                v = v()
                            print(f"    .{attr} = {v!r}")
                        except Exception:
                            pass
            except Exception as e:
                print(f"  get_source('{input_name}') FAILED: {e}")
    except Exception as e:
        print(f"  TEST 3 FAILED: {e}")

    # ============================================================
    # TEST 4: set_material_source (alternative approach)
    # ============================================================
    print(f"\n{SEP}")
    print("[PROBE2] === TEST 4: set_material_source / get_material_source ===")
    print(SEP)
    try:
        ms = fill.get_material_source()
        print(f"  get_material_source() -> {ms!r} ({type(ms).__name__})")
        if ms:
            for attr in dir(ms):
                if not attr.startswith("_"):
                    try:
                        v = getattr(ms, attr)
                        if not callable(v):
                            print(f"    .{attr} = {v!r}")
                    except Exception:
                        pass
    except Exception as e:
        print(f"  get_material_source() FAILED: {e}")

    # ============================================================
    # Summary
    # ============================================================
    print(f"\n{SEP}")
    print("[PROBE2] Done!")
    print("  Test layers: __PROBE2_TEST1__, __PROBE2_MRO_Metallic/Roughness/AO__")
    print("  VISUALLY check: Do MRO layers show correct channel extraction?")
    print("  Then delete test layers and report output.")
    print(SEP)


try:
    probe()
except Exception as ex:
    import traceback as _tb
    print(f"[PROBE2] Top-level exception: {ex}")
    _tb.print_exc()
