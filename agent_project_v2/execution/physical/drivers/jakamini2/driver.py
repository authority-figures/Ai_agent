import sys,os
import time
import cv2
import pybullet as p
# sys.path.extend(['/home/lwh/Project/python_project/Ai_agent/agent_project_v2/execution/physical/drivers/jakamini2/'])
sys.path.insert(0, '/home/lwh/Project/python_project/Ai_agent/agent_project_v2/execution/physical/drivers/jakamini2/')
from execution.physical.drivers.jakamini2.camera import RealSenseRGB
from execution.physical.base.robot_interface import RobotInterface
from execution.simulation.Robot import Robot
import numpy as np
import asyncio
import jkrc



class Jakamini2Driver(RobotInterface):
    def __init__(self, robot_ip: str,):
        super().__init__(robot_ip)
        # 在这里添加任何特定于 Jakamini2 机器人的初始化代码
        # self.robot = jkrc.RC(robot_ip)
        self.robot = None
        self.connected = False
        self.servo_enabled = False
        self.camera = RealSenseRGB()
        self.calibration_data = {}
        self.physics_client = None



    def init_sim(self):
        robot_urdf = r"/home/lwh/Project/python_project/Ai_agent/agent_project_v2/assets/models/jaka_description/urdf/jaka_minicobo_with_rolling_tool.urdf"

        self.physics_client = p.connect(p.DIRECT)
        self.sim_robot = Robot(self.physics_client)
        self.sim_robot.f_print = True
        self.sim_robot.load_urdf(fileName=robot_urdf, basePosition=(0, 0, 0), baseOrientation=(0, 0, 0, 1),
                                 useFixedBase=True,
                                 )
    async def connect(self,ip=None)->tuple:
        # 将同步函数放到线程中执行，不阻塞事件循环
        try:
            if not ip:
                ip = self.robot_ip
            self.robot = jkrc.RC(ip)
            self.robot_ip = ip
            ret = await asyncio.to_thread(self.robot.login)
            if ret[0] == 0:
                self.connected = True
                return (ret[0],ret[1])
            else:
                print(f"[Jakamini2Driver:connect] Failed to connect: {ret[1]}")
                return (ret[0],ret[1])
        except Exception as e:
            print(f"[Jakamini2Driver:connect] Exception: {e}")
            return (-1, str(e))

    async def disconnect(self)->tuple:
        try:
            if not self.robot:
                return (-1, "Robot not connected")
            ret = await asyncio.to_thread(self.robot.logout)
            if ret[0] == 0:
                self.connected = False
                return (ret[0],ret[1])
            else:
                print(f"[Jakamini2Driver:disconnect] Failed to disconnect: {ret[1]}")
                return (ret[0],ret[1])
        except Exception as e:
            print(f"[Jakamini2Driver:disconnect] Exception: {e}")
            return (-1, str(e))


    async def power_on(self)->tuple:
        try:
            if not self.robot:
                return (-1, "Robot not connected")
            ret = await asyncio.to_thread(self.robot.power_on)
            return ret
        except Exception as e:
            print(f"[Jakamini2Driver:power_on] Exception: {e}")
            return (-1, str(e))

    async def power_off(self):
        try:
            if not self.robot:
                return (-1, "Robot not connected")
            ret = await asyncio.to_thread(self.robot.power_off)
            return ret
        except Exception as e:
            print(f"[Jakamini2Driver:power_off] Exception: {e}")
            return (-1, str(e))

    async def enable_robot(self):
        try:
            if not self.robot:
                return (-1, "Robot not connected")
            ret = await asyncio.to_thread(self.robot.enable_robot)
            return ret
        except Exception as e:
            print(f"[Jakamini2Driver:enable_robot] Exception: {e}")
            return (-1, str(e))

    async def disable_robot(self):
        try:
            if not self.robot:
                return (-1, "Robot not connected")
            ret = await asyncio.to_thread(self.robot.disable_robot)
            return ret
        except Exception as e:
            print(f"[Jakamini2Driver:disable_robot] Exception: {e}")
            return (-1, str(e))

    async def get_joint_pos(self):
        try:
            if not self.robot:
                return (-1, "Robot not connected")
            ret = await asyncio.to_thread(self.robot.get_joint_position)
            if ret[0] == 0:
                return ret[1]
            return None
        except Exception as e:
            print(f"[Jakamini2Driver:get_joint_pos] Exception: {e}")
            return None

    async def joint_move(self, joint_positions,move_mode=0, speed=1, acc=1,is_block=True,tol=0.0):
        """
        简单包装一下joint_move。
        joint_positions 是关节位置
        speed, acc 是速度与加速度
        """
        return await self.robot.joint_move_extend(joint_positions,move_mode,is_block, speed, acc,tol)

    async def servo_move_use_joint_NLF(self, max_vr=2, max_ar=2, max_jr=4):
        """
        简单包装一下servo_move_use_joint_NLF。
        joint_positions 是关节位置
        speed, acc 是速度与加速度
        """
        if self.servo_enabled == True:
            raise Exception("Servo move is enabled. Please disable it first.")

        return await self.robot.servo_move_use_joint_NLF(max_vr, max_ar, max_jr)

    async def servo_move_enable(self,enable):
        """
        简单包装一下servo_move_enable。
        joint_positions 是关节位置
        speed, acc 是速度与加速度
        """
        if enable==True:
            self.servo_enabled = True
            return await self.robot.servo_move_enable(enable)
        else:
            self.servo_enabled = False
            return await self.robot.servo_move_enable(enable)

    async def servo_j(self, joint_pos, move_mode=0,step_num=1):
        """
        简单包装一下servo_j。
        joint_positions 是关节位置
        move_mode 是增量还是绝对
        """
        if self.servo_enabled == False:
            await self.servo_move_enable(True)
            self.servo_enabled = True

        return await self.robot.servo_j(joint_pos=joint_pos, move_mode=move_mode,step_num=step_num)


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



    async def move_path(self, path,step_num=1):
        """

        """
        if self.servo_enabled == False:
            await self.servo_move_enable(True)
            self.servo_enabled = True

        for joints in path:
            if not self.validate_joint_values(joints):
                raise Exception("Invalid joint values: {}".format(joints))
            await self.servo_j(joint_pos=joints, move_mode=0, step_num=step_num)

        # 等待到达目标位置
        while True:
            current_joints = await self.get_joint_pos()
            if current_joints is None:
                raise Exception("获取关节位置失败")
            if np.allclose(current_joints, path[-1], atol=0.01):
                break
            await asyncio.sleep(0.1)
        await self.servo_move_enable(False)


        return 0,None


    async def use_camera(self,point_data:dict={},id:int=0):
        if not self.camera.started:
            self.camera.start()
            await asyncio.sleep(1)
        for _ in range(10):
            rgb_img = self.camera.get_rgb_frame()
            data = {}
            if rgb_img is not None:
                cv2.imshow("RGB", rgb_img)
                cv2.waitKey(1)
                ret = self.camera.detect_cirle(rgb_img)
                if ret:
                    data['img'] = rgb_img
                    joints = await self.get_joint_pos()
                    if joints is None:
                        raise Exception("获取关节位置失败")
                    pos,ori = self.sim_robot.get_pos_ori_from_ik(joints=joints)
                    data["TB2E"] = self.pos_to_matrix(pos,ori)
                    point_data[f'point_{id}'] = data
                    return True
                else:
                    await asyncio.sleep(0.2)
                    continue
            else:
                print("[WARNING] 无法获取 RGB 图像。")

        return False


if __name__ == '__main__':
    robot = Jakamini2Driver('192.168.100.20')
    asyncio.run(robot.connect())
    pass



