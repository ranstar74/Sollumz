from argparse import Action
import enum
import bpy
from bpy.types import PoseBone
from mathutils import Vector
from numpy import deg2rad

from ..resources.clipsdictionary import *
from ..sollumz_properties import SollumType
from ..tools.jenkhash import Generate
from ..tools.blenderhelper import build_tag_bone_map, get_armature_obj
from ..tools.animationhelper import *

def get_name(item):
    return item.name.split('.')[0]

def ensure_action_track(track_type: TrackType, action_type: ActionType):
    """Gets valid track type for specified action type."""
    if action_type is ActionType.RootMotion:
        if track_type is TrackType.BonePosition:
            return TrackType.RootMotionPosition
        if track_type is TrackType.BoneRotation:
            return TrackType.RootMotionRotation

    if action_type is ActionType.Camera:
        if track_type is TrackType.BonePosition:
            return TrackType.CameraPosition
        if track_type is TrackType.BoneRotation:
            return TrackType.CameraRotation

    return track_type

def transform_location_to_armature_space(locations_map, bones_map):
    for tag, positions in locations_map.items():
        p_bone = bones_map[tag]
        bone = p_bone.bone

        for frame_id, position in enumerate(positions):
            mat = bone.matrix_local

            if (bone.parent != None):
                mat = bone.parent.matrix_local.inverted() @ bone.matrix_local

                mat_decomposed = mat.decompose()

                bone_location = mat_decomposed[0]
                bone_rotation = mat_decomposed[1]

                position.rotate(bone_rotation)

                diff_location = Vector((
                    (position.x + bone_location.x),
                    (position.y + bone_location.y),
                    (position.z + bone_location.z),
                ))

                positions[frame_id] = diff_location

def sequence_items_from_armature_action(action, sequence_items, bones_map, action_type, frame_count, has_bones):
    locations_map = {}
    rotations_map = {}
    scales_map = {}
    cam_fov_map = {}

    # Extract track data to maps
    p_bone: PoseBone
    for tag, p_bone in bones_map.items():

        if has_bones:
            location_path = p_bone.path_from_id('location')
            rotation_quaternion_path = p_bone.path_from_id('rotation_quaternion')
            rotation_euler_path = p_bone.path_from_id('rotation_euler')
            scale_path = p_bone.path_from_id('scale')
        else:
            location_path = 'location'
            rotation_quaternion_path = 'rotation_quaternion'
            rotation_euler_path = 'rotation_euler'
            scale_path = 'scale'

        if action_type == ActionType.CameraFov:
            fov_path = 'sensor_width'

            fovs = evaluate_float(action.fcurves, 
                fov_path, frame_count)
            
            if len(fovs) > 0:
                cam_fov_map[0] = fovs

        # Get list of per-frame data for every path

        b_locations = evaluate_vector(action.fcurves, 
            location_path, frame_count)
        b_quaternions = evaluate_quaternion(action.fcurves, 
            rotation_quaternion_path, frame_count)
        b_euler_quaternions = evaluate_euler_to_quaternion(action.fcurves, 
            rotation_euler_path, frame_count)
        b_scales = evaluate_vector(action.fcurves, 
            scale_path, frame_count)

        # Link them with Bone ID

        if len(b_locations) > 0:
            locations_map[tag] = b_locations

        # Its a bit of a edge case scenario because blender uses either
        # euler or quaternion (I cant really understand why quaternion doesnt update with euler)
        # So we will prefer quaternion over euler for now
        # TODO: Theres also third rotation in blender, angles or something...
        
        if len(b_quaternions) > 0:
            rotations_map[tag] = b_quaternions
        elif len(b_euler_quaternions) > 0:
            rotations_map[tag] = b_euler_quaternions

        if len(b_scales) > 0:
            scales_map[tag] = b_scales

    if has_bones:
        transform_location_to_armature_space(locations_map, bones_map)

    for tag, quaternions in rotations_map.items():
        if has_bones:
            p_bone = bones_map[tag]
            bone = p_bone.bone

        prev_quaternion = None
        for index, quaternion in enumerate(quaternions):
            if has_bones:
                # Transform rotation from local to armature space
                if p_bone.parent is not None:
                    pose_rot = Matrix.to_quaternion(bone.matrix)
                    quaternion.rotate(pose_rot)

            euler = Quaternion.to_euler(quaternion)

            # For some reason camera up axis is different
            if action_type is ActionType.Camera:
                euler.x -= deg2rad(90)

            quaternion = Euler.to_quaternion(euler)

            if prev_quaternion is not None:
                fix_quaternion_lerp(quaternion, prev_quaternion)

            rotations_map[tag][index] = quaternion
            prev_quaternion = quaternion

    # WARNING: ANY OPERATION WITH ROTATION WILL CAUSE SIGN CHANGE. PROCEED ANYTHING BEFORE FIX.

    if len(locations_map) > 0:
        sequence_items[ensure_action_track(TrackType.BonePosition, action_type)] = locations_map

    if len(rotations_map) > 0:
        sequence_items[ensure_action_track(TrackType.BoneRotation, action_type)] = rotations_map

    if len(scales_map) > 0:
        sequence_items[ensure_action_track(TrackType.BoneScale, action_type)] = scales_map

    if len(cam_fov_map) > 0:
        sequence_items[TrackType.CameraFov] = cam_fov_map

