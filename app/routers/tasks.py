from fastapi import APIRouter, HTTPException
from app.models.task_models import TaskRequest, TaskResponse
from app.services.task_service import task_service

router = APIRouter(prefix="/tasks", tags=["Tasks"])

@router.post("/run", response_model=TaskResponse)
async def run_task(request: TaskRequest):
    if not request.app or not request.instruction:
        raise HTTPException(status_code=400, detail="Both 'app' and 'instruction' are required.")

    result = await task_service.process_task(request.app, request.instruction)
    return result