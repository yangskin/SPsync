import unreal

editor_actor_subsystem:unreal.EditorActorSubsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
unreal_editor_subsystem:unreal.UnrealEditorSubsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)

def import_mesh(path:str, target_path:str, name:str, scale:float)->str:
    asset_library:unreal.EditorAssetLibrary = unreal.EditorAssetLibrary()
    if asset_library.does_asset_exist(target_path + "/" + name):
        asset_library.delete_asset(target_path + "/" + name)
    
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
    fbx_static_mesh_import_data.import_uniform_scale = scale
    options.static_mesh_import_data = fbx_static_mesh_import_data
    task.options = options

    aset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    aset_tools.import_asset_tasks([task])
    return target_path + "/" + name

def swap_meshes_and_set_material(path:str, materials_folder:str, name:str, udmi:bool):
    static_mesh:unreal.StaticMesh = unreal.EditorAssetLibrary.load_asset(path)
    materials = static_mesh.static_materials
    asset_library:unreal.EditorAssetLibrary = unreal.EditorAssetLibrary()
    
    for index in range(len(materials)): 
        material_instance_path = find_asset(materials_folder, ("M_" if udmi else "MI_") + name + "_" + str(materials[index].material_slot_name))
        if material_instance_path != None:
            static_mesh.set_material(index, asset_library.load_asset(material_instance_path[0 : material_instance_path.rfind(".")]))

    world = unreal_editor_subsystem.get_editor_world()
    actors = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
        
    for actor in actors:
        if static_mesh.get_name() == actor.get_actor_label():
            editor_actor_subsystem.destroy_actor(actor)

    viewport = unreal_editor_subsystem.get_level_viewport_camera_info()
    camera_location = viewport[0]
    camera_rotation = viewport[1]

    spawn_distance = 1000.0
    forward_vector = camera_rotation.get_forward_vector()
    spawn_location = camera_location + forward_vector * spawn_distance

    static_mesh_actor = editor_actor_subsystem.spawn_actor_from_object(static_mesh, spawn_location, unreal.Rotator(0, 0, camera_rotation.yaw).combine(unreal.Rotator(0, 0, -180)))
    editor_actor_subsystem.set_selected_level_actors([static_mesh_actor])

    '''
    ray_start = spawn_location
    ray_end = ray_start + unreal.Vector(0, 0, -10000)
    
    hit_result:unreal.HitResult = unreal.SystemLibrary.line_trace_single(
        world,
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
        
        static_mesh_actor = editor_actor_subsystem.spawn_actor_from_object(static_mesh, ground_location, unreal.Rotator(0, 0, camera_rotation.yaw).combine(unreal.Rotator(0, 0, -180)))
        editor_actor_subsystem.set_selected_level_actors([static_mesh_actor])
    else:
        static_mesh_actor = editor_actor_subsystem.spawn_actor_from_object(static_mesh, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
        editor_actor_subsystem.set_selected_level_actors([static_mesh_actor])
    '''

def import_mesh_and_swap(path:str, target:str, name:str, udmi:bool, scale:float):
    swap_meshes_and_set_material(import_mesh(path, target, name, scale), target, name, udmi)
    return True
