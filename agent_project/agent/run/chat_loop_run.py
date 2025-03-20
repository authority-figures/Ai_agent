from agent_project.agent.graph.chat_loop_graph import graph
import langchain
from langgraph.graph.message import Messages
from agent_project.agent.messages.myMessages import SimpleMessages
# langchain.debug = True


# # ✅ 运行任务流，传递 `State`
# result = graph.invoke({
#     "input":"请在仿真环境中加载机械臂，文件路径为`F:\\sw\\urdf_files\\minicobo_v1.4\\urdf\\minicobo_v1.4.urdf`，然后创建一个红色方块于(0.5, 0.3, 0.2)处，然后移动机械臂末端到红色方块上方，姿态为(0,0,0,1)。",
# })
#
# print("\n🔹 LangGraph 执行结果：", result)



def chat_loop():
    print("开始对话，输入 'exit'、'end' 或 'quit' 结束")

    while True:
        user_text = input("新的一轮对话开始> ")
        result = graph.invoke({"input": user_text})

        # 检查会话是否已结束
        if result.get("exit_loop", False):
            print("对话结束")
            break

        # 可以在这里处理或显示结果
        print("\n结果:", result.get("action_result", ["无结果"]))
        print("等待下一个指令...\n")


# 启动对话
if __name__ == "__main__":
    chat_loop()