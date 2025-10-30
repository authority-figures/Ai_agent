# main_app.py
import sys
import os
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
import threading
import multiprocessing
import time
import socket


os.environ["QT_IM_MODULE"] = "fcitx"


# 添加项目根目录到Python路径，确保可以导入自定义模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def run_fastapi_app():
    """
    在一个单独的线程中运行 FastAPI 应用
    """
    import uvicorn

    # 先在这里初始化服务，确保API启动时服务已注册
    # initialize_services()
    """
    初始化核心服务并注册到ServiceLocator
    """
    logger.info("Initializing services...")

    try:
        from core.service_locator import ServiceLocator
        from agent.services.agent_service import AgentService
        from agent.services.task_repo import TaskRepo, create_repo

        # 初始化task repo
        repo = create_repo("redis://localhost")
        ServiceLocator.register('task_repo', repo)
        logger.info("TaskRepo registered successfully")

        # 初始化AgentService
        from agent.graph.Interactive_chat_graph import compiled_graph as Interactive_chat_compiled_graph
        agent_service = AgentService(compiled_graph=Interactive_chat_compiled_graph)
        ServiceLocator.register('agent_service', agent_service)
        logger.info("AgentService registered successfully")

        from agent.graph.plan_graph import compiled_graph as plan_compiled_graph
        plan_agent_service = AgentService(compiled_graph=plan_compiled_graph)
        ServiceLocator.register('plan_agent_service', plan_agent_service)
        logger.info("Plan AgentService registered successfully")

        # 这里可以初始化其他服务...
        # from services.simulation_service import SimulationService
        # simulation_service = SimulationService()
        # ServiceLocator.register('simulation_service', simulation_service)

    except Exception as e:
        logger.error(f"Failed to initialize services: {str(e)}")

    try:
        # 指定启动配置：应用对象、主机、端口等
        uvicorn.run(
            "api.main:app",  # 假设你的FastAPI app实例在 api/main.py 中，变量名为 app
            host="0.0.0.0",  # 允许所有网络接口访问
            port=8000,       # 指定端口
            reload=False,     # 开发时启用热重载，生产环境应设为 False
            log_level="info",
            loop="asyncio" # 调试时使用 asyncio 事件循环
        )
    except Exception as e:
        logger.error(f"Failed to start FastAPI server: {e}")
    finally:
        time.sleep(5)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            result = s.connect_ex(('127.0.0.1', 8000))
            if result == 0:
                print("✅ Backend actually listening on 8000")
            else:
                print("❌ Backend did NOT start in debug mode")


async def initialize_services():
    """
    初始化核心服务并注册到ServiceLocator
    """
    logger.info("Initializing services...")

    try:
        from core.service_locator import ServiceLocator
        from agent.services.agent_service import AgentService
        from agent.services.task_repo import TaskRepo, create_repo
        # 初始化task repo
        repo = await create_repo("redis://localhost")
        ServiceLocator.register('task_repo', repo)

        # 初始化AgentService
        agent_service = AgentService()
        ServiceLocator.register('agent_service', agent_service)

        logger.info("AgentService registered successfully")

        # 这里可以初始化其他服务...
        # from services.simulation_service import SimulationService
        # simulation_service = SimulationService()
        # ServiceLocator.register('simulation_service', simulation_service)

        return True
    except Exception as e:
        logger.error(f"Failed to initialize services: {str(e)}")
        return False


def setup_qt_application():
    """
    设置并返回Qt应用实例
    """
    logger.info("Setting up Qt application...")

    try:
        # 创建Qt应用实例[1,2](@ref)
        app = QApplication(sys.argv)
        app.setApplicationName("Agent Robot Control System")
        app.setApplicationVersion("1.0.0")

        # 可以设置应用样式等
        # app.setStyle('Fusion')

        logger.info("Qt application setup completed")
        return app
    except Exception as e:
        logger.error(f"Failed to setup Qt application: {str(e)}")
        raise


def create_main_window(app):
    """
    创建并返回主窗口实例
    """
    logger.info("Creating main window...")

    try:
        # 导入并创建主窗口
        from ui.views.main_window import MainWindow
        window = MainWindow()

        logger.info("Main window created successfully")
        return window
    except Exception as e:
        logger.error(f"Failed to create main window: {str(e)}")
        raise


def setup_global_exception_handling():
    """
    设置全局异常处理
    """

    def excepthook(type, value, traceback):
        logger.critical(f"Unhandled exception: {type.__name__}: {value}", exc_info=(type, value, traceback))
        sys.__excepthook__(type, value, traceback)

    sys.excepthook = excepthook


def main():
    """
    应用主入口函数
    """
    logger.info("Starting application...")

    try:
        # 0. 设置全局异常处理
        setup_global_exception_handling()

        # 1. 在后台线程中启动 FastAPI 服务器
        api_process = multiprocessing.Process(target=run_fastapi_app, daemon=False)
        api_process.start()
        logger.info(f"FastAPI server started in process (PID: {api_process.pid}).")

        # # 2. 初始化服务
        # if not initialize_services():
        #     logger.error("Service initialization failed. Exiting...")
        #     return 1

        # 3. 设置Qt应用
        app = setup_qt_application()

        # 4. 创建主窗口
        window = create_main_window(app)

        # 5. 显示主窗口[1,2](@ref)
        window.show()

        # 6. 启动应用事件循环[1,2](@ref)
        logger.info("Application started successfully")
        exit_code = app.exec_()

        logger.info(f"Application exited with code: {exit_code}")
        return exit_code

    except Exception as e:
        logger.critical(f"Failed to start application: {str(e)}")
        return 1


if __name__ == "__main__":
    # 直接运行时的入口点
    sys.exit(main())