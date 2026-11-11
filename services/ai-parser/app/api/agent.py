from fastapi import APIRouter

from app.parsing.agent import agent_step
from app.schemas.agent import AgentStepRequest, AgentStepResponse

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/step", response_model=AgentStepResponse)
async def step(body: AgentStepRequest) -> AgentStepResponse:
    return await agent_step(body)
