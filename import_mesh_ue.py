import unreal

def import_mesh(path:str, target_path:str, name:str)->str:
    task = unreal.AssetImportTask()
    task.filename = path
    task.destination_path = target_path
    task.destination_name = name
    task.replace_existing = True
    task.automated = True
    task.save = True
    
    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_textures = False
    options.import_materials = False
    options.import_as_skeletal = False
    options.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
    fbx_static_mesh_import_data = unreal.FbxStaticMeshImportData()
    fbx_static_mesh_import_data.force_front_x_axis =True
    fbx_static_mesh_import_data.combine_meshes = True
    fbx_static_mesh_import_data.import_uniform_scale = 100.0
    options.static_mesh_import_data = fbx_static_mesh_import_data
    task.options = options

    aset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    aset_tools.import_asset_tasks([task])
    return target_path + "/" + name

def swap_meshes_and_set_material(path:str, materials_folder:str, name:str):
    static_mesh:unreal.StaticMesh = unreal.EditorAssetLibrary.load_asset(path)
    materials = static_mesh.static_materials
    asset_library:unreal.EditorAssetLibrary = unreal.EditorAssetLibrary()
    
    for index in range(len(materials)): 
        material_instance_path = find_asset(materials_folder, "MI_" + name + "_" + str(materials[index].material_slot_name))
        if material_instance_path != None:
            static_mesh.set_material(index, asset_library.load_asset(material_instance_path[0 : material_instance_path.rfind(".")]))

    world = unreal.EditorLevelLibrary.get_editor_world()
    actors = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
        

    for actor in actors:
        if static_mesh.get_name() == actor.get_actor_label():
            unreal.EditorLevelLibrary.destroy_actor(actor)

    #static_mesh_actor = unreal.EditorLevelLibrary.spawn_actor_from_object(static_mesh, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
    viewport = unreal.EditorLevelLibrary.get_level_viewport_camera_info()
    camera_location = viewport[0]
    camera_rotation = viewport[1]

    spawn_distance = 1000.0
    forward_vector = camera_rotation.get_forward_vector()
    spawn_location = camera_location + forward_vector * spawn_distance
    
    ray_start = spawn_location
    ray_end = ray_start + unreal.Vector(0, 0, -10000)
    
    hit_result:unreal.HitResult = unreal.SystemLibrary.line_trace_single(
        unreal.EditorLevelLibrary.get_editor_world(),
        ray_start,
        ray_end,
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
        False,
        [],
        unreal.DrawDebugTrace.NONE,
        True
    )
    
    if hit_result:
        ground_location = hit_result.to_tuple()[4]
        static_mesh_actor = unreal.EditorLevelLibrary.spawn_actor_from_object(static_mesh, ground_location, camera_rotation.combine(unreal.Rotator(0, 0, -180)))
        unreal.EditorLevelLibrary.set_selected_level_actors([static_mesh_actor])
    else:
        static_mesh_actor = unreal.EditorLevelLibrary.spawn_actor_from_object(static_mesh, unreal.Vector(0, 0, 0), unreal.Quat.IDENTITY)

def import_mesh_and_swap(path:str, target:str, name:str):
    swap_meshes_and_set_material(import_mesh(path, target, name), target, name)
    return True
