import unreal

def find_camera_by_name(camera_name:str):

    world = unreal.EditorLevelLibrary.get_editor_world()
    actors = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.CameraActor)
    
    for actor in actors:
        if camera_name in actor.get_actor_label():
            return actor
    return None

def create_and_activate_camera(camera_name, location=unreal.Vector(0, 0, 300), rotation=unreal.Rotator(0, 0, 0)):

    existing_camera = find_camera_by_name(camera_name)
    if existing_camera:
        return existing_camera

    camera_actor = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.CameraActor, location, rotation, True)
    camera_actor.set_actor_label(camera_name)
    unreal.EditorLevelLibrary.pilot_level_actor(camera_actor)
    return camera_actor

def maya_to_unreal_rotation(x, y, z):
    maya_quaternion = unreal.Rotator(x, y, 360 - z).quaternion()
    return unreal.Quat(-maya_quaternion.z, maya_quaternion.x, maya_quaternion.y, maya_quaternion.w).rotator().combine(unreal.Rotator(0, 0, 180))

camera_actor:unreal.Actor = create_and_activate_camera("temp_camera")

selected_actors = unreal.EditorLevelLibrary.get_selected_level_actors()


root_transform:unreal.Transform = None 
for actor in selected_actors:
    root_transform = actor.get_actor_transform()

positon:unreal.Vector = unreal.Vector(POS)
positon = unreal.Vector(positon.z , -positon.x, positon.y)
positon = unreal.Vector.multiply_float(positon, 100)
rotator:unreal.Rotator = maya_to_unreal_rotation(ROTATE)

if root_transform == None:
    camera_actor.set_actor_location_and_rotation(positon, rotator, False, False)
else:
    camera_actor.set_actor_location_and_rotation(root_transform.transform_location(positon), root_transform.transform_rotation(rotator), False, False)

camera_component = camera_actor.get_component_by_class(unreal.CameraComponent)
if camera_component:
    camera_component.set_editor_property("constrain_aspect_ratio", False)
    camera_component.set_editor_property("field_of_view", FOV)

unreal.EditorLevelLibrary.pilot_level_actor(camera_actor)