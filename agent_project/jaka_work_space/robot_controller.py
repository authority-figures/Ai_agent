# robot_controller.py
import jkrc


class RobotServer:
    def __init__(self, ip: str):
        self.ip = ip
        self.robot = jkrc.RC(self.ip)
        self.logged_in = False

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

    def joint_move(self, joint_positions,move_mode=0, speed=20, acc=5,is_block=True,tol=0.1):
        """
        简单包装一下joint_move。
        joint_positions 是关节位置
        speed, acc 是速度与加速度
        """
        return self.robot.joint_move_extend(joint_positions,move_mode,is_block, speed, acc,tol)