def build_values_channel(values, uniq_values, indirect_percentage=0.1):
    values_len_percentage = len(uniq_values) / len(values)

    if len(uniq_values) == 1:
        channel = ChannelsListProperty.StaticFloat()

        channel.value = uniq_values[0]
    elif values_len_percentage <= indirect_percentage:
        channel = ChannelsListProperty.IndirectQuantizeFloat()

        min_value, quantum = get_quantum_and_min_val(uniq_values)

        channel.values = uniq_values
        channel.offset = min_value
        channel.quantum = quantum

        for value in values:
            channel.frames.append(uniq_values.index(value))
    else:
        channel = ChannelsListProperty.QuantizeFloat()

        min_value, quantum = get_quantum_and_min_val(values)

        channel.values = values
        channel.offset = min_value
        channel.quantum = quantum

    return channel

def sequence_from_items(track_type, frames_data):
    sequence_data = Animation.SequenceDataListProperty.SequenceData()

    track_value_type = TrackTypeValueMap[track_type]

    if track_value_type == TrackValueType.Vector3:
        values_x = []
        values_y = []
        values_z = []

        for vector in frames_data:
            values_x.append(vector.x)
            values_y.append(vector.y)
            values_z.append(vector.z)

        uniq_x = list(set(values_x))
        len_uniq_x = len(uniq_x)

        uniq_y = list(set(values_y))
        len_uniq_y = len(uniq_y)

        uniq_z = list(set(values_z))
        len_uniq_z = len(uniq_z)

        if len_uniq_x == 1 and len_uniq_y == 1 and len_uniq_z == 1:
            channel = ChannelsListProperty.StaticVector3()
            channel.value = frames_data[0]

            sequence_data.channels.append(channel)
        else:
            sequence_data.channels.append(build_values_channel(values_x, uniq_x))
            sequence_data.channels.append(build_values_channel(values_y, uniq_y))
            sequence_data.channels.append(build_values_channel(values_z, uniq_z))
    if track_value_type == TrackValueType.Quaternion:
        values_x = []
        values_y = []
        values_z = []
        values_w = []

        for vector in frames_data:
            values_x.append(vector.x)
            values_y.append(vector.y)
            values_z.append(vector.z)
            values_w.append(vector.w)

        uniq_x = list(set(values_x))
        len_uniq_x = len(uniq_x)

        uniq_y = list(set(values_y))
        len_uniq_y = len(uniq_y)

        uniq_z = list(set(values_z))
        len_uniq_z = len(uniq_z)

        uniq_w = list(set(values_w))
        len_uniq_w = len(uniq_w)

        if len_uniq_x == 1 and len_uniq_y == 1 and len_uniq_z == 1 and len_uniq_w == 1:
            channel = ChannelsListProperty.StaticQuaternion()
            channel.value = frames_data[0]

            sequence_data.channels.append(channel)
        else:
            sequence_data.channels.append(build_values_channel(values_x, uniq_x))
            sequence_data.channels.append(build_values_channel(values_y, uniq_y))
            sequence_data.channels.append(build_values_channel(values_z, uniq_z))
            sequence_data.channels.append(build_values_channel(values_w, uniq_w))
    if track_value_type == TrackValueType.Float:
        values = frames_data

        uniq = list(set(values))
        len_uniq = len(uniq)

        if len_uniq == 1:
            channel = ChannelsListProperty.StaticFloat()
            channel.value = frames_data[0]

            sequence_data.channels.append(channel)
        else:
            sequence_data.channels.append(build_values_channel(values, uniq))

    return sequence_data

