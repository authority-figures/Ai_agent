import numpy as np
import pybullet as p


# =========================
# 反射工具
# =========================
def _get_attr_first(obj, names, default=None):
    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)
    return default


def _call_method_first(obj, names, *args, **kwargs):
    for name in names:
        if hasattr(obj, name):
            fn = getattr(obj, name)
            if callable(fn):
                return fn(*args, **kwargs)
    raise AttributeError(f"None of methods found: {names}")


# =========================
# 从 robot 实例提取信息
# =========================
def get_robot_body_id(robot):
    body_id = _get_attr_first(robot, ["body_id", "robot_id", "id_robot", "id"], None)
    if body_id is None:
        raise AttributeError("robot 中未找到 body_id / robot_id / uid / id")
    return int(body_id)


def get_robot_urdf_path(robot):
    return _get_attr_first(robot, ["urdf_path", "urdf_file", "urdf"], None)


def get_robot_base_pose(robot, physicsClientId=0):
    for name in ["get_base_pose", "getBasePose", "base_pose"]:
        if hasattr(robot, name) and callable(getattr(robot, name)):
            return getattr(robot, name)()

    body_id = get_robot_body_id(robot)
    return p.getBasePositionAndOrientation(body_id, physicsClientId=physicsClientId)


def get_robot_joint_indices(robot, physicsClientId=0):
    for name in [
        "get_movable_joint_indices",
        "get_active_joint_indices",
        "get_controllable_joint_indices",
        "get_joint_indices",
    ]:
        if hasattr(robot, name) and callable(getattr(robot, name)):
            return list(getattr(robot, name)())

    body_id = get_robot_body_id(robot)
    joint_indices = []
    for j in range(p.getNumJoints(body_id, physicsClientId=physicsClientId)):
        info = p.getJointInfo(body_id, j, physicsClientId=physicsClientId)
        joint_type = info[2]
        if joint_type in (p.JOINT_REVOLUTE, p.JOINT_PRISMATIC):
            joint_indices.append(j)
    return joint_indices


def get_robot_use_fixed_base(robot, default=True):
    value = _get_attr_first(robot, ["use_fixed_base", "fixed_base"], None)
    return default if value is None else bool(value)


def get_robot_global_scaling(robot, default=1.0):
    value = _get_attr_first(robot, ["global_scaling", "scaling", "scale"], None)
    return default if value is None else float(value)


# =========================
# PyBullet 基础操作
# =========================
def set_robot_configuration(body_id, q, joint_indices, physicsClientId=0):
    q = np.asarray(q, dtype=float)
    if len(q) != len(joint_indices):
        raise ValueError(
            f"len(q)={len(q)} 与 len(joint_indices)={len(joint_indices)} 不一致"
        )

    for joint_id, val in zip(joint_indices, q):
        p.resetJointState(
            bodyUniqueId=body_id,
            jointIndex=int(joint_id),
            targetValue=float(val),
            physicsClientId=physicsClientId
        )


def set_body_transparency(body_id, rgba, physicsClientId=0):
    num_joints = p.getNumJoints(body_id, physicsClientId=physicsClientId)

    try:
        p.changeVisualShape(
            body_id, -1, rgbaColor=rgba, physicsClientId=physicsClientId
        )
    except Exception:
        pass

    for link_idx in range(num_joints):
        try:
            p.changeVisualShape(
                body_id, link_idx, rgbaColor=rgba, physicsClientId=physicsClientId
            )
        except Exception:
            pass


def disable_body_collision(body_id, physicsClientId=0):
    num_joints = p.getNumJoints(body_id, physicsClientId=physicsClientId)

    for a in range(-1, num_joints):
        for b in range(-1, num_joints):
            try:
                p.setCollisionFilterPair(
                    body_id, body_id, a, b, enableCollision=0,
                    physicsClientId=physicsClientId
                )
            except Exception:
                pass

    for link_idx in range(-1, num_joints):
        try:
            p.setCollisionFilterGroupMask(
                body_id,
                link_idx,
                collisionFilterGroup=0,
                collisionFilterMask=0,
                physicsClientId=physicsClientId
            )
        except Exception:
            pass


