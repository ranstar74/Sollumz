import bpy

from ..tools.animationhelper import create_animation, create_clip
from ..sollumz_helper import SOLLUMZ_OT_base
from ..sollumz_properties import SollumType
from ..tools.blenderhelper import get_armature_obj
from .ycdimport import create_clip_dictionary

class SOLLUMZ_OT_clip_apply_nla(SOLLUMZ_OT_base, bpy.types.Operator):
    bl_idname = "sollumz.anim_apply_nla"
    bl_label = "Apply NLA"
    bl_description = "Applies clip as a Nonlinear Animation for a quick preview"

    def run(self, context):
        if len(bpy.context.selected_objects) <= 0:
            return {'FINISHED'}

        active_object = bpy.context.selected_objects[0]

        if active_object.sollum_type != SollumType.CLIP:
            return {'FINISHED'}

        clip_dictionary = active_object.parent.parent
        armature = get_armature_obj(clip_dictionary.clip_dict_properties.armature)

        if armature is None:
            return {'FINISHED'}

        clip_properties = active_object.clip_properties

        groups = {}

        for clip_animation in clip_properties.animations:
            if clip_animation.animation == None:
                continue

            animation_properties = clip_animation.animation.animation_properties

            start_frames = clip_animation.start_frame
            end_frames = clip_animation.end_frame

            visual_frame_count = round(clip_properties.duration * bpy.context.scene.render.fps)

            actions = []

            if animation_properties.base_action != None:
                actions.append(animation_properties.base_action)

            if animation_properties.root_motion_location_action != None:
                actions.append(animation_properties.root_motion_location_action)

            # if animation_properties.root_motion_rotation_action != None:
            #     actions.append(animation_properties.root_motion_rotation_action)

            for action in actions:
                if action.name not in groups:
                    groups[action.name] = []

                group = groups[action.name]

                group.append({
                    'name': clip_properties.hash,
                    'start_frames': start_frames,
                    'end_frames': end_frames,
                    'visual_frame_count': visual_frame_count,
                    'action': action,
                })

        if armature.animation_data is None:
            armature.animation_data_create()

        for nla_track in armature.animation_data.nla_tracks:
            armature.animation_data.nla_tracks.remove(nla_track)

        for group_name, clips in groups.items():
            track = armature.animation_data.nla_tracks.new()
            track.name = group_name

            for clip in clips:
                virtual_frames_count = clip['visual_frame_count']
                action_frames_count = clip['end_frames'] - clip['start_frames']

                nla_strip = track.strips.new(clip['name'], 0, clip['action'])
                nla_strip.frame_start = 0
                nla_strip.frame_end = virtual_frames_count

                bpy.context.scene.frame_start = 0
                bpy.context.scene.frame_end = nla_strip.frame_end

                if '_root_motion_location' in group_name:
                    nla_strip.blend_type = "ADD"
                elif '_root_motion_rotation' in group_name:
                    nla_strip.blend_type = "MULTIPLY"
                elif '_base' in group_name:
                    nla_strip.blend_type = "COMBINE"

                nla_strip.extrapolation = "NOTHING"
                nla_strip.name = clip['name']

                nla_strip.scale = virtual_frames_count / action_frames_count
                nla_strip.action_frame_start = clip['start_frames']
                nla_strip.action_frame_end = clip['end_frames']

        return {'FINISHED'}


class SOLLUMZ_OT_clip_new_animation(SOLLUMZ_OT_base, bpy.types.Operator):
    bl_idname = "sollumz.anim_new_animation"
    bl_label = "Add a new animation"
    bl_description = "Adds a new animation entry to the clip dictionary"

    def run(self, context):
        if len(bpy.context.selected_objects) <= 0:
            return {'FINISHED'}

        active_object = bpy.context.selected_objects[0]

        if active_object.sollum_type != SollumType.CLIP:
            return {'FINISHED'}

        clip_properties = active_object.clip_properties

        clip_properties.animations.add()

        return {'FINISHED'}


