from app.models.task_models import TaskResponse, Step
from app.services.capture_service import capture_service
from app.services.llm_agent import llm_agent

class TaskService:
    async def process_task(self, app: str, instruction: str) -> TaskResponse:
        steps_raw = llm_agent.generate_steps(app, instruction)
        
        steps_captured = await capture_service.execute_steps(app, instruction)
        
        normalized_steps = [Step(**s) for s in steps_captured]

        return TaskResponse(
            status="completed",
            app=app,
            instruction=instruction,
            steps=normalized_steps
        )
task_service = TaskService()