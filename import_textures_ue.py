import unreal

asset_library:unreal.EditorAssetLibrary = unreal.EditorAssetLibrary()
def find_asset(folder_path, name, contain:bool = True):
    assets = asset_library.list_assets(folder_path)
    for asset in assets:
        if contain:
            if name in asset:
                return asset
        else:
            if name == asset[asset.rfind("/") + 1 : asset.rfind(".")]:
                return asset
    return None

def import_textures():
    paths = [
    EXPORT_TEXTURE_PATH
    ]

    folder_path = "FOLDER_PATH"
    asset_library:unreal.EditorAssetLibrary = unreal.EditorAssetLibrary()

    for path in paths:
        file_name = path[path.rfind("/") + 1 :path.rfind(".")]
        file_path = folder_path + "/" + file_name

        current_texture:unreal.Texture2D = None
        if asset_library.do_assets_exist([file_path]):
            current_texture:unreal.Texture2D = asset_library.load_asset(file_path)
            if current_texture:
                srgb = current_texture.get_editor_property("srgb")
                compression_settings = current_texture.get_editor_property("compression_settings")
                lod_group = current_texture.get_editor_property("lod_group")

        importTask:unreal.AssetImportTask = unreal.AssetImportTask()
        importTask.filename = path
        importTask.async_ = False
        importTask.destination_name = file_name
        importTask.destination_path = folder_path
        importTask.replace_existing = True
        importTask.replace_existing_settings = False
        importTask.automated = True

        assetTools = unreal.AssetToolsHelpers.get_asset_tools()
        assetTools.import_asset_tasks([importTask])

        if current_texture != None:
            current_texture = asset_library.load_asset(file_path)
            current_texture.set_editor_property("srgb", srgb)
            current_texture.set_editor_property("compression_settings", compression_settings)
            current_texture.set_editor_property("lod_group", lod_group)

import_textures()

