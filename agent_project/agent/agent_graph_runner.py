from graph.main_graph import graph
import langchain
from langgraph.graph.message import Messages
from agent_project.agent.messages.myMessages import SimpleMessages
langchain.debug = True


# ✅ 运行任务流，传递 `State`
result = graph.invoke({
    "input":"请在仿真环境中加载机械臂，文件路径为`F:\\sw\\urdf_files\\minicobo_v1.4\\urdf\\minicobo_v1.4.urdf`，然后移动机械臂末端到 (0.5, 0.3, 0.2) 位置，姿态为（0,0,0,1)，然后创建一个红色方块。",
    "action_result": [],  # ✅ 让任务状态保持在 LLM 记忆中
    "messages": SimpleMessages(),
})

print("\n🔹 LangGraph 执行结果：", result)
