import bpy
from ..sollumz_properties import SollumType

def animations_filter(self, object):
    if len(bpy.context.selected_objects) <= 0:
        return False

    active_object = bpy.context.selected_objects[0]

    if active_object.sollum_type != SollumType.CLIP:
        return False

    return object.sollum_type == SollumType.ANIMATION and active_object.parent.parent == object.parent.parent


class ClipDictionary(bpy.types.PropertyGroup):
    pass


class ClipAnimation(bpy.types.PropertyGroup):
    start_frame: bpy.props.IntProperty(name='Start Frame', default=0, min=0, description='First frame of the playback area')
    end_frame: bpy.props.IntProperty(name='End Frame', default=0, min=0, description='Last frame (inclusive) of the playback area')

    animation: bpy.props.PointerProperty(name='Animation', type=bpy.types.Object, poll=animations_filter)


class ClipProperties(bpy.types.PropertyGroup):
    hash: bpy.props.StringProperty(name='Hash', default='')
    name: bpy.props.StringProperty(name='Name', default='')

    duration: bpy.props.FloatProperty(name='Duration', default=0, min=0, description='Duration of the clip in seconds')

    start_frame: bpy.props.IntProperty(name='Start Frame', default=0, min=0)
    end_frame: bpy.props.IntProperty(name='End Frame', default=0, min=0)

    animations: bpy.props.CollectionProperty(name='Animations', type=ClipAnimation)

class AnimationProperties(bpy.types.PropertyGroup):
    hash: bpy.props.StringProperty(name='Hash', default='')
    frame_count: bpy.props.IntProperty(name='Frame Count', default=1, min=1)

    armature: bpy.props.PointerProperty(
        name='Armature', 
        type=bpy.types.Armature, 
        description="Armature source. Leave empty for camera or drawable that does not have an armature")

    base_action: bpy.props.PointerProperty(
        name='Base', 
        type=bpy.types.Action, 
        description="Action for object with Armature such as ped or vehicle")

    root_motion_location_action: bpy.props.PointerProperty(
        name='Root Position', 
        type=bpy.types.Action, 
        description="Action for model collision position in space, known as Root Motion")

    root_motion_rotation_action: bpy.props.PointerProperty(
        name='Root Rotation', 
        type=bpy.types.Action, 
        description="Action for model collision rotation in space, known as Root Motion")

    camera_action: bpy.props.PointerProperty(
        name='Camera', 
        type=bpy.types.Action, 
        description="Action for camera transformation in space")

    camera_fov_action: bpy.props.PointerProperty(
        name='Camera FOV', 
        type=bpy.types.Action, 
        description="Action for camera fov")

def register():
    bpy.types.Object.clip_dict_properties = bpy.props.PointerProperty(type=ClipDictionary)
    bpy.types.Object.clip_properties = bpy.props.PointerProperty(type=ClipProperties)
    bpy.types.Object.animation_properties = bpy.props.PointerProperty(type=AnimationProperties)


def unregister():
    del bpy.types.Object.clip_dict_properties
    del bpy.types.Object.clip_properties
    del bpy.types.Object.animation_properties
