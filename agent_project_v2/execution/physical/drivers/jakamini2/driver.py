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

        # 创建查询机械臂状态的轮询任务
        self._status_task: asyncio.Task | None = None
        self._status_interval = 0.01  # 轮询周期，单位秒
        self._last_status = None  # 可选：缓存最近一次状态



    def init_sim(self):
        robot_urdf = r"/home/lwh/Project/python_project/Ai_agent/agent_project_v2/assets/models/jaka_description/urdf/jaka_minicobo_with_rolling_tool_12mm.urdf"

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
                return (ret[0],"connect success")
            else:
                print(f"[Jakamini2Driver:connect] Failed to connect: {ip}")
                return (ret[0],"Failed to connect")
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
                return (ret[0],"disconnect success")
            else:
                print(f"[Jakamini2Driver:disconnect] Failed to disconnect: {ret[1]}")
                return (ret[0],"disconnect failed")
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

    async def get_robotstatus(self):
        '''
        成功：(0, robotstatus)，robotstatus的长度为24，robotstatus返回数据顺序如下所示:
            errcode 机器人运行出错时错误编号，0为运行正常，其它为异常
            inpos 机器人运动是否到位标志，0为没有到位，1为运动到位
            powered_on 机器人是否上电标志，0为没有上电，1为上电
            enabled 机器人是否使能标志，0为没有使能，1为使能
            rapidrate 机器人运行倍率
            protective_stop 机器人是否检测到碰撞，0为没有检测到碰撞，1则相反
            drag_status机器人是否处于拖拽状态，0为没有处于拖拽状态，1则相反
            on_soft_limit 机器人是否处于限位，0为没有触发限位保护，1为触发限位保护
            current_user_id 机器人目前使用的用户坐标系id
            current_tool_id 机器人目前使用的工具坐标系id
            dout 机器人控制柜数字输出信号
            din 机器人控制柜数字输入信号
            aout 机器人控制柜模拟输出信号
            ain 机器人控制柜模拟输入信号
            tio_dout 机器人末端工具数字输出信号
            tio_din 机器人末端工具数字输入信号
            tio_ain 机器人末端工具模拟输入信号
            extio 机器人外部扩展模块IO信号
            cart_position 机器人末端的笛卡尔空间位置值
            joint_position 机器人关节空间位置
            robot_monitor_data 机器人状态监测数据（scb主版本号、scb小版本号、控制器温度、机器人平均电压、机器人平均电流、机器人6个关节的监测数据（瞬时电流、瞬时电压、瞬时温度））
            torq_sensor_monitor_data 机器人力矩传感器状态监测数据（力矩传感器ip地址、力矩传感器端口号、工具负载（负载质量、质心x轴坐标、质心y轴坐标、质心z轴坐标）、力矩传感器状态、力矩传感器异常错误码、6个力矩传感器实际接触力值、6个力矩传感器原始读数值、6个力矩传感器实际接触力值（不随初始化选项变化））
            is_socket_connect sdk与控制器连接通道是否正常，0为连接通道异常，1为连接通道正常
            emergency_stop 机器人是否急停，0为没有按下急停，1则相反
            tio_key 机器人末端工具按钮 [0]free；[1]point；[2]末端灯光按钮
            失败：其它
        :return:
        '''
        try:
            if not self.robot:
                return (-1, "Robot not connected")
            ret = await asyncio.to_thread(self.robot.get_robot_status)
            return ret
        except Exception as e:
            print(f"[Jakamini2Driver:get_robotstatus] Exception: {e}")
            return (-1, str(e))


    async def _status_loop(self):
        """后台协程：持续轮询机器人状态"""
        try:
            while self.connected:
                ret = await self.get_robotstatus()
                # ret 具体是什么结构看 jkrc 返回，这里假设 ret[0] 为错误码
                if ret[0] == 0:
                    status = ret[1]
                    self._last_status = status
                    # TODO: 在这里做你想做的事，比如发布到 event_bus / 更新 DT
                    # event_bus.publish("robot_status_updated", {...})
                else:
                    print(f"[Jakamini2Driver:status_loop] get_robotstatus failed: {ret}")
                await asyncio.sleep(self._status_interval)
        except asyncio.CancelledError:
            # 任务被取消时的收尾处理
            print("[Jakamini2Driver:status_loop] cancelled")
        except Exception as e:
            print(f"[Jakamini2Driver:status_loop] Exception: {e}")

    def start_status_monitor(self, interval: float = 0.1):
        """在当前事件循环中启动状态监控任务"""
        self._status_interval = interval
        if self._status_task is not None and not self._status_task.done():
            return  # 已经在跑了

        loop = asyncio.get_running_loop()
        self._status_task = loop.create_task(self._status_loop())

    async def stop_status_monitor(self):
        """停止状态监控任务"""
        if self._status_task is not None:
            self._status_task.cancel()
            try:
                await self._status_task
            except asyncio.CancelledError:
                pass
            self._status_task = None



    async def joint_move(self, joint_positions,move_mode=0, speed=1, acc=1,is_block=True,tol=0.0)->tuple:
        """
        简单包装一下joint_move。
        joint_positions 是关节位置
        speed, acc 是速度与加速度
        """
        ret = await asyncio.to_thread(
            self.robot.joint_move_extend,
            joint_positions,
            move_mode,
            is_block,
            speed,
            acc,
            tol
        )
        return ret

    async def servo_move_use_joint_NLF(self, max_vr=2, max_ar=2, max_jr=4):
        """
        简单包装一下servo_move_use_joint_NLF。
        joint_positions 是关节位置
        speed, acc 是速度与加速度
        """
        if self.servo_enabled == True:
            raise Exception("Servo move is enabled. Please disable it first.")
        ret = await asyncio.to_thread(self.robot.servo_move_use_joint_NLF,max_vr, max_ar, max_jr)


        return ret

    async def servo_move_use_joint_LPF(self, cutoffFreq=0.5):
        """
        简单包装一下servo_move_use_joint_NLF。
        joint_positions 是关节位置
        speed, acc 是速度与加速度
        """
        if self.servo_enabled == True:
            raise Exception("Servo move is enabled. Please disable it first.")
        ret = await asyncio.to_thread(self.robot.servo_move_use_joint_LPF, cutoffFreq)

        return ret



    async def servo_move_enable(self,enable):
        """
        简单包装一下servo_move_enable。
        joint_positions 是关节位置
        speed, acc 是速度与加速度
        """
        if enable==True:
            self.servo_enabled = True
            ret = await asyncio.to_thread(self.robot.servo_move_enable,enable)
            return ret

        else:
            self.servo_enabled = False
            ret = await asyncio.to_thread(self.robot.servo_move_enable,enable)
            return ret


    async def servo_j(self, joint_pos, move_mode=0,step_num=1):
        """
        简单包装一下servo_j。
        joint_positions 是关节位置
        move_mode 是增量还是绝对
        """
        if self.servo_enabled == False:
            await self.servo_move_enable(True)
            self.servo_enabled = True

        ret = await asyncio.to_thread(
            self.robot.servo_j,
            joint_pos=joint_pos,
            move_mode=move_mode,
            step_num=step_num
        )
        return ret


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
            await asyncio.sleep(0.008)

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


    async def run_nine_point_calibration_path(self,paths:dict=None,use_camera=True):
        current_joints = await self.get_joint_pos()
        if current_joints is None:
            raise Exception("获取关节位置失败")
        if not np.allclose(current_joints, paths['point_0'][0], atol=0.001):
            await self.joint_move(paths['point_0'][0])
        point_data = {}
        success_list = []
        if paths:
            for id,key in enumerate(paths.keys()):
                path = paths[key]
                await self.servo_move_enable(True)
                await self.move_path(path)
                await self.servo_move_enable(False)
                if use_camera:
                    time.sleep(1)
                    ifsuccess = await self.use_camera(point_data,id)
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
                    np.savez(f"/home/lwh/Project/python_project/Ai_agent/agent_project_v2/execution/physical/data/calibration_data.npz", **self.calibration_data)
                    print("[INFO] 标定数据已保存。")
        pass


