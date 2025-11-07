from typing import List, Dict, Any
from app.models.task_models import TaskResponse, Step
from app.services.llm_agent import llm_agent

class TaskService:
    @staticmethod
    def process_task(app: str, instruction: str) -> TaskResponse:
        steps_raw: List[Dict[str, Any]] = llm_agent.generate_steps(app, instruction)

        normalized_steps = []
        for s in steps_raw:
            try:
                normalized_steps.append(
                    Step(
                        action=s.get("action", "unknown"),
                        selector_hint=s.get("selector_hint", ""),
                        description=s.get("description", "") or s.get("desc", ""),
                        value=s.get("value")
                    )
                )
            except Exception:
                normalized_steps.append(
                    Step(
                        action="unknown",
                        selector_hint="",
                        description=f"Malformed step: {s}",
                        value=None
                    )
                )

        return TaskResponse(
            status="ok",
            app=app,
            instruction=instruction,
            steps=normalized_steps
        )

task_service = TaskService()