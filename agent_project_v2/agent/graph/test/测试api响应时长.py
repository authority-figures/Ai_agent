
from agent_project_v2.agent.llm import chatGPT_llm
from langchain.tools import tool  # ✅ 直接使用装饰器
# from langgraph.prebuilt.tool_executor import ToolExecutor,ToolInvocation
from langgraph.prebuilt import ToolNode, ToolInvocation
from agent_project_v2.agent.utils import ColorPrinter
from langgraph.checkpoint.memory import InMemorySaver

import time

# memory = SqliteSaver.from_conn_string("agent_memory.db")
memory = InMemorySaver()
color_printer = ColorPrinter()

@tool
def get_robot_end_pos_and_ori(description,robot_id):
    """
    获取机械臂末端位置。

    参数:
    - description (str): 对任务的详细复述,包含输入的参数
    - robot_id (int): 机械臂的 ID

    返回:
    - dict: API 响应数据，包含 `status`、`end_pos` 和 `end_ori`
    """

    try:
        result = {"end_pos": [0.5, 0.3, 0.2], "end_ori": [0, 0, 0, 1]}
        return {"status": "success", "message": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


llm = chatGPT_llm(model_name="gpt-4o-mini",temperature=0)
llm_with_tools = llm.bind_tools([get_robot_end_pos_and_ori])
tool_executor = ToolNode(tools=[get_robot_end_pos_and_ori])

time_1 = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
llm_output = llm_with_tools.invoke("请帮我编写一段关于机械臂的操作规范手册，100词左右")
time_2 = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

color_printer.llm_output(llm_output.content)
print(f"LLM调用开始时间: {time_1}, 结束时间: {time_2},Cost time: {time_2 - time_1}")



