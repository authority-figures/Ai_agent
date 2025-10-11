'''
提供Agent相关服务
负责与langgrain交互
'''
import traceback
from langgraph.graph import StateGraph
from agent.graph.chat_loop_graph import graph as compiled_graph


class AgentService:
    """一个专门用于提供智能体相关功能的服务"""
    def __init__(self):
        self.connections = set()

    def set_connection_pool(self, connections):
        '''从 FastAPI 注入 WebSocket 连接池'''
        self.connections = connections

    def invoke_graph(self, user_input):
        try:
            result = compiled_graph.invoke({"input": user_input})
        except EOFError:
            # 打印完整堆栈，定位哪一行调了 input()
            traceback.print_exc()
            # 如果想继续跑，可以 return 一个默认值
            result = {"error": "interactive input not allowed in this environment"}
        return result

    def get_graph_structure(self):
        """
        获取LangGraph图的结构化信息。
        返回包含节点和边的字典，便于前端可视化。

        Returns:
            dict: {"nodes": [...], "edges": [{"from": str, "to": str, "condition": bool}]}
        """
        # 方法1: 如果你的LangGraph版本支持，直接获取图表示
        # graph_structure = compiled_graph.get_graph()
        # 然后将其转换为前端需要的格式

        # 方法2: 手动构建图结构信息（通用方法）
        # 这里需要根据你编译的图对象实际结构来调整
        graph_obj = compiled_graph.get_graph()  # 获取内部图表示

        nodes = []
        edges = []

        # 假设 graph_obj 有 nodes 和 edges 属性
        # 遍历节点，将其转换为前端可识别的格式
        for node_name,data in graph_obj.nodes.items():
            nodes.append({
                "id": node_name,
                "name": node_name,
                # 可以根据节点类型添加更多属性，如形状、颜色等
                "node_type": node_name if "start" in node_name or "end" in node_name
                else data.metadata.get("node_type", "normal") if data.metadata is not None else "normal"
            })

        # 2. 根据 edges 实际格式，调整遍历逻辑（重点修改这里）
        # ------------------- 情况1：edges 是“元组列表”（最常见） -------------------
        if isinstance(graph_obj.edges, list) and all(isinstance(edge, tuple) for edge in graph_obj.edges):
            for edge in graph_obj.edges:
                source_node = edge[0]  # 元组第一个元素是起点
                target_node = edge[1]  # 元组第二个元素是终点
                data = edge[2] # 元组第三个元素是边的数据（如果有）
                conditional = edge[3]   # 元组第四个元素是条件（True/False）
                edges.append({"from": source_node, "to": target_node, "data": data, "type": "condition" if conditional else "normal"})

        # ------------------- 情况2：edges 是“字典列表”（含 source/target 键） -------------------
        elif isinstance(graph_obj.edges, list) and all(isinstance(edge, dict) for edge in graph_obj.edges):
            for edge in graph_obj.edges:
                # 确保字典有 source 和 target 键（避免键不存在报错）
                if "source" in edge and "target" in edge:
                    source_node = edge["source"]
                    target_node = edge["target"]
                    data = edge.get("data", None)  # 边数据可选
                    conditional = edge.get("condition", False)  # 条件可选
                    edges.append({"from": source_node, "to": target_node, "data": data, "type": "condition" if conditional else "normal"})
                else:
                    print(f"忽略无效边（缺少 source/target）: {edge}")

        # ------------------- 其他情况：提示格式不支持 -------------------
        else:
            raise ValueError(f"不支持的 edges 格式: {type(graph_obj.edges)}，请先确认格式")

        return {"nodes": nodes, "edges": edges}

    # 你可以在这里添加其他服务方法，如运行智能体、处理状态等
    # def run_agent(self, input_message):
    #    ...


    async def broadcast_state(self, state):
        """
        广播智能体状态更新
        """
        # 这里可以集成一个事件总线，或者直接调用回调函数等
        message = {
            "type": "state_update",
            "data": state
        }
        # print("[AgentService] Broadcasting state:", state)

        dead_connections = []
        for ws in list(self.connections):
            try:
                await ws.send_json(message)
            except Exception:
                dead_connections.append(ws)
        for ws in dead_connections:
            self.connections.remove(ws)