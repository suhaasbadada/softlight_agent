from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/tasks", tags=["Tasks"])

class TaskRequest(BaseModel):
    app: str
    instruction: str

@router.post("/run")
async def run_task(request: TaskRequest):
    return {
        "status": "Task received",
        "app": request.app,
        "instruction": request.instruction
    }