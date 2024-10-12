import unreal

asset_library:unreal.EditorAssetLibrary = unreal.EditorAssetLibrary()

def set_texture_srgb_off(folder_path, name):
    texture_path = find_asset(folder_path, name)
    if texture_path != None:
        texture:unreal.Texture2D = asset_library.load_asset(texture_path[0 : texture_path.rfind(".")])
        texture.set_editor_property("srgb", False)

def set_texture_normal(folder_path, name):
    texture_path = find_asset(folder_path, name)
    if texture_path != None:
        texture = asset_library.load_asset(texture_path[0 : texture_path.rfind(".")])
        texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)

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
    mesh_name = "MESH_NAME"
    udim_type = UDIM_TYPE
    masked = MASKED
    translucent = TRANSLUCENT

    for material_name in material_names:
        material_path = target_path + "/" + ("M_" if udim_type else "MI_") + mesh_name + "_" + material_name

        if not asset_library.do_assets_exist([material_path]):
            bco_name = "T_" + mesh_name + "_" + material_name + "_BCO"
            mra_name = "T_" + mesh_name + "_" + material_name + "_MRAS"
            es_name = "T_" + mesh_name + "_" + material_name + "_ES"
            n_name = "T_" + mesh_name + "_" + material_name + "_N"

            texture_path = find_asset(target_path, es_name)
            if texture_path == None:
                es_name = bco_name

            if udim_type:
                set_texture_srgb_off(target_path, mra_name)
                set_texture_normal(target_path, n_name)
                create_material(material_path, 
                                target_path + '/' + bco_name,
                                target_path + '/' + es_name,   
                                target_path + '/' + mra_name,
                                target_path + '/' + n_name,
                                True, masked, translucent)
                
            else:
                bco = get_texture_parameter_value("BCO", target_path, bco_name)
                mra = get_texture_parameter_value("MRA", target_path, mra_name, False)
                n = get_texture_parameter_value("N", target_path, n_name, False, True)
                es = get_texture_parameter_value("ES", target_path, es_name)

                material_instance:unreal.MaterialInstanceConstant = get_material_instance(material_path, 
                                                                                        target_path + '/' + bco_name,
                                                                                        target_path + '/' + es_name,   
                                                                                        target_path + '/' + mra_name,
                                                                                        target_path + '/' + n_name,
                                                                                        False, masked, translucent)

                texture_parameter_values = []
                if bco != None:
                    texture_parameter_values.append(bco)
                if mra != None:
                    texture_parameter_values.append(mra)
                if n != None:
                    texture_parameter_values.append(n)
                if es != None:
                    texture_parameter_values.append(es)
                    unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value,(material_instance, "emissive_intensity" , 1)
                
                if len(texture_parameter_values) > 0:
                    material_instance.set_editor_property("texture_parameter_values", texture_parameter_values)

    return True


