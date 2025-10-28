from langchain.tools import tool  # ✅ 直接使用装饰器

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