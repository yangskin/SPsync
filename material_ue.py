import unreal

def create_material(path:str)->unreal.Material:
    asset_library:unreal.EditorAssetLibrary = unreal.EditorAssetLibrary()
    if asset_library.do_assets_exist([path]):
        return asset_library.load_asset(path)
    else:
        material_factory:unreal.MaterialFactoryNew = unreal.MaterialFactoryNew()
        material:unreal.Material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            asset_name=path[path.rfind("/") + 1:],
            package_path=path[0:path.rfind("/")],
            asset_class=unreal.Material,
            factory=material_factory
        )

        if material:
            base_color:unreal.MaterialExpressionTextureSampleParameter2D = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionTextureSampleParameter2D)
            base_color.set_editor_property("parameter_name", "BCO")
            unreal.MaterialEditingLibrary.connect_material_property(base_color, "", unreal.MaterialProperty.MP_BASE_COLOR)

            metallic_roughness_ao:unreal.MaterialExpressionTextureSampleParameter2D = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionTextureSampleParameter2D)
            metallic_roughness_ao.set_editor_property("parameter_name", "MRA")
            metallic_roughness_ao.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_VIRTUAL_LINEAR_COLOR)
            metallic_roughness_ao_texture:unreal.Texture2D = asset_library.load_asset("/Engine/EngineMaterials/Good64x64TilingNoiseHighFreq_Low")
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

            unreal.EditorAssetLibrary.save_asset(path)
            unreal.MaterialEditingLibrary.layout_material_expressions(material)
            return material

def create_material_instance(parent_material:unreal.Material, path:str)->unreal.MaterialInstanceConstant:
    asset_library:unreal.EditorAssetLibrary = unreal.EditorAssetLibrary()
    if asset_library.do_assets_exist([path]):
        return asset_library.load_asset(path)
    else:
        material_factory = unreal.MaterialInstanceConstantFactoryNew()

        material_instance = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            asset_name=path[path.rfind("/") + 1:],
            package_path=path[0:path.rfind("/")],
            asset_class=unreal.MaterialInstanceConstant,
            factory=material_factory
        )

        if material_instance:    
            material_instance.set_editor_property("parent", parent_material)
            unreal.EditorAssetLibrary.save_asset(path)

def get_material(path:str):
    material = create_material(path[0:path.rfind("/")] + "/M_Base")
    return create_material_instance(material, path)

get_material("/Game/Sphere/MI_testtest")
