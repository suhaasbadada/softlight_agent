from pydantic import BaseModel

class TaskRequest(BaseModel):
    app: str
    instruction: str

class TaskResponse(BaseModel):
    status: str
    app: str
    instruction: str