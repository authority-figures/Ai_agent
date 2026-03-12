import numpy as np
from scipy.spatial.transform import Rotation as R


def wrap_to_pi(x):
    return (x + np.pi) % (2 * np.pi) - np.pi


def joint_distance(q1, q2, weights=None, revolute=True):
    """
    计算两组关节状态的距离
    revolute=True 时，对每个关节按角度周期处理
    """
    q1 = np.asarray(q1, dtype=float)
    q2 = np.asarray(q2, dtype=float)
    dq = q1 - q2

    if revolute:
        dq = np.array([wrap_to_pi(v) for v in dq], dtype=float)

    if weights is not None:
        dq = dq * np.asarray(weights, dtype=float)

    return float(np.linalg.norm(dq))


def is_duplicate_state(q, state_list, tol=1e-3, weights=None, revolute=True):
    for old_q in state_list:
        if joint_distance(q, old_q, weights=weights, revolute=revolute) < tol:
            return True
    return False


def sample_orientations_around_quat(
    ref_quat,
    roll_range_deg=20,
    pitch_range_deg=20,
    yaw_range_deg=30,
    roll_step_deg=10,
    pitch_step_deg=10,
    yaw_step_deg=10,
    include_identity=False
):
    """
    网格采样：在参考姿态附近按 rpy 规则扫描
    ref_quat: [x, y, z, w]
    return: list of quat [x, y, z, w]
    """
    ref_rot = R.from_quat(ref_quat)

    roll_vals = np.arange(-roll_range_deg, roll_range_deg + 1e-9, roll_step_deg)
    pitch_vals = np.arange(-pitch_range_deg, pitch_range_deg + 1e-9, pitch_step_deg)
    yaw_vals = np.arange(-yaw_range_deg, yaw_range_deg + 1e-9, yaw_step_deg)

    quats = []
    used = set()

    if include_identity:
        q0 = ref_rot.as_quat()
        if q0[3] < 0:
            q0 = -q0
        key = tuple(np.round(q0, 6))
        used.add(key)
        quats.append(q0)

    for dr in roll_vals:
        for dp in pitch_vals:
            for dy in yaw_vals:
                if (not include_identity and
                        abs(dr) < 1e-12 and abs(dp) < 1e-12 and abs(dy) < 1e-12):
                    continue

                delta_rot = R.from_euler("xyz", [dr, dp, dy], degrees=True)
                new_rot = ref_rot * delta_rot
                q = new_rot.as_quat()

                if q[3] < 0:
                    q = -q

                key = tuple(np.round(q, 6))
                if key not in used:
                    used.add(key)
                    quats.append(q)

    return quats


def sample_yaw_only_around_quat(
    ref_quat,
    yaw_range_deg=180,
    yaw_step_deg=15,
    local_axis="z",
    include_identity=False
):
    """
    网格采样：只绕局部某一轴旋转
    local_axis: 'x' / 'y' / 'z'
    """
    ref_rot = R.from_quat(ref_quat)
    yaw_vals = np.arange(-yaw_range_deg, yaw_range_deg + 1e-9, yaw_step_deg)

    quats = []
    used = set()

    axis_map = {"x": [1, 0, 0], "y": [0, 1, 0], "z": [0, 0, 1]}
    if local_axis not in axis_map:
        raise ValueError(f"local_axis must be one of x/y/z, got {local_axis}")

    axis = np.asarray(axis_map[local_axis], dtype=float)

    if include_identity:
        q0 = ref_rot.as_quat()
        if q0[3] < 0:
            q0 = -q0
        key = tuple(np.round(q0, 6))
        used.add(key)
        quats.append(q0)

    for ang in yaw_vals:
        if not include_identity and abs(ang) < 1e-12:
            continue

        delta_rot = R.from_rotvec(np.deg2rad(ang) * axis)
        new_rot = ref_rot * delta_rot
        q = new_rot.as_quat()

        if q[3] < 0:
            q = -q

        key = tuple(np.round(q, 6))
        if key not in used:
            used.add(key)
            quats.append(q)

    return quats


def sample_random_orientations_around_quat(
    ref_quat,
    num_samples,
    roll_range_deg=20,
    pitch_range_deg=20,
    yaw_range_deg=30,
    rng=None,
    include_identity=False
):
    """
    随机采样：在参考姿态附近随机采样 rpy 扰动
    """
    if rng is None:
        rng = np.random.default_rng()

    ref_rot = R.from_quat(ref_quat)
    quats = []
    used = set()

    target_count = num_samples + (1 if include_identity else 0)

    if include_identity:
        q0 = ref_rot.as_quat()
        if q0[3] < 0:
            q0 = -q0
        key = tuple(np.round(q0, 6))
        used.add(key)
        quats.append(q0)

    max_trials = max(num_samples * 10, 100)
    trials = 0

    while len(quats) < target_count and trials < max_trials:
        trials += 1

        dr = rng.uniform(-roll_range_deg, roll_range_deg)
        dp = rng.uniform(-pitch_range_deg, pitch_range_deg)
        dy = rng.uniform(-yaw_range_deg, yaw_range_deg)

        delta_rot = R.from_euler("xyz", [dr, dp, dy], degrees=True)
        new_rot = ref_rot * delta_rot
        q = new_rot.as_quat()

        if q[3] < 0:
            q = -q

        key = tuple(np.round(q, 6))
        if key not in used:
            used.add(key)
            quats.append(q)

    return quats


