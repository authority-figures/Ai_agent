from langchain.agents import initialize_agent, AgentType
from tools import *  # ✅ 直接导入封装好的工具
from llm import chatGPT_llm
import requests,json

# 初始化 LLM（使用 OpenAI API 或其他 LLM）
llm = chatGPT_llm(model_name="gpt-4o-mini",temperature=0.1)

# 定义 Agent，让它能调用 `load_robot`
agent = initialize_agent(
    tools=[load_robot,move_robot_to_target,get_robot_end_pos_and_ori,create_cube,get_object_pos_and_ori],  # ✅ 直接传入 `load_robot`
    llm=llm,
    agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
)



response = requests.post('http://127.0.0.1:8000/simulation/create_cube', headers={'Content-Type': 'application/json'}, data=json.dumps(
        {'pos': [0.3, 0, 0.05], 'ori': [0,0,0,1], 'half_extents': [0.05,0.05,0.05],'color':[0,1,0,1]}))
greenBoxID = response.json()['message']['cube_id']
response = requests.post('http://127.0.0.1:8000/simulation/create_cube', headers={'Content-Type': 'application/json'}, data=json.dumps(
        {'pos': [-0.3, 0, 0.05], 'ori': [0,0,0,1], 'half_extents': [0.05,0.05,0.05],'color':[1,0,0,1]}))
redBoxID = response.json()['message']['cube_id']
# 让 Agent 自动调用 `load_robot`
response = agent.invoke(
    {
        "input":f"请使用工具加载机械臂，URDF 文件路径是 F:\\sw\\urdf_files\\minicobo_v1.4\\urdf\\minicobo_v1.4.urdf。仿真环境中，我已经创建好了两个方块，绿色的方块ID为{greenBoxID},红色方块ID为{redBoxID}。请帮我将机械臂末端运动到绿色方块上方，姿态为[1, 0, 0, 0]，确保机器人运动到位后，再帮我将机械臂末端运动到红色方块上方，姿态为[1, 0, 0, 0]，最后再验证机械臂是否运动到位了，并告诉我结果：已到位或未到位"
    }
)
print(response)
