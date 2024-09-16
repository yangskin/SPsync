import unreal

def import_textures():
    paths = [
    EXPORT_TEXTURE_PATH
    ]

    folder_path = "FOLDER_PATH"
    asset_library:unreal.EditorAssetLibrary = unreal.EditorAssetLibrary()

    for path in paths:
        file_name = path[path.rfind("/") + 1 :path.rfind(".")]

        current_texture = asset_library.load_asset(folder_path + "/" + file_name)
        if current_texture:
            srgb = current_texture.get_editor_property("srgb")
            compression_settings = current_texture.get_editor_property("compression_settings")

        importTask:unreal.AssetImportTask = unreal.AssetImportTask()
        importTask.filename = path
        importTask.async_ = False
        importTask.destination_name = file_name
        importTask.destination_path = folder_path
        importTask.replace_existing = True
        importTask.automated = True

        assetTools = unreal.AssetToolsHelpers.get_asset_tools()
        assetTools.import_asset_tasks([importTask])

        if current_texture:
            current_texture = asset_library.load_asset(folder_path + "/" + file_name)
            current_texture.set_editor_property("srgb", srgb)
            current_texture.set_editor_property("compression_settings", compression_settings)

import_textures()

