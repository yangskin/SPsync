import unreal

paths = [
EXPORT_TEXTURE_PATH
]

for path in paths:
    file_name = path[path.rfind("/") + 1 :path.rfind(".")]
    importTask:unreal.AssetImportTask = unreal.AssetImportTask()
    importTask.filename = path
    importTask.destination_name = file_name
    importTask.destination_path = "FOLDER_PATH"
    importTask.replace_existing = True
    importTask.automated = True
    assetTools = unreal.AssetToolsHelpers.get_asset_tools()
    assetTools.import_asset_tasks([importTask])