import numpy as np


def sample_trajectory_indices(
    num_states,
    max_snapshots=12,
    sample_mode="uniform",
    snapshot_progresses=None
):
    """
    根据轨迹长度生成要显示鬼影的索引

    参数
    ----
    num_states : int
        轨迹状态总数

    max_snapshots : int
        uniform 模式下最多采样多少个快照

    sample_mode : str
        "uniform"  : 均匀采样
        "all"      : 全部采样
        "progress" : 按给定归一化进度采样

    snapshot_progresses : list[float] or None
        当 sample_mode="progress" 时使用
        例如 [0, 0.5, 0.7, 0.8, 0.9, 1.0]

    返回
    ----
    indices : list[int]
    """
    if num_states <= 0:
        return []

    if sample_mode == "all":
        return list(range(num_states))

    if sample_mode == "uniform":
        k = min(max_snapshots, num_states)
        idx = np.linspace(0, num_states - 1, k).round().astype(int).tolist()
        return sorted(set(idx))

    if sample_mode == "progress":
        if snapshot_progresses is None:
            raise ValueError("sample_mode='progress' 时必须提供 snapshot_progresses")

        progresses = np.asarray(snapshot_progresses, dtype=float)

        if progresses.ndim != 1:
            raise ValueError("snapshot_progresses 必须是一维数组或列表")

        if np.any(progresses < 0.0) or np.any(progresses > 1.0):
            raise ValueError("snapshot_progresses 中所有值都必须位于 [0,1]")

        idx = (progresses * (num_states - 1)).round().astype(int).tolist()
        return sorted(set(idx))

    raise ValueError(f"Unsupported sample_mode: {sample_mode}")


# =========================
# 在当前环境中生成“副本”
# =========================
def default_spawn_clone(robot, physicsClientId=0, load_flags=0):
    """
    默认克隆方法：
    通过 robot.urdf_path 在当前已存在的 PyBullet 环境中加载一个同款机器人副本
    """
    urdf_path = get_robot_urdf_path(robot)
    if urdf_path is None:
        raise ValueError(
            "robot 中没有 urdf_path/urdf_file/urdf，无法默认生成鬼影副本。"
            "请给 create_robot_ghost_trajectory 传入 spawn_clone_fn。"
        )

    base_pos, base_orn = get_robot_base_pose(robot, physicsClientId=physicsClientId)
    use_fixed_base = get_robot_use_fixed_base(robot, default=True)
    global_scaling = get_robot_global_scaling(robot, default=1.0)

    ghost_id = p.loadURDF(
        fileName=urdf_path,
        basePosition=base_pos,
        baseOrientation=base_orn,
        useFixedBase=use_fixed_base,
        globalScaling=global_scaling,
        flags=load_flags,
        physicsClientId=physicsClientId
    )
    return ghost_id


# =========================
# 对外主函数
# =========================
def create_robot_ghost_snapshot(
    robot,
    q,
    *,
    rgba=(0.2, 0.6, 1.0, 0.25),
    spawn_clone_fn=None,
    disable_collision_for_ghost=True,
    physicsClientId=0,
    load_flags=0
):
    """
    在当前已存在环境中，为 robot 创建一个鬼影快照

    参数
    ----
    robot : object
        你外部已有的机器人实例

    q : array-like
        该鬼影对应的关节状态

    rgba : tuple
        鬼影颜色和透明度

    spawn_clone_fn : callable or None
        用于在当前环境中生成“同款机器人副本”
        签名建议：
            spawn_clone_fn(robot, physicsClientId=0, load_flags=0) -> ghost_body_id
        若为 None，则默认尝试用 robot.urdf_path 进行 loadURDF

    返回
    ----
    ghost_id : int
    """
    joint_indices = get_robot_joint_indices(robot, physicsClientId=physicsClientId)

    if spawn_clone_fn is None:
        ghost_id = default_spawn_clone(
            robot,
            physicsClientId=physicsClientId,
            load_flags=load_flags
        )
    else:
        ghost_id = spawn_clone_fn(
            robot,
            physicsClientId=physicsClientId,
            load_flags=load_flags
        )

    if disable_collision_for_ghost:
        disable_body_collision(ghost_id, physicsClientId=physicsClientId)

    set_robot_configuration(
        ghost_id,
        q,
        joint_indices=joint_indices,
        physicsClientId=physicsClientId
    )
    set_body_transparency(ghost_id, rgba=rgba, physicsClientId=physicsClientId)

    return ghost_id


