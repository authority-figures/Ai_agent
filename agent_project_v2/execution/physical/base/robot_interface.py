# execution/physical/base/robot_interface.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from scipy.spatial.transform import Rotation as R
import numpy as np

class RobotInterface(ABC):
    """所有物理机器人（或控制器）必须实现的统一接口"""

    def __init__(self, robot_ip: str,):
        self.robot_ip = robot_ip

    @abstractmethod
    async def connect(self,ip) -> None:
        """建立与物理机的连接（TCP/串口/SDK）"""

    @abstractmethod
    async def disconnect(self) -> None:
        """断开连接"""


    # ---- 状态相关 ----
    @abstractmethod
    async def get_joint_pos(self) -> Dict[str, Any]:
        """当前关节角"""

    # @abstractmethod
    # async def get_pose(self) -> Dict[str, Any]:
    #     """TCP 位姿等"""

    # ---- 控制命令 ----
    @abstractmethod
    async def joint_move(
        self,
        joint_positions: List[float],
        move_mode: int = 0,
        speed: Optional[float] = None,
        acc: Optional[float] = None,
        is_block: bool = True,
        tol: float = 0.0,
    ) -> None:
        """关节空间运动"""

    # @abstractmethod
    # async def move_line(
    #     self,
    #     pose: Dict[str, float],
    #     speed: Optional[float] = None,
    #     accel: Optional[float] = None,
    #     blocking: bool = True,
    # ) -> None:
    #     """笛卡尔空间运动"""




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
