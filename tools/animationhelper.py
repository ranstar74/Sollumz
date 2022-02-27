from sys import float_info
from mathutils import Quaternion, Vector, Euler
from enum import IntFlag, IntEnum

class AnimationFlag(IntFlag):
    Default = 0
    RootMotion = 16

class TrackType(IntEnum):
    """An enumeration of Animation Tracks supported by GTA."""
    BonePosition = 0
    BoneRotation = 1
    BoneScale = 2
    RootMotionPosition = 5
    RootMotionRotation = 6
    CameraPosition = 7
    CameraRotation = 8
    UV0 = 17
    UV1 = 18
    CameraFov = 27

    # TODO: Research remaning track types
    LightColor = -1
    LightRange = -1
    LightIntensity1 = -1
    LightIntensity2 = -1
    LightDirection = -1
    CameraDof = -1

class TrackValueType(IntEnum):
    Vector3 = 0
    Quaternion = 1
    Float = 2

class ActionType(IntEnum):
    Base = 0,
    RootMotion = 1,
    Camera = 2,
    CameraFov = 3

TrackTypeValueMap = {
    TrackType.BonePosition: TrackValueType.Vector3,
    TrackType.BoneRotation: TrackValueType.Quaternion,
    TrackType.BoneScale: TrackValueType.Vector3,
    TrackType.RootMotionPosition: TrackValueType.Vector3,
    TrackType.RootMotionRotation: TrackValueType.Quaternion,
    TrackType.CameraPosition: TrackValueType.Vector3,
    TrackType.CameraRotation: TrackValueType.Quaternion,
    TrackType.UV0: TrackValueType.Vector3,
    TrackType.UV1: TrackValueType.Vector3,
    TrackType.CameraFov: TrackValueType.Float
}

def evaluate_vector(fcurves, data_path, frames):
    xCurve = fcurves.find(data_path, index = 0)
    yCurve = fcurves.find(data_path, index = 1)
    zCurve = fcurves.find(data_path, index = 2)

    if xCurve is None:
        return []

    result = []
    for frame_id in range(0, frames):
        x = xCurve.evaluate(frame_id)
        y = yCurve.evaluate(frame_id)
        z = zCurve.evaluate(frame_id)

        result.append(Vector((x, y, z)))
    return result

def evaluate_euler_to_quaternion(fcurves, data_path, frames):
    xCurve = fcurves.find(data_path, index = 0)
    yCurve = fcurves.find(data_path, index = 1)
    zCurve = fcurves.find(data_path, index = 2)

    if xCurve is None:
        return []

    result = []
    for frame_id in range(0, frames):
        x = xCurve.evaluate(frame_id)
        y = yCurve.evaluate(frame_id)
        z = zCurve.evaluate(frame_id)

        result.append(Euler((x, y, z)).to_quaternion())
    return result

def evaluate_quaternion(fcurves, data_path, frames):
    wCurve = fcurves.find(data_path, index = 0)
    xCurve = fcurves.find(data_path, index = 1)
    yCurve = fcurves.find(data_path, index = 2)
    zCurve = fcurves.find(data_path, index = 3)

    if xCurve is None:
        return []

    result = []
    for frame_id in range(0, frames):
        w = wCurve.evaluate(frame_id)
        x = xCurve.evaluate(frame_id)
        y = yCurve.evaluate(frame_id)
        z = zCurve.evaluate(frame_id)

        result.append(Quaternion((w, x, y, z)))
    return result

def evaluate_float(fcurves, data_path, frames):
    curve = fcurves.find(data_path, index = 0)

    if curve is None:
        return []
    
    result = []
    for frame_id in range(0, frames):
        result.append(curve.evaluate(frame_id))
    return result

def get_quantum_and_min_val(nums):
    min_val = float_info.max
    max_val = float_info.min
    min_delta = float_info.max
    last_val = 0

    for value in nums:
        min_val = min(min_val, value)
        max_val = max(max_val, value)

        if value != last_val:
            min_delta = min(min_delta, abs(value - last_val))

        last_val = value

    if min_delta == float_info.max:
        min_delta = 0

    range_value = max_val - min_val
    min_quant = range_value / 1048576
    quantum = max(min_delta, min_quant)

    return min_val, quantum

def fix_quaternion_lerp(quaternion, previous_quaternion):
    """Aligns quaternion direction with previous one."""
    # 'Flickering bug' fix - killso:
    # This bug is caused by interpolation algorithm used in GTA
    # which is not slerp, but straight interpolation of every value
    # and this leads to incorrect results in cases if dot(this, next) < 0
    # This is correct 'Quaternion Lerp' algorithm:
    # if (Dot(start, end) >= 0f)
    # {
    #   result.X = (1 - amount) * start.X + amount * end.X
    #   ...
    # }
    # else
    # {
    #   result.X = (1 - amount) * start.X - amount * end.X
    #   ...
    # }
    # (Statement difference is only substracting instead of adding)
    # But GTA algorithm doesn't have Dot check,
    # resulting all values that are not passing this statement to 'lag' in game.
    # (because of incorrect interpolation direction)
    # So what we do is make all values to pass Dot(start, end) >= 0f statement
    if Quaternion.dot(previous_quaternion, quaternion) < 0:
        quaternion *= -1
