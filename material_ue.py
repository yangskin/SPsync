import unreal

def create_material(path:str)->unreal.Material:
    asset_library:unreal.EditorAssetLibrary = unreal.EditorAssetLibrary()
    if asset_library.do_assets_exist([path]):
        return asset_library.load_asset(path)
    else:
        material_factory:unreal.MaterialFactoryNew = unreal.MaterialFactoryNew()
        material:unreal.Material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(asset_name=path[path.rfind("/") + 1:],package_path=path[0:path.rfind("/")],asset_class=unreal.Material,factory=material_factory)
        if material:
            base_color:unreal.MaterialExpressionTextureSampleParameter2D = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionTextureSampleParameter2D)
            base_color.set_editor_property("parameter_name", "BCO")
            unreal.MaterialEditingLibrary.connect_material_property(base_color, "", unreal.MaterialProperty.MP_BASE_COLOR)
          
            emissive_scattering:unreal.MaterialExpressionTextureSampleParameter2D = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionTextureSampleParameter2D)
            emissive_scattering_texture:unreal.Texture2D = asset_library.load_asset("/Engine/EngineResources/Black")
            emissive_scattering.set_editor_property("texture", emissive_scattering_texture)
            emissive_scattering.set_editor_property("parameter_name", "ES")
            unreal.MaterialEditingLibrary.connect_material_property(emissive_scattering, "rgb", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
            #unreal.MaterialEditingLibrary.connect_material_property(emissive_scattering, "a", unreal.MaterialProperty.MP)

            metallic_roughness_ao:unreal.MaterialExpressionTextureSampleParameter2D = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionTextureSampleParameter2D)
            metallic_roughness_ao.set_editor_property("parameter_name", "MRA")
            metallic_roughness_ao.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
            metallic_roughness_ao_texture:unreal.Texture2D = asset_library.load_asset("/Engine/EngineMaterials/RandomAngles")
            metallic_roughness_ao.set_editor_property("texture", metallic_roughness_ao_texture)
            unreal.MaterialEditingLibrary.connect_material_property(metallic_roughness_ao, "r", unreal.MaterialProperty.MP_METALLIC)
            unreal.MaterialEditingLibrary.connect_material_property(metallic_roughness_ao, "g", unreal.MaterialProperty.MP_ROUGHNESS)
            unreal.MaterialEditingLibrary.connect_material_property(metallic_roughness_ao, "b", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)

            normal:unreal.MaterialExpressionTextureSampleParameter2D = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionTextureSampleParameter2D)
            normal.set_editor_property("parameter_name", "N")
            normal.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
            normal_texture:unreal.Texture2D = asset_library.load_asset("/Engine/EngineMaterials/FlatNormal")
            normal.set_editor_property("texture", normal_texture)
            unreal.MaterialEditingLibrary.connect_material_property(normal, "", unreal.MaterialProperty.MP_NORMAL)

            unreal.MaterialEditingLibrary.layout_material_expressions(material)
            unreal.MaterialEditingLibrary.recompile_material(material)
            material.modify()
            unreal.MaterialEditingLibrary.recompile_material(material)
            
            return material