
import numpy as np
from pb_ompl import *
from scipy.spatial.transform.rotation import Rotation as R

class TaskSpaceRRT(PbOMPL):
    def __init__(self, robot, obstacles=[]):
        super(TaskSpaceRRT, self).__init__(robot, obstacles)
        self.z_range = (0.01, 0.05)  # z-axis range for sampling
        self.x_range = (-0.01, 0.01)
        self.y_range = (-0.01, 0.01)
        self.yaw_range = 15
        self.roll_range = 5
        self.pitch_range = 5

        self.T_goal = None
        self.valid_joint_samples = []



    def set_tsRRT_sample(self):
        # def allocator(si):
        #     print("[DEBUG] allocator")
        #     return MixedValidStateSampler(si, self.sample_in_task_space, ratio=0.8)
        # self.si.setValidStateSamplerAllocator(ob.ValidStateSamplerAllocator(allocator))

        self.set_state_sampler(MixedStateSampler(self.space, self.sample_in_task_space, ratio=0.3))

    def set_random_sample(self):
        self.set_state_sampler(self.space.allocDefaultStateSampler())

    def sample_in_task_space(self, num_samples=1):
        if self.T_goal is None:
            return None
        joints = None
        end_effector_poses = self.sample_end_effector_poses(self.T_goal, num_samples)
        for T_sampled in end_effector_poses:
            pos, ori = self.robot.matrix_to_pos(T_sampled)
            joints = self.robot.get_state_from_ik(pos, ori, tcp_name="rolling_tool")
            if joints is not None:
                self.valid_joint_samples.append(joints)
        return joints
        pass


    def get_T_goal(self, joints, tcp_name=None):
        """
        Get the transformation matrix for the goal pose
        """
        pos,ori = self.robot.get_pos_ori_from_ik(joints, tcp_name=tcp_name)
        T_goal = np.eye(4)
        T_goal[:3, :3] = R.from_quat(ori).as_matrix()
        T_goal[:3, 3] = pos
        self.T_goal = T_goal.copy()
        return T_goal

    def sample_end_effector_poses(self,T_goal=None, num_samples=10):
        """
        Sample end-effector poses in the task space
        """
        end_effector_poses = []
        if T_goal is None:
            raise ValueError("T_goal must be provided")
        for _ in range(num_samples):
            # Sample a random pos along -z in the end-effector space
            pos_offset = np.array([np.random.uniform(self.x_range[0],self.x_range[1] ),
                                   np.random.uniform(self.y_range[0],self.y_range[1] )
                                      ,-np.random.uniform(self.z_range[0],self.z_range[1] )])  # pos in end-effector sys
            sampled_pos = T_goal[:3, 3] + T_goal[:3, :3] @ pos_offset # pos in base sys

            # Sample small random rotation around the yaw / roll / pitch axis
            T_perturbed_rot = self.perturb_rotation(T_goal,self.yaw_range, self.roll_range, self.pitch_range)
            T_sampled = T_goal.copy()
            T_sampled[:3, 3] = sampled_pos
            T_sampled[:3, :3] = T_perturbed_rot
            end_effector_poses.append(T_sampled)
        return end_effector_poses


    def perturb_rotation(self, T_goal,yaw_range=15, roll_range=5, pitch_range=5):
        """
        Perturb the rotation of the end-effector pose
        """
        # Sample a small random rotation around the yaw / roll / pitch axis
        yaw_offset = np.random.uniform(-np.radians(yaw_range), np.radians(yaw_range))
        roll_offset = np.random.uniform(-np.radians(roll_range), np.radians(roll_range))
        pitch_offset = np.random.uniform(-np.radians(pitch_range), np.radians(pitch_range))

        # Local rotation in end-effector frame
        rot_offset_local = R.from_euler('yxz', [yaw_offset, pitch_offset, roll_offset]).as_matrix()

        # Convert to world frame: R_new = R_world @ R_offset_local
        R_world = T_goal[:3, :3] @ rot_offset_local
        return R_world






import random
class MixedValidStateSampler(ob.ValidStateSampler):
    def __init__(self, si, guided_samples, ratio=0.4):
        super().__init__(si)
        self.name_ = "MixedValidStateSampler"
        self.guided_samples = guided_samples
        self.ratio = ratio
        self.default_sampler = si.allocStateSampler()

    def sample(self, state):
        print("[DEBUG] MixedValidStateSampler.sample()")
        if random.random() < self.ratio:
            # Guided sample
            ret = self.guided_samples()
            if ret:
                sample = ret
            else:
                return False
            for i in range(len(sample)):
                state[i] = sample[i]
            return True
        else:
            # Fallback to default sampler (e.g., UniformRealVectorStateSampler)
            return self.default_sampler.sample(state)

    def sampleNear(self, state, near, distance):
        # Optional: let OMPL handle local sampling
        return self.default_sampler.sampleNear(state, near, distance)