def animation_from_object(exportop, animation_obj):
    animation = Animation()

    animation_properties = animation_obj.animation_properties
    frame_count = animation_properties.frame_count

    animation.hash = animation_properties.hash
    animation.frame_count = frame_count
    animation.sequence_frame_limit = frame_count + 30
    animation.duration = (frame_count - 1) / bpy.context.scene.render.fps
    animation.unknown10 = AnimationFlag.Default

    # This value must be unique (Looks like its used internally for animation caching)
    animation.unknown1C = 'hash_' + hex(Generate(animation_properties.hash) + 1)[2:].zfill(8)

    sequence_items = {}

    if animation_properties.armature:
        armature_obj = get_armature_obj(animation_properties.armature)
        
        bones_map = build_tag_bone_map(armature_obj)

        if animation_properties.base_action:
            action = animation_properties.base_action
            action_type = ActionType.Base
            sequence_items_from_armature_action(
                action, sequence_items, bones_map, action_type, frame_count, True)

    bones_map = { 0: ''}
    if animation_properties.root_motion_location_action:
        action = animation_properties.root_motion_location_action
        action_type = ActionType.RootMotion

        animation.unknown10 |= AnimationFlag.RootMotion
        sequence_items_from_armature_action(
            action, sequence_items, bones_map, action_type, frame_count, False)

    if animation_properties.root_motion_rotation_action:
        action = animation_properties.root_motion_rotation_action
        action_type = ActionType.RootMotion

        # TODO: Figure out root motion rotation
        # animation.unknown10 |= AnimationFlag.RootMotion
        # sequence_items_from_action(
        #     action, sequence_items, bones_map, action_type, frames_count, False)

    if animation_properties.camera_action:
        action = animation_properties.camera_action
        action_type = ActionType.Camera

        sequence_items_from_armature_action(action, sequence_items, bones_map, action_type, frame_count, False)

    if animation_properties.camera_fov_action:
        action = animation_properties.camera_fov_action
        action_type = ActionType.CameraFov

        sequence_items_from_armature_action(action, sequence_items, bones_map, action_type, frame_count, False)

    sequence = Animation.SequenceListProperty.Sequence()
    sequence.frame_count = frame_count
    sequence.hash = 'hash_' + hex(0)[2:].zfill(8)

    for track, bones_data in sorted(sequence_items.items()):
        for bone_id, frames_data in sorted(bones_data.items()):
            sequence_data = sequence_from_items(track, frames_data)

            seq_bone_id = Animation.BoneIdListProperty.BoneId()
            seq_bone_id.bone_id = bone_id
            seq_bone_id.track = track.value
            seq_bone_id.unk0 = TrackTypeValueMap[track].value
            animation.bone_ids.append(seq_bone_id)

            sequence.sequence_data.append(sequence_data)

    animation.sequences.append(sequence)

    # Get int value from enum, a bit junky...
    animation.unknown10 = animation.unknown10.value

    return animation

def clip_from_object(exportop, clip_obj):
    clip_properties = clip_obj.clip_properties

    is_single_animation = len(clip_properties.animations) == 1

    if is_single_animation:
        clip = ClipsListProperty.ClipAnimation()
        clip_animation_property = clip_properties.animations[0]

        if clip_animation_property.animation is None:
            exportop.report({'ERROR'}, F"{clip_properties.name} doens't have all animation link's setup correctly.")
            return

        animation_properties = clip_animation_property.animation.animation_properties

        animation_duration = animation_properties.frame_count / bpy.context.scene.render.fps

        clip.animation_hash = animation_properties.hash
        clip.start_time = (clip_animation_property.start_frame / animation_properties.frame_count) * animation_duration
        clip.end_time = (clip_animation_property.end_frame / animation_properties.frame_count) * animation_duration

        clip_animation_duration = clip.end_time - clip.start_time
        clip.rate = clip_animation_duration / clip_properties.duration
    else:
        clip = ClipsListProperty.ClipAnimationList()
        clip.duration = clip_properties.duration

        for clip_animation_property in clip_properties.animations:
            clip_animation = ClipAnimationsListProperty.ClipAnimation()

            if clip_animation_property.animation is None:
                exportop.report({'ERROR'}, F"{clip_properties.name} doens't have all animation link's setup correctly.")
                return

            animation_properties = clip_animation_property.animation.animation_properties

            animation_duration = animation_properties.frame_count / bpy.context.scene.render.fps

            clip_animation.animation_hash = animation_properties.hash
            clip_animation.start_time = (clip_animation_property.start_frame / animation_properties.frame_count) * animation_duration
            clip_animation.end_time = (clip_animation_property.end_frame / animation_properties.frame_count) * animation_duration

            clip_animation_duration = clip_animation.end_time - clip_animation.start_time
            clip_animation.rate = clip_animation_duration / clip_properties.duration

            clip.animations.append(clip_animation)

    clip.hash = clip_properties.hash
    clip.name = clip_properties.name
    clip.unknown30 = 0

    return clip

  
def clip_dictionary_from_object(exportop, obj, exportpath, export_settings):
    clip_dictionary = ClipsDictionary()

    animations_obj = None
    clips_obj = None

    if len(obj.children) != 2:
        exportop.report({'ERROR'}, F"{obj.name} is not a valid clip dictionary.")
        return

    for child_obj in obj.children:
        if child_obj.sollum_type == SollumType.ANIMATIONS:
            animations_obj = child_obj
        elif child_obj.sollum_type == SollumType.CLIPS:
            clips_obj = child_obj

    if animations_obj is None or clips_obj is None:
        exportop.report({'ERROR'}, F"{obj.name} is not a valid clip dictionary.")
        return    

    for animation_obj in animations_obj.children:
        animation = animation_from_object(exportop, animation_obj)

        if animation is not None:
            clip_dictionary.animations.append(animation)

    for clip_obj in clips_obj.children:
        clip = clip_from_object(exportop, clip_obj)

        if clip is not None:
            clip_dictionary.clips.append(clip)

    return clip_dictionary

def export_ycd(exportop, obj, filepath, export_settings):
    cd = clip_dictionary_from_object(exportop, obj, filepath, export_settings)

    if cd is not None:
        cd.write_xml(filepath)
