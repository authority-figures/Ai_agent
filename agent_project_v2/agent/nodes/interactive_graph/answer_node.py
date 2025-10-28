
from agent_project_v2.agent.nodes.interactive_graph.state import OverallState
from agent_project_v2.agent.utils import ColorPrinter
from agent_project_v2.agent.nodes.node_publisher import send_state


color_printer = ColorPrinter()


def answer_node(state: OverallState):
    messages = state.get("messages", [])
    AI_answer = state.get("AI_answer", "")
    action_result = state.get("action_result", [])
    input_text = state.get("input", "")

    # 这里可以调用你的语言模型来生成回答
    answer = f"{AI_answer}"

    send_state("answer_node", {"status": "running", "content": AI_answer})
    color_printer.llm_output(f"AI回答: {answer}")