def get_stage_rgba(t, stage_colors):
    """
    根据归一化进度 t∈[0,1] 返回对应阶段颜色

    stage_colors: list of (end_t, rgba)
        例如：
        [
            (0.3, (0.2, 0.4, 1.0, 0.08)),
            (0.7, (1.0, 0.8, 0.1, 0.18)),
            (1.0, (1.0, 0.2, 0.2, 0.35)),
        ]
    """
    if t <= 0:
        return tuple(stage_colors[0][1])
    if t >= 1:
        return tuple(stage_colors[-1][1])

    prev_t, prev_rgba = 0.0, np.asarray(stage_colors[0][1], dtype=float)

    for end_t, rgba in stage_colors:
        rgba = np.asarray(rgba, dtype=float)
        if t <= end_t:
            if end_t <= prev_t + 1e-12:
                return tuple(rgba)
            alpha = (t - prev_t) / (end_t - prev_t)
            out = (1 - alpha) * prev_rgba + alpha * rgba
            return tuple(out)
        prev_t = end_t
        prev_rgba = rgba

    return tuple(stage_colors[-1][1])


def create_robot_ghost_trajectory(
    robot,
    trajectory,
    *,
    max_snapshots=12,
    sample_mode="uniform",
    snapshot_progresses=None,
    rgba_start=(0.2, 0.6, 1.0, 0.08),
    rgba_end=(0.2, 0.6, 1.0, 0.35),
    stage_colors=None,
    snapshot_rgba_list=None,
    spawn_clone_fn=None,
    disable_collision_for_ghost=True,
    draw_ee_points=False,
    ee_link_index=None,
    ee_point_radius=0.008,
    physicsClientId=0,
    load_flags=0,
    draw_dense_ee_points=False,
    ee_point_rgba=(1.0, 0.0, 0.0, 1.0),
):
    traj = np.asarray(trajectory, dtype=float)
    if traj.ndim != 2:
        raise ValueError(f"trajectory 应为 shape=(N, dof)，实际为 {traj.shape}")

    used_indices = sample_trajectory_indices(
        num_states=len(traj),
        max_snapshots=max_snapshots,
        sample_mode=sample_mode,
        snapshot_progresses=snapshot_progresses
    )

    rgba_start_arr = np.asarray(rgba_start, dtype=float)
    rgba_end_arr = np.asarray(rgba_end, dtype=float)

    ghost_ids = []
    ee_marker_ids = []
    m = len(used_indices)

    for i, idx in enumerate(used_indices):
        t = 0.0 if m == 1 else i / (m - 1)

        if snapshot_rgba_list is not None:
            if len(snapshot_rgba_list) != len(used_indices):
                raise ValueError("snapshot_rgba_list 长度必须等于实际快照数量")
            rgba = tuple(snapshot_rgba_list[i])
        elif stage_colors is not None:
            rgba = get_stage_rgba(t, stage_colors)
        else:
            rgba = tuple((1 - t) * rgba_start_arr + t * rgba_end_arr)

        ghost_id = create_robot_ghost_snapshot(
            robot=robot,
            q=traj[idx],
            rgba=rgba,
            spawn_clone_fn=spawn_clone_fn,
            disable_collision_for_ghost=disable_collision_for_ghost,
            physicsClientId=physicsClientId,
            load_flags=load_flags
        )
        ghost_ids.append(ghost_id)



        if draw_ee_points:
            if ee_link_index is None:
                raise ValueError("draw_ee_points=True 时必须提供 ee_link_index")

            ls = p.getLinkState(
                ghost_id,
                ee_link_index,
                computeForwardKinematics=True,
                physicsClientId=physicsClientId
            )
            ee_pos = ls[4]  # worldLinkFramePosition

            marker_id = create_ee_point_marker(
                ee_pos,
                radius=ee_point_radius,
                rgba=rgba,
                physicsClientId=physicsClientId
            )
            ee_marker_ids.append(marker_id)

    ee_marker_ids = []
    if draw_dense_ee_points:
        if ee_link_index is None:
            raise ValueError("draw_dense_ee_points=True 时必须提供 ee_link_index")

        ee_marker_ids = create_dense_ee_trajectory_points(
            robot=robot,
            trajectory=traj,
            ee_link_index=ee_link_index,
            point_radius=ee_point_radius,
            point_rgba=ee_point_rgba,
            physicsClientId=physicsClientId
        )

    return ghost_ids, used_indices, ee_marker_ids

