import unreal

asset_library:unreal.EditorAssetLibrary = unreal.EditorAssetLibrary()

def find_asset(folder_path, name):
    assets = asset_library.list_assets(folder_path)
    for asset in assets:
        if name in asset:
            return asset
    return None

def get_texture_parameter_value(parameter_name, folder_path, name, srgb_type = True, is_normal = False):
    texture_path = find_asset(folder_path, name)
    if texture_path != None:
        texture = asset_library.load_asset(texture_path[0 : texture_path.rfind(".")])
        texture.set_editor_property("srgb", srgb_type)
        if is_normal:
            texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
        return unreal.TextureParameterValue(parameter_info=unreal.MaterialParameterInfo(parameter_name, unreal.MaterialParameterAssociation.GLOBAL_PARAMETER, -1), parameter_value=texture)
    return None

def create_material_and_connect_texture():
    material_names = [
    MATERIAL_NAMES
    ]

    target_path = "TARGET_PATH"
    
    for material_name in material_names:
        material_instance_path = target_path + "/" + "MI_" + material_name
        if not asset_library.do_assets_exist([material_instance_path]):
            material_instance:unreal.MaterialInstanceConstant = get_material_instance(material_instance_path)

            bco = get_texture_parameter_value("BCO", target_path, material_name + "_BCO")
            mra = get_texture_parameter_value("MRA", target_path, material_name + "_MRAS", False)
            n = get_texture_parameter_value("N", target_path, material_name + "_N", False, True)
            es = get_texture_parameter_value("ES", target_path, material_name + "_ES")

            texture_parameter_values = []
            if bco != None:
                texture_parameter_values.append(bco)
            if mra != None:
                texture_parameter_values.append(mra)
            if n != None:
                texture_parameter_values.append(n)
            if es != None:
                texture_parameter_values.append(es)
                
            if len(texture_parameter_values) > 0:
                material_instance.set_editor_property("texture_parameter_values", texture_parameter_values)

    return True