def sample_random_yaw_only_around_quat(
    ref_quat,
    num_samples,
    yaw_range_deg=180,
    local_axis="z",
    rng=None,
    include_identity=False
):
    """
    随机采样：只绕局部某一轴随机旋转
    """
    if rng is None:
        rng = np.random.default_rng()

    ref_rot = R.from_quat(ref_quat)
    quats = []
    used = set()

    axis_map = {"x": [1, 0, 0], "y": [0, 1, 0], "z": [0, 0, 1]}
    if local_axis not in axis_map:
        raise ValueError(f"local_axis must be one of x/y/z, got {local_axis}")

    axis = np.asarray(axis_map[local_axis], dtype=float)
    target_count = num_samples + (1 if include_identity else 0)

    if include_identity:
        q0 = ref_rot.as_quat()
        if q0[3] < 0:
            q0 = -q0
        key = tuple(np.round(q0, 6))
        used.add(key)
        quats.append(q0)

    max_trials = max(num_samples * 10, 100)
    trials = 0

    while len(quats) < target_count and trials < max_trials:
        trials += 1

        ang = rng.uniform(-yaw_range_deg, yaw_range_deg)

        delta_rot = R.from_rotvec(np.deg2rad(ang) * axis)
        new_rot = ref_rot * delta_rot
        q = new_rot.as_quat()

        if q[3] < 0:
            q = -q

        key = tuple(np.round(q, 6))
        if key not in used:
            used.add(key)
            quats.append(q)

    return quats




