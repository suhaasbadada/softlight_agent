from fastapi import APIRouter
from playwright.async_api import async_playwright
import os

router = APIRouter(prefix="/debug", tags=["Debug"])
@router.post("/test-llm-detailed")
async def test_llm_detailed(request: dict):
    """Comprehensive LLM testing with full output"""
    from app.services.llm_agent import llm_agent
    
    app = request.get("app", "Notion")
    instruction = request.get("instruction", "Create a new database")
    page_context = request.get("page_context", {})
    
    try:
        result = await llm_agent.generate_steps_direct_test(app, instruction, page_context)
        return {
            "status": "success",
            "app": app,
            "instruction": instruction,
            "result": result
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "app": app,
            "instruction": instruction
        }