def create_dense_ee_trajectory_points(
    robot,
    trajectory,
    *,
    ee_link_index,
    point_radius=0.004,
    point_rgba=(1.0, 0.0, 0.0, 1.0),
    physicsClientId=0
):
    """
    沿整条轨迹的每个状态绘制末端轨迹点
    点为不透明，且和轨迹一样密集

    参数
    ----
    robot : object
        你的机器人实例
    trajectory : array-like, shape=(N, dof)
        关节轨迹
    ee_link_index : int
        末端 link index
    point_radius : float
        点半径
    point_rgba : tuple
        点颜色，默认不透明
    """
    traj = np.asarray(trajectory, dtype=float)
    if traj.ndim != 2:
        raise ValueError(f"trajectory 应为 shape=(N, dof)，实际为 {traj.shape}")

    body_id = get_robot_body_id(robot)
    joint_indices = get_robot_joint_indices(robot, physicsClientId=physicsClientId)

    if traj.shape[1] != len(joint_indices):
        raise ValueError(
            f"trajectory 维数与机器人关节数不匹配: "
            f"traj.shape[1]={traj.shape[1]}, len(joint_indices)={len(joint_indices)}"
        )

    # 保存当前关节状态，避免画完以后把机器人停在轨迹终点
    cur_q = [
        p.getJointState(body_id, j, physicsClientId=physicsClientId)[0]
        for j in joint_indices
    ]

    marker_ids = []

    try:
        for q in traj:
            set_robot_configuration(
                body_id,
                q,
                joint_indices=joint_indices,
                physicsClientId=physicsClientId
            )

            ls = p.getLinkState(
                body_id,
                ee_link_index,
                computeForwardKinematics=True,
                physicsClientId=physicsClientId
            )
            ee_pos = ls[4]  # worldLinkFramePosition

            marker_id = create_ee_point_marker(
                ee_pos,
                radius=point_radius,
                rgba=point_rgba,
                physicsClientId=physicsClientId
            )
            marker_ids.append(marker_id)

    finally:
        # 恢复机器人原始状态
        set_robot_configuration(
            body_id,
            cur_q,
            joint_indices=joint_indices,
            physicsClientId=physicsClientId
        )

    return marker_ids

def create_ee_point_marker(
    position,
    *,
    radius=0.004,
    rgba=(1.0, 0.0, 0.0, 1.0),
    physicsClientId=0
):
    """
    在给定位置创建一个纯可视化小球
    默认不透明
    """
    visual_shape = p.createVisualShape(
        shapeType=p.GEOM_SPHERE,
        radius=radius,
        rgbaColor=rgba,
        physicsClientId=physicsClientId
    )

    marker_id = p.createMultiBody(
        baseMass=0,
        baseCollisionShapeIndex=-1,
        baseVisualShapeIndex=visual_shape,
        basePosition=position,
        baseOrientation=[0, 0, 0, 1],
        physicsClientId=physicsClientId
    )
    return marker_id


def remove_ee_point_markers(marker_ids, physicsClientId=0):
    for mid in marker_ids:
        try:
            p.removeBody(mid, physicsClientId=physicsClientId)
        except Exception:
            pass



def remove_robot_ghosts_and_markers(
    ghost_ids,
    ee_marker_ids=None,
    physicsClientId=0
):
    if ee_marker_ids is not None:
        remove_ee_point_markers(ee_marker_ids, physicsClientId=physicsClientId)

    for gid in ghost_ids:
        try:
            p.removeBody(gid, physicsClientId=physicsClientId)
        except Exception:
            pass


