import unreal

asset_library:unreal.EditorAssetLibrary = unreal.EditorAssetLibrary()
def find_asset(folder_path, name):
    assets = asset_library.list_assets(folder_path)
    for asset in assets:
        if name == asset[asset.rfind("/") + 1 : asset.rfind(".")]:
            return asset
    return None

def import_textures():
    paths = [
    EXPORT_TEXTURE_PATH
    ]

    folder_path = "FOLDER_PATH"
    asset_library:unreal.EditorAssetLibrary = unreal.EditorAssetLibrary()
    asset_tools:unreal.AssetTools = unreal.AssetToolsHelpers.get_asset_tools()

    for path in paths:
        file_name = path[path.rfind("/") + 1 :path.rfind(".")]
        file_path = folder_path + "/" + file_name

        if asset_library.do_assets_exist([file_path]):
            data = unreal.AutomatedAssetImportData()
            data.set_editor_property("destination_path", folder_path)
            data.set_editor_property("filenames", [path])
            data.set_editor_property("replace_existing", True)
            asset_tools.import_assets_automated(data)

        else:
            importTask:unreal.AssetImportTask = unreal.AssetImportTask()
            importTask.filename = path
            importTask.destination_name = file_name
            importTask.destination_path = folder_path
            importTask.replace_existing = True
            importTask.replace_existing_settings = False
            importTask.automated = True
            asset_tools.import_asset_tasks([importTask])
 
    return True

