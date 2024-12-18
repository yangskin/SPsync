import unreal

def create_material(path:str, bco_path:str, es_path:str, mra_path:str, n_path:str, udmi:bool, material_type:str, emissive_type:bool)->unreal.Material:
    asset_library:unreal.EditorAssetLibrary = unreal.EditorAssetLibrary()
    if asset_library.do_assets_exist([path]):
        return asset_library.load_asset(path)
    else:
        material_factory:unreal.MaterialFactoryNew = unreal.MaterialFactoryNew()
        material:unreal.Material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(asset_name=path[path.rfind("/") + 1:],package_path=path[0:path.rfind("/")],asset_class=unreal.Material,factory=material_factory)
        if material:

            if material_type == "masked":
                material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED) 

            if material_type == "translucency":
                material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT) 
            material.set_editor_property("translucency_lighting_mode", unreal.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
            
            base_color:unreal.MaterialExpressionTextureSampleParameter2D = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionTextureSampleParameter2D)
            base_color.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_VIRTUAL_COLOR if udmi else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
            base_color_texture:unreal.Texture2D = asset_library.load_asset(bco_path)
            base_color.set_editor_property("texture", base_color_texture)
            base_color.set_editor_property("parameter_name", "BCO")
            unreal.MaterialEditingLibrary.connect_material_property(base_color, "", unreal.MaterialProperty.MP_BASE_COLOR)

            dither_function_call:unreal.MaterialExpressionMaterialFunctionCall = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionMaterialFunctionCall)
            dither_function:unreal.MaterialFunction = asset_library.load_asset("/Engine/Functions/Engine_MaterialFunctions02/Utility/DitherTemporalAA")
            dither_function_call.set_material_function(dither_function)
            unreal.MaterialEditingLibrary.connect_material_expressions(base_color, "a", dither_function_call, "Alpha Threshold")
            unreal.MaterialEditingLibrary.connect_material_property(dither_function_call, "Result", unreal.MaterialProperty.MP_OPACITY_MASK)
          
            emissive_scattering:unreal.MaterialExpressionTextureSampleParameter2D = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionTextureSampleParameter2D)
            emissive_scattering.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_VIRTUAL_COLOR if udmi else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
            emissive_scattering_texture:unreal.Texture2D = asset_library.load_asset(es_path)
            emissive_scattering.set_editor_property("texture", emissive_scattering_texture)
            emissive_scattering.set_editor_property("parameter_name", "ES")
            emissive_mul_node:unreal.MaterialExpressionMultiply = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionMultiply)
            unreal.MaterialEditingLibrary.connect_material_expressions(emissive_scattering, "rgb", emissive_mul_node, "a")
            emissive_scalar_node:unreal.MaterialExpressionScalarParameter = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionScalarParameter)
            emissive_scalar_node.set_editor_property("parameter_name", "emissive_intensity")
            emissive_scalar_node.set_editor_property("default_value", 1 if emissive_type else 0)
            unreal.MaterialEditingLibrary.connect_material_expressions(emissive_scalar_node, "", emissive_mul_node, "b")
            unreal.MaterialEditingLibrary.connect_material_property(emissive_mul_node, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
            #unreal.MaterialEditingLibrary.connect_material_property(emissive_scattering, "a", unreal.MaterialProperty.MP)

            metallic_roughness_ao:unreal.MaterialExpressionTextureSampleParameter2D = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionTextureSampleParameter2D)
            metallic_roughness_ao.set_editor_property("parameter_name", "MRA")
            metallic_roughness_ao.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_VIRTUAL_LINEAR_COLOR if udmi else unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
            metallic_roughness_ao_texture:unreal.Texture2D = asset_library.load_asset(mra_path)
            metallic_roughness_ao.set_editor_property("texture", metallic_roughness_ao_texture)
            unreal.MaterialEditingLibrary.connect_material_property(metallic_roughness_ao, "r", unreal.MaterialProperty.MP_METALLIC)
            unreal.MaterialEditingLibrary.connect_material_property(metallic_roughness_ao, "g", unreal.MaterialProperty.MP_ROUGHNESS)
            unreal.MaterialEditingLibrary.connect_material_property(metallic_roughness_ao, "b", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
            one_mius:unreal.MaterialExpressionOneMinus = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionOneMinus)
            unreal.MaterialEditingLibrary.connect_material_expressions(metallic_roughness_ao, "a", one_mius, "")
            unreal.MaterialEditingLibrary.connect_material_property(one_mius, "", unreal.MaterialProperty.MP_OPACITY)

            normal:unreal.MaterialExpressionTextureSampleParameter2D = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionTextureSampleParameter2D)
            normal.set_editor_property("parameter_name", "N")
            normal.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_VIRTUAL_NORMAL if udmi else unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
            normal_texture:unreal.Texture2D = asset_library.load_asset(n_path)
            normal.set_editor_property("texture", normal_texture)
            unreal.MaterialEditingLibrary.connect_material_property(normal, "", unreal.MaterialProperty.MP_NORMAL)
        
            unreal.MaterialEditingLibrary.layout_material_expressions(material)
            unreal.MaterialEditingLibrary.recompile_material(material)
            material.modify()
            unreal.MaterialEditingLibrary.recompile_material(material)
            
            return material