# =========================================================



def create_ee_point_marker(
    position,
    *,
    radius=0.004,
    rgba=(1.0, 0.0, 0.0, 1.0),
    physicsClientId=0
):
    visual_shape = p.createVisualShape(
        shapeType=p.GEOM_SPHERE,
        radius=radius,
        rgbaColor=rgba,
        physicsClientId=physicsClientId
    )

    marker_id = p.createMultiBody(
        baseMass=0,
        baseCollisionShapeIndex=-1,
        baseVisualShapeIndex=visual_shape,
        basePosition=position,
        baseOrientation=[0, 0, 0, 1],
        physicsClientId=physicsClientId
    )
    return marker_id


def sample_path_point_indices(
    num_states,
    *,
    point_stride=1,
    point_progresses=None
):
    """
    路径点采样索引

    point_stride:
        每隔多少个轨迹状态取一个点，1表示全部

    point_progresses:
        若提供，则按归一化路径进度取点，例如 [0, 0.5, 0.8, 1.0]
        优先级高于 point_stride
    """
    if num_states <= 0:
        return []

    if point_progresses is not None:
        progresses = np.asarray(point_progresses, dtype=float)
        if progresses.ndim != 1:
            raise ValueError("point_progresses 必须是一维数组")
        if np.any(progresses < 0.0) or np.any(progresses > 1.0):
            raise ValueError("point_progresses 必须在 [0,1] 内")
        idx = (progresses * (num_states - 1)).round().astype(int).tolist()
        return unique_keep_order(idx)

    point_stride = int(point_stride)
    if point_stride <= 0:
        raise ValueError("point_stride 必须为正整数")

    return list(range(0, num_states, point_stride))


def unique_keep_order(seq):
    seen = set()
    out = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def create_ee_path_points(
    robot,
    trajectory,
    *,
    ee_link_index,
    point_stride=1,
    point_progresses=None,
    point_radius=0.004,
    point_rgba=(1.0, 0.0, 0.0, 1.0),
    physicsClientId=0
):
    """
    单独绘制末端路径点

    参数
    ----
    point_stride:
        控制稠密程度，1=全部绘制，2=隔一个绘制，5=每5个绘制一个

    point_progresses:
        自定义归一化进度采样，优先级高于 point_stride
    """
    traj = np.asarray(trajectory, dtype=float)
    if traj.ndim != 2:
        raise ValueError(f"trajectory 应为 shape=(N, dof)，实际为 {traj.shape}")

    body_id = get_robot_body_id(robot)
    joint_indices = get_robot_joint_indices(robot, physicsClientId=physicsClientId)

    if traj.shape[1] != len(joint_indices):
        raise ValueError(
            f"trajectory 维数与机器人关节数不匹配: "
            f"traj.shape[1]={traj.shape[1]}, len(joint_indices)={len(joint_indices)}"
        )

    used_indices = sample_path_point_indices(
        num_states=len(traj),
        point_stride=point_stride,
        point_progresses=point_progresses
    )

    cur_q = [
        p.getJointState(body_id, j, physicsClientId=physicsClientId)[0]
        for j in joint_indices
    ]

    marker_ids = []

    try:
        for idx in used_indices:
            q = traj[idx]

            set_robot_configuration(
                body_id,
                q,
                joint_indices=joint_indices,
                physicsClientId=physicsClientId
            )

            ls = p.getLinkState(
                body_id,
                ee_link_index,
                computeForwardKinematics=True,
                physicsClientId=physicsClientId
            )
            ee_pos = ls[4]

            marker_id = create_ee_point_marker(
                ee_pos,
                radius=point_radius,
                rgba=point_rgba,
                physicsClientId=physicsClientId
            )
            marker_ids.append(marker_id)

    finally:
        set_robot_configuration(
            body_id,
            cur_q,
            joint_indices=joint_indices,
            physicsClientId=physicsClientId
        )

    return marker_ids, used_indices




