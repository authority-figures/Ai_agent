
from agent_project_v2.agent.nodes.interactive_graph.state import OverallState
from agent_project_v2.agent.utils import ColorPrinter
from agent_project_v2.agent.nodes.node_publisher import send_state
from agent.utils import ColorPrinter
import time

color_printer = ColorPrinter()


def answer_node(state: OverallState):
    time_ = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    ColorPrinter.debug_normal(f"[interactive answer_node] |{time_}|进入interactive answer_node节点", color="green")
    messages = state.get("messages", [])
    AI_answer = state.get("AI_answer", "")
    action_result = state.get("action_result", [])
    input_text = state.get("input", "")

    # 这里可以调用你的语言模型来生成回答
    answer = f"{AI_answer}"

    send_state("answer_node", {"status": "running", "content": AI_answer})
    if state.get("finished_task_id", None):
        send_state("finished_task", {"status": "running", "content": AI_answer})

    color_printer.llm_output(f"AI回答: {answer}")
    time_ = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    ColorPrinter.debug_normal(f"[interactive answer_node] |{time_}|离开interactive answer_node节点", color="green")
    return {"finished_task_id":None}