# api/graph_info.py (或类似名称)
from fastapi import APIRouter, HTTPException, Depends
from agent_project_v2.core.service_locator import ServiceLocator
from agent.services.agent_service import AgentService

router = APIRouter(prefix="/api/graph", tags=["Graph Information"])

def get_agent_service():
    agent_service = ServiceLocator.get('agent_service')
    if agent_service is None:
        raise HTTPException(status_code=500, detail="Agent service not available")
    return agent_service

@router.get("/graph-structure")
async def get_graph_structure(agent_service: AgentService = Depends(get_agent_service)):
    """
    获取Agent图结构的API端点。
    """
    try:
        graph_data = agent_service.get_graph_structure()
        return {
            "status": "success",
            "data": graph_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get graph structure: {str(e)}")

@router.get("/invoke")
async def invoke_graph(user_input: str, agent_service: AgentService = Depends(get_agent_service)):
    """
    调用Agent图的API端点。
    """
    try:
        result = agent_service.invoke_graph(user_input)
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to invoke graph: {str(e)}")
