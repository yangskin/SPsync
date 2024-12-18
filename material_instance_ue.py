import unreal

def create_material_instance(parent_material:unreal.Material, path:str, material_type:str)->unreal.MaterialInstanceConstant:
    asset_library:unreal.EditorAssetLibrary = unreal.EditorAssetLibrary()

    if asset_library.do_assets_exist([path]):
        return asset_library.load_asset(path)
    else:
        material_factory = unreal.MaterialInstanceConstantFactoryNew()

        material_instance = unreal.AssetToolsHelpers.get_asset_tools().create_asset(asset_name=path[path.rfind("/") + 1:],package_path=path[0:path.rfind("/")],asset_class=unreal.MaterialInstanceConstant,factory=material_factory)

        if material_instance:    
            material_instance.set_editor_property("parent", parent_material)

            if material_type == "masked" or material_type == "translucency":
                overrides:unreal.MaterialInstanceBasePropertyOverrides = unreal.MaterialInstanceBasePropertyOverrides()
                overrides.set_editor_property("override_blend_mode", True)
                if material_type == "masked":
                    overrides.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
                if material_type == "translucency":
                    overrides.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
                material_instance.set_editor_property("base_property_overrides", overrides)

            unreal.EditorAssetLibrary.save_asset(path)
            return material_instance
        
def get_material_instance(path:str, bco_path:str, es_path:str, mra_path:str, n_path:str, udmi:bool, material_type:str)->unreal.MaterialInstanceConstant:
    material = create_material(path[0:path.rfind("/")] + "/M_Base", bco_path, es_path, mra_path, n_path, udmi, "", False)
    return create_material_instance(material, path, material_type)