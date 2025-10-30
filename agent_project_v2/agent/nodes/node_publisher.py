from core.service_locator import ServiceLocator
import asyncio, threading

# def send_state(node_name, state):
#     """
#     模拟将节点状态发送到AgentService进行处理
#     """
#     try:
#         agent_service = ServiceLocator.get('agent_service')
#         if agent_service:
#             agent_service.broadcast_state({"node": node_name, "state": state})
#             return True
#         else:
#             print("AgentService not found in ServiceLocator.")
#             return False
#     except Exception as e:
#         print(f"Error sending state to AgentService: {e}")
#         return False

def send_state(node_name, state):
    """
    将节点状态即时广播到 WebSocket
    """
    try:
        agent_service = ServiceLocator.get('agent_service')
        if not agent_service:
            print("AgentService not found in ServiceLocator.")
            return False

        message = {"node": node_name, "state": state}

        # ✅ 独立线程执行异步任务，保证实时广播
        threading.Thread(
            target=lambda: asyncio.run(agent_service.broadcast_state(message)),
            daemon=True
        ).start()

        return True

    except Exception as e:
        print(f"Error sending state to AgentService: {e}")
        return False
