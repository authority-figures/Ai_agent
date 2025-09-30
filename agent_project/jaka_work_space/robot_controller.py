# robot_controller.py
# %%
import sys,os
import time
import cv2
sys.path.extend(['/home/lwh/Project/python_project/Ai_agent/agent_project/jaka_work_space/'])
from scipy.spatial.transform import Rotation as R
import pybullet as p
from camera import RealSenseRGB
from agent_project.simulation.Robot import Robot

# os.environ['LD_LIBRARY_PATH'] = '/home/lwh/Project/python_project/Ai_agent/agent_project/jaka_work_space/'
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import jkrc
import numpy as np

class RobotServer:
    def __init__(self, ip: str):
        self.ip = ip
        self.robot = jkrc.RC(self.ip)
        self.logged_in = False
        self.servo_enabled = False
        self.camera = RealSenseRGB()
        self.calibration_data = {}

        robot_urdf = r"/home/lwh/Project/python_project/Ai_agent/agent_project/simulation/models/jaka_description/urdf/jaka_minicobo_with_rolling_tool.urdf"

        self.physics_client = p.connect(p.DIRECT)
        self.sim_robot = Robot(self.physics_client)
        self.sim_robot.f_print = True
        self.sim_robot.load_urdf(fileName=robot_urdf, basePosition=(0,0,0), baseOrientation=(0,0,0,1),
                        useFixedBase=True,
                        )



    def login(self):
        ret = self.robot.login()
        if ret[0] == 0:
            self.logged_in = True
        return ret

    def logout(self):
        ret = self.robot.logout()
        if ret[0] == 0:
            self.logged_in = False
        return ret

    def power_on(self):
        return self.robot.power_on()

    def power_off(self):
        return self.robot.power_off()

    def enable_robot(self):
        return self.robot.enable_robot()

    def disable_robot(self):
        return self.robot.disable_robot()

    def move_line(self, position, speed, acc):
        """
        简单包装一下move_line。
        position 是 [x, y, z, rx, ry, rz]
        speed, acc 是速度与加速度
        """
        return self.robot.move_line(position, speed, acc)

    def get_joints(self):
        """
        获取当前关节位置
        """
        ret = self.robot.get_joint_position()
        if ret[0] == 0:
            return ret[1]
        return None


    def joint_move(self, joint_positions,move_mode=0, speed=1, acc=1,is_block=True,tol=0.0):
        """
        简单包装一下joint_move。
        joint_positions 是关节位置
        speed, acc 是速度与加速度
        """
        return self.robot.joint_move_extend(joint_positions,move_mode,is_block, speed, acc,tol)

    def servo_move_use_joint_NLF(self, max_vr=2, max_ar=2, max_jr=4):
        """
        简单包装一下servo_move_use_joint_NLF。
        joint_positions 是关节位置
        speed, acc 是速度与加速度
        """
        if self.servo_enabled == True:
            raise Exception("Servo move is enabled. Please disable it first.")

        return self.robot.servo_move_use_joint_NLF(max_vr, max_ar, max_jr)

    def servo_move_enable(self,enable):
        """
        简单包装一下servo_move_enable。
        joint_positions 是关节位置
        speed, acc 是速度与加速度
        """
        if enable==True:
            self.servo_enabled = True
            return self.robot.servo_move_enable(enable)
        else:
            self.servo_enabled = False
            return self.robot.servo_move_enable(enable)

    def servo_j(self, joint_pos, move_mode=0,step_num=1):
        """
        简单包装一下servo_j。
        joint_positions 是关节位置
        move_mode 是增量还是绝对
        """
        if self.servo_enabled == False:
            self.servo_move_enable(True)
            self.servo_enabled = True

        return self.robot.servo_j(joint_pos=joint_pos, move_mode=move_mode,step_num=step_num)

    def validate_joint_values(self, joint_pos):



        """
        验证关节值是否合法
        joint_pos 是一个包含6个关节值的列表或数组
        """
        if len(list(joint_pos)) != 6:
            return False  # 关节值数量不正确

        # 检查每个关节值是否在合法范围内
        # 这里假设关节值范围是 [-360, 360] 度
        if (joint_pos[0] < -360 / 180 * np.pi or joint_pos[0] > 360 / 180 * np.pi): return False
        if (joint_pos[1] < -125 / 180 * np.pi or joint_pos[1] > 125 / 180 * np.pi): return False
        if (joint_pos[2] < -130 / 180 * np.pi or joint_pos[2] > 130 / 180 * np.pi): return False
        if (joint_pos[3] < -360 / 180 * np.pi or joint_pos[3] > 360 / 180 * np.pi): return False
        if (joint_pos[4] < -120 / 180 * np.pi or joint_pos[4] > 120 / 180 * np.pi): return False
        if (joint_pos[5] < -360 / 180 * np.pi or joint_pos[5] > 360 / 180 * np.pi): return False

        return True # 所有关节值均合法



    def move_path(self, path,step_num=1):
        """

        """
        if self.servo_enabled == False:
            self.servo_move_enable(True)
            self.servo_enabled = True

        for joints in path:
            if not self.validate_joint_values(joints):
                raise Exception("Invalid joint values: {}".format(joints))
            self.servo_j(joint_pos=joints, move_mode=0, step_num=step_num)

        # 等待到达目标位置
        while True:
            current_joints = self.get_joints()
            if current_joints is None:
                raise Exception("获取关节位置失败")
            if np.allclose(current_joints, path[-1], atol=0.01):
                break
            time.sleep(0.1)
        self.servo_move_enable(False)


        return 0,None


    def run_nine_point_calibration_path(self,paths:dict=None,use_camera=True):
        point_data = {}
        success_list = []
        if paths:
            for id,key in enumerate(paths.keys()):
                path = paths[key]
                self.servo_move_enable(True)
                self.move_path(path)
                self.servo_move_enable(False)
                if use_camera:
                    time.sleep(1)
                    ifsuccess = self.use_camera(point_data,id)
                    success_list.append(ifsuccess)
                    cv2.destroyAllWindows()
                time.sleep(2)

            if use_camera:
                self.calibration_data['point_data'] = point_data
                K,D = self.camera.get_intrinsics()
                self.calibration_data["camera_matrix"] = K
                self.calibration_data['dist_coeffs'] = D
                self.camera.release()
                if not all(success_list):
                    raise Exception("相机标定失败，请检查相机和标定板的状态。")
                else:
                    print("[INFO] 相机标定成功。")
                    np.savez(f"/home/lwh/Project/python_project/Ai_agent/agent_project/jaka_work_space/datas/calibration_data.npz", **self.calibration_data)
                    print("[INFO] 标定数据已保存。")
        pass

    def use_camera(self,point_data:dict={},id:int=0):
        if not self.camera.started:
            self.camera.start()
            time.sleep(1)
        for _ in range(10):
            rgb_img = self.camera.get_rgb_frame()
            data = {}
            if rgb_img is not None:
                cv2.imshow("RGB", rgb_img)
                cv2.waitKey(1)
                ret = self.camera.detect_cirle(rgb_img)
                if ret:
                    data['img'] = rgb_img
                    joints = self.get_joints()
                    if joints is None:
                        raise Exception("获取关节位置失败")
                    pos,ori = self.sim_robot.get_pos_ori_from_ik(joints=joints)
                    data["TB2E"] = self.pos_to_matrix(pos,ori)
                    point_data[f'point_{id}'] = data
                    return True
                else:
                    time.sleep(0.2)
                    continue
            else:
                print("[WARNING] 无法获取 RGB 图像。")

        return False



    @staticmethod
    def pos_to_matrix(pos, ori):
        """
        将位置和姿态转换为 4x4 变换矩阵。

        参数:
        - pos: 位置 (3 元素列表或数组)
        - ori: 姿态 (四元数, 4 元素列表或数组)(x, y, z, w)

        返回:
        - T: 4x4 变换矩阵
        """
        rot = R.from_quat(ori).as_matrix()
        T = np.eye(4)
        T[:3, :3] = rot
        T[:3, 3] = pos
        return T

    @staticmethod
    def matrix_to_pos(matrix):
        """
        将 4x4 变换矩阵转换为位置和姿态。
        :param matrix:
        :return:
        """
        assert matrix.shape == (4, 4), "Matrix must be 4x4"
        pos = matrix[:3, 3]
        rot = R.from_matrix(matrix[:3, :3]).as_quat()
        return pos, rot

# %%
if __name__ == '__main__':
    robot = RobotServer('192.168.100.20')
    robot.login()


    paths = np.load('/home/lwh/Project/python_project/Ai_agent/agent_project/simulation/test/test_data/interpolate_path_005.npz')
    current_joints = robot.get_joints()
    cj = np.array(current_joints, dtype=np.float64)
    target = np.array(paths['point_0'][0], dtype=np.float64)
    if not np.allclose(current_joints, paths['point_0'][0], atol=0.001):
        robot.move_path(paths['point_0'][::-1])
    robot.run_nine_point_calibration_path(paths=paths,use_camera=True)

