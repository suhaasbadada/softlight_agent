from pydantic import BaseModel

class TaskRequest(BaseModel):
    app: str
    instruction: str