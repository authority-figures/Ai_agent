'''
提供Agent相关服务
负责与langgrain交互
'''

from langgraph.graph import StateGraph
from agent.graph.main_graph import graph as compiled_graph


class AgentService:
    """一个专门用于提供智能体相关功能的服务"""

    def get_graph_structure(self):
        """
        获取LangGraph图的结构化信息。
        返回包含节点和边的字典，便于前端可视化。

        Returns:
            dict: 例如 {'nodes': [...], 'edges': [...]}
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
        for node_name in graph_obj.nodes:
            nodes.append({
                "id": node_name,
                "name": node_name,
                # 可以根据节点类型添加更多属性，如形状、颜色等
                "type": "stateNode" if "state" in node_name.lower() else "actionNode"
            })

        # 2. 根据 edges 实际格式，调整遍历逻辑（重点修改这里）
        # ------------------- 情况1：edges 是“元组列表”（最常见） -------------------
        if isinstance(graph_obj.edges, list) and all(isinstance(edge, tuple) for edge in graph_obj.edges):
            for edge in graph_obj.edges:
                source_node = edge[0]  # 元组第一个元素是起点
                target_node = edge[1]  # 元组第二个元素是终点
                edges.append({"from": source_node, "to": target_node})

        # ------------------- 情况2：edges 是“字典列表”（含 source/target 键） -------------------
        elif isinstance(graph_obj.edges, list) and all(isinstance(edge, dict) for edge in graph_obj.edges):
            for edge in graph_obj.edges:
                # 确保字典有 source 和 target 键（避免键不存在报错）
                if "source" in edge and "target" in edge:
                    source_node = edge["source"]
                    target_node = edge["target"]
                    edges.append({"from": source_node, "to": target_node})
                else:
                    print(f"忽略无效边（缺少 source/target）: {edge}")

        # ------------------- 其他情况：提示格式不支持 -------------------
        else:
            raise ValueError(f"不支持的 edges 格式: {type(graph_obj.edges)}，请先确认格式")

        return {"nodes": nodes, "edges": edges}

    # 你可以在这里添加其他服务方法，如运行智能体、处理状态等
    # def run_agent(self, input_message):
    #    ...