import numpy as np
import random
from scipy.spatial.transform import Rotation as R

from ompl import base as ob
from ompl import geometric as og
from agent_project.simulation.Robot import Robot
from agent_project.simulation.pb_ompl import PbOMPLRobot

# -------- 基础空间 --------
class PbStateSpace(ob.RealVectorStateSpace):
    def __init__(self, num_dim) -> None:
        super().__init__(num_dim)
        self.num_dim = num_dim

    def allocStateSampler(self):
        print("[TRACE] Fallback: allocStateSampler 被调用！")
        return super().allocDefaultStateSampler()



# -------- 混合采样器 --------
class MixedValidStateSampler(ob.ValidStateSampler):
    def __init__(self, si, guided_sample_fn, ratio=0.5):
        super().__init__(si)
        self.name_ = "MixedValidStateSampler"
        self.guided_sample_fn = guided_sample_fn
        self.ratio = ratio
        self.default_sampler = si.allocStateSampler()

    def sample(self, state):
        if random.random() < self.ratio:
            print("[TRACE] Guided sample 被调用！")
            sample = self.guided_sample_fn()
            if sample:
                for i in range(len(sample)):
                    state[i] = sample[i]
                return True
        print("[TRACE] Default sample 被调用！")
        return self.default_sampler.sample(state)

    def sampleNear(self, state, near, distance):
        return self.default_sampler.sampleNear(state, near, distance)


# -------- 主类 --------
class TaskSpaceRRT:
    def __init__(self, robot):
        self.robot = robot
        self.space = PbStateSpace(robot.num_avail_joints)

        bounds = ob.RealVectorBounds(robot.num_avail_joints)
        for i, (low, high) in enumerate(robot.get_joint_bounds()):
            bounds.setLow(i, low)
            bounds.setHigh(i, high)
        self.space.setBounds(bounds)

        self.ss = og.SimpleSetup(self.space)
        self.si = self.ss.getSpaceInformation()
        self.ss.setStateValidityChecker(ob.StateValidityCheckerFn(self.is_state_valid))

        self.T_goal = None

    def is_state_valid(self, state):
        return True  # 允许所有采样点通过，便于验证采样器行为

    def get_T_goal(self, joints):
        pos, ori = self.robot.get_pos_ori_from_ik(joints)
        T = np.eye(4)
        T[:3, 3] = pos
        T[:3, :3] = R.from_quat(ori).as_matrix()
        self.T_goal = T.copy()

    def sample_in_task_space(self):
        if self.T_goal is None:
            return None
        offset = np.array([0, 0, -np.random.uniform(0.01, 0.05)])
        sampled_pos = self.T_goal[:3, 3] + self.T_goal[:3, :3] @ offset
        sampled_quat = R.from_euler('xyz', [0, 0, random.uniform(-np.pi / 12, np.pi / 12)]).as_quat()
        return self.robot.get_state_from_ik(sampled_pos, sampled_quat)

    def prepare_sampler(self):
        def allocator(si):
            return MixedValidStateSampler(si, self.sample_in_task_space, ratio=0.8)
        self.si.setValidStateSamplerAllocator(ob.ValidStateSamplerAllocator(allocator))

    def plan(self, start=None, goal=None):
        if start is None:
            start = self.robot.get_cur_state()
        if goal is None:
            goal = [0.5] * self.robot.num_avail_joints

        s = ob.State(self.space)
        g = ob.State(self.space)
        for i in range(self.robot.num_avail_joints):
            s[i] = start[i]
            g[i] = goal[i]

        self.ss.setStartAndGoalStates(s, g)
        planner = og.RRTConnect(self.si)
        planner.setRange(0.1)
        self.ss.setPlanner(planner)

        print("[INFO] 开始规划……")
        solved = self.ss.solve(2.0)
        if solved:
            print("[SUCCESS] 规划成功！")
            path = self.ss.getSolutionPath()
            print("[INFO] 采样点数量：", path.getStateCount())
        else:
            print("[FAIL] 规划失败！")

# -------- 测试入口 --------
if __name__ == "__main__":
    # load robot
    import pybullet as p
    physics_client = p.connect(p.GUI)
    p.setGravity(0, 0, -9.8)
    p.setTimeStep(1. / 240.)
    urdf_path = r"../models/jaka_description/urdf/jaka_minicobo.urdf"
    robot = PbOMPLRobot(physics_client)
    robot.f_print = True
    robot.load_urdf(fileName=urdf_path, basePosition=(0, 0, 0), baseOrientation=(0, 0, 0, 1),
                    useFixedBase=1,
                    flags=p.URDF_USE_SELF_COLLISION,
                    )
    robot.inverse_mode='body'
    robot.reset()

    planner = TaskSpaceRRT(robot)
    planner.get_T_goal([0.0]*6)        # 设置末端目标姿态
    planner.prepare_sampler()          # 注册自定义采样器
    planner.plan()                     # 执行路径规划
