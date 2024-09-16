import unreal

def create_material_instance(parent_material:unreal.Material, path:str)->unreal.MaterialInstanceConstant:
    asset_library:unreal.EditorAssetLibrary = unreal.EditorAssetLibrary()

    if asset_library.do_assets_exist([path]):
        return asset_library.load_asset(path)
    else:
        material_factory = unreal.MaterialInstanceConstantFactoryNew()

        material_instance = unreal.AssetToolsHelpers.get_asset_tools().create_asset(asset_name=path[path.rfind("/") + 1:],package_path=path[0:path.rfind("/")],asset_class=unreal.MaterialInstanceConstant,factory=material_factory)

        if material_instance:    
            material_instance.set_editor_property("parent", parent_material)
            unreal.EditorAssetLibrary.save_asset(path)
            return material_instance
        
def get_material_instance(path:str)->unreal.MaterialInstanceConstant:
    material = create_material(path[0:path.rfind("/")] + "/M_Base")
    return create_material_instance(material, path)