class MixedStateSampler(ob.StateSampler):
    def __init__(self, space, guided_samples, ratio=0.4):
        super().__init__(space)
        self.name_ = "MixedStateSampler"
        self.guided_samples = guided_samples
        self.ratio = ratio
        self.default_sampler = space.allocDefaultStateSampler()

    def sampleUniform(self, state):

        if random.random() < self.ratio:
            # Guided sample
            ret = self.guided_samples()
            if ret:
                sample = ret
                for i in range(len(sample)):
                    state[i] = sample[i]

                return
        else:
            # Fallback to default sampler (e.g., UniformRealVectorStateSampler)

            self.default_sampler.sampleUniform(state)

    def sampleUniformNear(self, state, near, distance):
        # Optional: let OMPL handle local sampling
        return self.default_sampler.sampleUniformNear(state, near, distance)
    def sampleGaussian(self, state, mean, stdDev):
        # Optional: let OMPL handle Gaussian sampling
        return self.default_sampler.sampleGaussian(state, mean, stdDev)



def test_sampling():
    import pybullet as p
    import pybullet_data
    import time

    physics_client = p.connect(p.GUI)
    p.setGravity(0, 0, -9.8)
    p.setTimeStep(1. / 240.)
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.loadURDF("plane.urdf")



    # load robot
    robot_with_rolling_tool_urdf = r"./models/jaka_description/urdf/jaka_minicobo_with_rolling_tool.urdf"
    robot = PbOMPLRobot(physics_client)
    robot.f_print = True
    robot.load_urdf(fileName=robot_with_rolling_tool_urdf, basePosition=(0, 0, 0), baseOrientation=(0., 0, 0, 1),
                    useFixedBase=1,
                    flags=p.URDF_USE_SELF_COLLISION,
                    )
    # 设置机械臂的tcp坐标
    ee_pos, ee_orn = p.getLinkState(robot.id_robot, 6)[4:6]
    tcp_pos, tcp_orn = p.getLinkState(robot.id_robot, 10)[4:6]
    tcp_in_ee_matrix = robot.TAB_with_AinW_and_BinW(tcp_pos, tcp_orn, ee_pos, ee_orn)
    robot.add_tcp("rolling_tool", tcp_in_ee_matrix)
    robot.inverse_mode = "body"
    robot.reset()

    pos = [0.1,0.3,0.5]
    ori = R.from_euler('xyz', [90, 0, 180],degrees=True).as_quat()

    tsRRT = TaskSpaceRRT(robot)

    joints = robot.get_state_from_ik(pos,ori,tcp_name="rolling_tool")
    robot.set_joints_states(joints,)

    pos, ori = robot.get_pos_ori_from_ik(joints, tcp_name="rolling_tool")
    print("ik pos: ", pos, "ori: ", ori)
    # get end-effector pose
    pos, ori = p.getLinkState(robot.id_robot, 10)[4:6]
    print("end-effector pos: ", pos, "ori: ", ori)

    # setup pb_ompl
    tsRRT.yaw_range = 30
    tsRRT.roll_range = 0
    tsRRT.pitch_range = 0
    tsRRT.z_range = (0.001, 0.1)  # z-axis range for sampling
    # Sample a random end-effector pose
    T_goal = tsRRT.get_T_goal(robot.get_state_from_ik(pos,ori,tcp_name="rolling_tool"),tcp_name="rolling_tool")
    end_effector_poses = tsRRT.sample_end_effector_poses(T_goal=T_goal, num_samples=10)

    import threading
    def run_simulation():
        while True:
            # Sample a random end-effector pose

            robot.show_link_sys(10, -1, 1, name="1")

            p.stepSimulation()
            time.sleep(1. / 240.)

    simulation_thread = threading.Thread(target=run_simulation, )
    simulation_thread.start()

    for end_effector_pose in end_effector_poses:
        pos1, ori1 = robot.matrix_to_pos(end_effector_pose)
        joints = robot.get_state_from_ik(pos1, ori1, tcp_name="rolling_tool")
        robot.joint_move(joints,maxVelocity=2)
        time.sleep(2)

    simulation_thread.join()






if __name__ == '__main__':
    test_sampling()