class SOLLUMZ_OT_clip_delete_animation(SOLLUMZ_OT_base, bpy.types.Operator):
    bl_idname='sollumz.anim_delete_animation'
    bl_label='Delete animation'

    animation_index : bpy.props.IntProperty(name="animation_index")

    def run(self, context):
        if len(bpy.context.selected_objects) <= 0:
            return {'FINISHED'}

        active_object = bpy.context.selected_objects[0]

        if active_object.sollum_type != SollumType.CLIP:
            return {'FINISHED'}

        clip_properties = active_object.clip_properties

        clip_properties.animations.remove(self.animation_index)

        return {'FINISHED'}


class SOLLUMZ_OT_create_clip_dictionary(SOLLUMZ_OT_base, bpy.types.Operator):
    bl_idname = "sollumz.crate_clip_dictionary"
    bl_label = "Create a Clip Dictionary"
    bl_description = "Creates a new Clip Dictionary"

    def run(self, context):
        create_clip_dictionary('Clip Dictionary')

        return {'FINISHED'}


class SOLLUMZ_OT_autogen_clip_from_action(SOLLUMZ_OT_base, bpy.types.Operator):
    bl_idname = "sollumz.autogen_clip_from_action"
    bl_label = "Create From Action"
    bl_description = "Creates a new Clip from action"

    def run(self, context):
        if len(bpy.context.selected_objects) <= 0:
            return {'FINISHED'}
        
        name = context.scene.autogen_name

        if name is '':
            self.report({'ERROR'}, 'Clip name can\'t be empy.')
            return {'FINISHED'}

        animation_obj = create_animation()
        clip_obj = create_clip()

        if animation_obj is None:
            return {'FINISHED'}

        animation_properties = animation_obj.animation_properties
        clip_properties = clip_obj.clip_properties

        armature = bpy.data.armatures[context.scene.autogen_selected_armature]
        armature_obj = get_armature_obj(armature)
        base_action = armature_obj.animation_data.action
        
        animation_properties.base_action = base_action
        animation_properties.frame_count = base_action.frame_range.y - base_action.frame_range.x + 1
        animation_properties.hash = name + '_anim'
        animation_properties.armature = armature

        clip_properties.hash = name
        clip_properties.name = 'pack:/' + name + '.clip'
        clip_properties.duration = animation_properties.frame_count / 24
        
        anim_link = clip_properties.animations.add()
        anim_link.animation = animation_obj
        anim_link.start_frame = base_action.frame_range.x
        anim_link.end_frame = base_action.frame_range.y

        context.scene.autogen_name = ''

        animation_obj.name = name + '_anim'
        clip_obj.name = name

        return {'FINISHED'}


class SOLLUMZ_OT_separate_root_motion(SOLLUMZ_OT_base, bpy.types.Operator):
    bl_idname = "sollumz.separate_root_motion"
    bl_label = "Separate Root Motion"
    bl_description = "Separates root motion tracks from base track"

    def run(self, context):
        if len(bpy.context.selected_objects) <= 0:
            return {'FINISHED'}


class SOLLUMZ_OT_create_clip(SOLLUMZ_OT_base, bpy.types.Operator):
    bl_idname = "sollumz.crate_clip"
    bl_label = "Create a new Clip"
    bl_description = "Create an empty Clip in selected Clip Dictionary"

    def run(self, context):
        if len(bpy.context.selected_objects) <= 0:
            return {'FINISHED'}

        create_clip()

        return {'FINISHED'}


class SOLLUMZ_OT_create_animation(SOLLUMZ_OT_base, bpy.types.Operator):
    bl_idname = "sollumz.crate_animation"
    bl_label = "Create a new Animation"
    bl_description = "Create an empty Animation in selected Clip Dictionary"

    def run(self, context):
        if len(bpy.context.selected_objects) <= 0:
            return {'FINISHED'}

        create_animation()

        return {'FINISHED'}


class SOLLUMZ_OT_animation_fill(SOLLUMZ_OT_base, bpy.types.Operator):
    bl_idname = "sollumz.animation_fill"
    bl_label = "Fill animation data"

    def run(self, context):
        if len(bpy.context.selected_objects) <= 0:
            return {'FINISHED'}

        return {'FINISHED'}
