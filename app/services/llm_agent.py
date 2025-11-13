import json
import re
from app.utils.groq_client import groq_client
from app.utils.config import settings

class LLMAgent:
    def __init__(self):
        self.client = groq_client

class LLMAgent:
    def __init__(self):
        self.client = groq_client

    def generate_steps(self, app: str, instruction: str):
        notion_knowledge = """
        NOTION UI KNOWLEDGE:
        - To create ANYTHING (page/database): Click the More Options button, next to username
        - After clicking it: Choose "Page" for new page OR "Database" for new database
        - For database: Click "Database" → Choose "New database" → Fill the title field
        - Settings/Theme: Click "Settings & members" → "Settings" → "Appearance" → Toggle theme
        - Date & Time Settings: Click "Settings & members" → "Settings" → "Date & time" → Toggle "Start week on Monday"
        - Search: Click "Search" or "Quick Find" field in sidebar
        
        CRITICAL: The More Options (looks like a v) button is the MAIN creation button, NOT the small "+ New" button
        """

        prompt = f"""
        You are an expert Notion automation planner. You know the EXACT UI structure of Notion.

        {notion_knowledge}
        
        Convert this instruction into precise, executable steps using EXACT Notion UI elements:
        
        App: {app}
        Instruction: {instruction}
        
        CRITICAL: Use ONLY these exact Notion UI element names:
        - "v" button (More Options) (MAIN creation button in sidebar - three dots with V arrow)
        - "Page" option (in the v menu)
        - "Database" option (in the v menu) 
        - "New database" button (after selecting Database)
        - "Untitled" field (for page/database titles)
        - "Settings & members" button
        - "Settings" option 
        - "Appearance" option
        - "Date & time" option
        - "Start week on Monday" toggle
        - "Dark mode" toggle
        - "Light mode" toggle
        - "Search" or "Quick Find" field
        
        IMPORTANT: For creating database, use EXACTLY these steps:
        [
        {{
            "action": "click",
            "selector_hint": "More Options (v shaped button)",
            "description": "Open main creation menu",
            "value": null,
            "url": null
        }},
        {{
            "action": "click", 
            "selector_hint": "Database",
            "description": "Select database type",
            "value": null,
            "url": null
        }},
        {{
            "action": "click",
            "selector_hint": "New database", 
            "description": "Create new database",
            "value": null,
            "url": null
        }},
        {{
            "action": "fill",
            "selector_hint": "Untitled",
            "description": "Name the database",
            "value": "DATABASE_NAME",
            "url": null
        }}
        ]
        
        Now generate steps for: "{instruction}"
        
        Output ONLY valid JSON array with exact Notion UI elements.
        """

        response = self.client.chat.completions.create(
            model=settings.MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=500
        )

        raw_output = response.choices[0].message.content.strip()

        match = re.search(r'\[.*\]', raw_output, re.DOTALL)
        if match:
            json_str = match.group(0)
        else:
            json_str = raw_output

        try:
            steps = json.loads(json_str)
            if isinstance(steps, list):
                validated_steps = []
                for step in steps:
                    if not isinstance(step, dict):
                        continue
                    validated_step = {
                        "action": step.get("action", ""),
                        "selector_hint": step.get("selector_hint", ""),
                        "description": step.get("description", ""),
                        "value": step.get("value"),
                        "url": step.get("url")
                    }
                    validated_steps.append(validated_step)
                return validated_steps
            else:
                print("Model returned non-list structure")
                return []
                
        except json.JSONDecodeError as e:
            print("JSON parse error:", e)
            print("Raw JSON:", json_str)
            return []

    async def analyze_page_and_generate_steps(self, app: str, instruction: str, page_context: dict = None):
        print(f"Generating steps for: {app} - {instruction}")
        if page_context:
            print(f"Page context available: {page_context.get('url', 'No URL')}")

        return self.generate_steps(app, instruction)

    async def generate_steps_direct_test(self, app: str, instruction: str, page_context: dict = None):
        steps = await self.analyze_page_and_generate_steps(app, instruction, page_context)
        return {
            "raw_output": "See server logs",
            "parsed_steps": steps,
            "prompt_used": f"Simple prompt for {app} - {instruction}",
            "page_context": page_context or {}
        }

    def _build_context_description(self, page_context: dict) -> str:
        if not page_context:
            return "No page context"
        return f"URL: {page_context.get('url', 'Unknown')}, Title: {page_context.get('title', 'Unknown')}"

    def _parse_json_response(self, raw_output: str):
        return self.generate_steps("temp", "temp")

llm_agent = LLMAgent()