def expand_goal_states_nearby(
    goal_q,
    fk_fn,
    ik_fn,
    state_valid_fn,
    *,
    sampler="rpy",
    sample_mode="grid",
    num_orientation_samples=None,
    random_seed=None,
    pos_tol=1e-3,
    roll_range_deg=20,
    pitch_range_deg=20,
    yaw_range_deg=30,
    roll_step_deg=10,
    pitch_step_deg=10,
    yaw_step_deg=10,
    local_axis="z",
    max_joint_dev=1.0,
    max_samples=None,
    ik_seed_mode="goal",
    extra_seed=None,
    unique_tol=1e-3,
    joint_weights=None,
    revolute=True,
    include_goal=True,
    verbose=True
):
    """
    在给定标准 goal_q 附近扩充一批安全可行的 goal states。
    该函数独立于 OMPL，只依赖外部传入的 fk / ik / state_valid 三个函数。

    参数
    ----
    goal_q : array-like
        标准目标关节角

    fk_fn : callable
        fk_fn(q) -> (pos, quat)
        输入:
            q: 关节角数组
        返回:
            pos: shape=(3,)
            quat: shape=(4,), 四元数格式 [x, y, z, w]

    ik_fn : callable
        ik_fn(pos, quat, seed=None) -> q_sol or None
        输入:
            pos: shape=(3,)
            quat: shape=(4,), [x, y, z, w]
            seed: 逆解初值
        返回:
            q_sol: 关节角数组
            或 None 表示 IK 失败

    state_valid_fn : callable
        state_valid_fn(q) -> bool
        返回该状态是否安全/无碰撞/合法

    sampler : str
        "rpy"      : 在 roll/pitch/yaw 附近采样
        "yaw_only" : 只绕局部某一轴旋转采样

    sample_mode : str
        "grid"   : 规则扫描
        "random" : 随机采样

    num_orientation_samples : int or None
        当 sample_mode="random" 时必须提供

    random_seed : int or None
        随机种子

    pos_tol : float
        逆解后末端位置允许误差

    roll/pitch/yaw_range_deg : float
        姿态采样范围（度）

    roll/pitch/yaw_step_deg : float
        当 grid 模式下的姿态步长（度）

    local_axis : str
        yaw_only 模式下绕哪个局部轴旋转: "x"/"y"/"z"

    max_joint_dev : float
        候选解相对 goal_q 的最大关节距离

    max_samples : int or None
        最多返回多少个有效 goal（包含原始 goal，如果 include_goal=True）

    ik_seed_mode : str
        "goal"  : 以 goal_q 作为 IK 初值
        "extra" : 以 extra_seed 作为 IK 初值
        "none"  : 不提供 seed

    extra_seed : array-like or None
        当 ik_seed_mode="extra" 时生效

    unique_tol : float
        去重阈值，按关节距离判断

    joint_weights : array-like or None
        关节距离加权系数

    revolute : bool
        是否将关节差按角度周期处理

    include_goal : bool
        是否把输入的 goal_q 本身加入返回结果（前提是 state_valid_fn(goal_q) 为 True）

    verbose : bool
        是否打印统计信息

    返回
    ----
    valid_goals : list[np.ndarray]
        扩充后的有效 goal 状态列表

    stats : dict
        统计信息
    """
    goal_q = np.asarray(goal_q, dtype=float).copy()
    valid_goals = []

    stats = {
        "input_goal_valid": False,
        "num_orientation_samples": 0,
        "num_ik_success": 0,
        "num_rejected_joint_dev": 0,
        "num_rejected_invalid_state": 0,
        "num_rejected_pos_error": 0,
        "num_rejected_duplicate": 0,
        "num_added": 0,
    }

    goal_valid = bool(state_valid_fn(goal_q))
    stats["input_goal_valid"] = goal_valid

    if include_goal and goal_valid:
        valid_goals.append(goal_q.copy())
        stats["num_added"] += 1

    ref_pos, ref_quat = fk_fn(goal_q)
    ref_pos = np.asarray(ref_pos, dtype=float)
    ref_quat = np.asarray(ref_quat, dtype=float)

    rng = np.random.default_rng(random_seed)

    if sample_mode == "grid":
        if sampler == "rpy":
            cand_quats = sample_orientations_around_quat(
                ref_quat=ref_quat,
                roll_range_deg=roll_range_deg,
                pitch_range_deg=pitch_range_deg,
                yaw_range_deg=yaw_range_deg,
                roll_step_deg=roll_step_deg,
                pitch_step_deg=pitch_step_deg,
                yaw_step_deg=yaw_step_deg,
                include_identity=False
            )
        elif sampler == "yaw_only":
            cand_quats = sample_yaw_only_around_quat(
                ref_quat=ref_quat,
                yaw_range_deg=yaw_range_deg,
                yaw_step_deg=yaw_step_deg,
                local_axis=local_axis,
                include_identity=False
            )
        else:
            raise ValueError(f"Unsupported sampler: {sampler}")

    elif sample_mode == "random":
        if num_orientation_samples is None:
            raise ValueError("num_orientation_samples must be provided when sample_mode='random'")

        if sampler == "rpy":
            cand_quats = sample_random_orientations_around_quat(
                ref_quat=ref_quat,
                num_samples=num_orientation_samples,
                roll_range_deg=roll_range_deg,
                pitch_range_deg=pitch_range_deg,
                yaw_range_deg=yaw_range_deg,
                rng=rng,
                include_identity=False
            )
        elif sampler == "yaw_only":
            cand_quats = sample_random_yaw_only_around_quat(
                ref_quat=ref_quat,
                num_samples=num_orientation_samples,
                yaw_range_deg=yaw_range_deg,
                local_axis=local_axis,
                rng=rng,
                include_identity=False
            )
        else:
            raise ValueError(f"Unsupported sampler: {sampler}")

    else:
        raise ValueError(f"Unsupported sample_mode: {sample_mode}")

    stats["num_orientation_samples"] = len(cand_quats)

    if verbose:
        print(f"[expand_goal_states_nearby] orientation samples = {len(cand_quats)}")

    for quat in cand_quats:
        if max_samples is not None and len(valid_goals) >= max_samples:
            break

        if ik_seed_mode == "goal":
            seed = goal_q
        elif ik_seed_mode == "extra":
            seed = None if extra_seed is None else np.asarray(extra_seed, dtype=float)
        elif ik_seed_mode == "none":
            seed = None
        else:
            raise ValueError(f"Unsupported ik_seed_mode: {ik_seed_mode}")

        q_sol = ik_fn(ref_pos, quat, seed=seed)
        if q_sol is None:
            continue

        stats["num_ik_success"] += 1
        q_sol = np.asarray(q_sol, dtype=float)

        dist = joint_distance(
            q_sol,
            goal_q,
            weights=joint_weights,
            revolute=revolute
        )
        if dist > max_joint_dev:
            stats["num_rejected_joint_dev"] += 1
            continue

        if not state_valid_fn(q_sol):
            stats["num_rejected_invalid_state"] += 1
            continue

        pos_chk, _ = fk_fn(q_sol)
        pos_chk = np.asarray(pos_chk, dtype=float)
        pos_err = float(np.linalg.norm(pos_chk - ref_pos))
        if pos_err > pos_tol:
            stats["num_rejected_pos_error"] += 1
            continue

        if is_duplicate_state(
            q_sol,
            valid_goals,
            tol=unique_tol,
            weights=joint_weights,
            revolute=revolute
        ):
            stats["num_rejected_duplicate"] += 1
            continue

        valid_goals.append(q_sol.copy())
        stats["num_added"] += 1

    if verbose:
        print(f"[expand_goal_states_nearby] valid goals = {len(valid_goals)}")
        print(f"[expand_goal_states_nearby] stats = {stats}")

    return valid_goals, stats