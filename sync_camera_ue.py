import unreal

level_editor_subsystem:unreal.LevelEditorSubsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
unreal_editor_subsystem:unreal.UnrealEditorSubsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
editor_actor_subsystem:unreal.EditorActorSubsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

level_editor_subsystem.editor_set_game_view(True)

def maya_to_unreal_rotation(x, y, z):
    maya_quaternion = unreal.Rotator(x, y, 360 - z).quaternion()
    return unreal.Quat(-maya_quaternion.z, maya_quaternion.x, maya_quaternion.y, maya_quaternion.w).rotator().combine(unreal.Rotator(0, 0, 180))

def exit_sync_camera():
    level_editor_subsystem.editor_set_game_view(False)
    
def sync_camera(px:float, py:float, pz:float, rx:float, ry:float, rz:float, fov:float):
    selected_actors = editor_actor_subsystem.get_selected_level_actors()

    root_transform:unreal.Transform = None 
    for actor in selected_actors:
        root_transform = actor.get_actor_transform()

    positon:unreal.Vector = unreal.Vector(px, py, pz)
    positon = unreal.Vector(positon.z , -positon.x, positon.y)
    positon = unreal.Vector.multiply_float(positon, 100)
    rotator:unreal.Rotator = maya_to_unreal_rotation(rx, ry, rz)

    if root_transform == None:
        unreal_editor_subsystem.set_level_viewport_camera_info(positon, rotator)
    else:
        unreal_editor_subsystem.set_level_viewport_camera_info(root_transform.transform_location(positon), root_transform.transform_rotation(rotator)) 
    
    level_editor_subsystem.editor_invalidate_viewports()
