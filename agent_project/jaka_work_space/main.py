from robot_controller import RobotServer
from api_server import *

def main():
    # 1. 实例化机械臂管理类
    robot_server = RobotServer(ip="192.168.1.10")

    # 2. 将 robot_server 注入或注册到 API 层（方式有很多，可根据需求选择）
    #    例如设置为某个全局变量，或者写一个 setter 函数，或使用 FastAPI 的依赖注入
    set_robot_server(robot_server)

    # 3. 启动 API 服务
    start_api_server()

if __name__ == "__main__":
    main()
