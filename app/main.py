from fastapi import FastAPI
from app.routers import tasks, debug
app = FastAPI(
    title="Softlight Agent",
    description="Captures UI states in real time.",
    version="1.0.0"
)

app.include_router(tasks.router)
app.include_router(debug.router)

@app.get("/")
async def root():
    return {"message": "running"}