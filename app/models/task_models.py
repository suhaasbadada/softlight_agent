from pydantic import BaseModel
from typing import List, Optional

class Step(BaseModel):
    action: str
    selector_hint: Optional[str] = None
    description: str
    value: Optional[str] = None
    url: Optional[str] = None
    screenshot_path: Optional[str] = None

class TaskRequest(BaseModel):
    app: str
    instruction: str

class TaskResponse(BaseModel):
    status: str
    app: str
    instruction: str
    steps: List[Step]