'''
/home/lwh/Project/python_project/Ai_agent/agent_project/simulation/test/test_pathplanning/path_files/滚压_path.npy
初始姿态
start [0.14192261229704023, 0.12777528184055628, -1.5362067689104764, 0.0007951065080360192, -1.733048469695333, -0.6433431903539001]
装配调试中的叶片最上角
[0.4879219885883196, -0.5562600932828626, -0.9357658112807045, 0.14464824871696938, -1.906429588556646, -0.2675356408611036]
joints = np.load("/home/lwh/Project/python_project/Ai_agent/agent_project/simulation/test/test_pathplanning/path_files/滚压_path.npy")
joints[789] 是一个靠近最外面的点

file_path = r'/home/lwh/Project/python_project/Ai_agent/agent_project/simulation/test/test_pathplanning/path_files/滚压到位点_6061_C轴连续加工.cls'

goto, origin_data = sim_env.rm_sys.read_cls_file(sim_env.robot_list[0], file_path, inverse=True)
pos_list, ori_list = [], []
for item in goto:
    # 解包位置信息pos (X/Y/Z)
    pos_list.append((item['X'], item['Y'], item['Z']))
    # 解包姿态信息ori (x/y/z/w)
    ori_list.append((item['O']['x'], item['O']['y'], item['O']['z'], item['O']['w']))
'''

if __name__ == '__main__':
    robot = Jakamini2Driver('192.168.100.20')
    robot.init_sim()
    asyncio.run(robot.connect())
    pass



