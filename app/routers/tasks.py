from fastapi import APIRouter
from pydantic import BaseModel
from app.models.task_models import TaskRequest

router = APIRouter(prefix="/tasks", tags=["Tasks"])

@router.post("/run")
async def run_task(request: TaskRequest):
    return {
        "status": "Task received",
        "app": request.app,
        "instruction": request.instruction
    }