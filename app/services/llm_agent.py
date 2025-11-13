import json
import re
from app.utils.groq_client import groq_client
from app.utils.config import settings

class LLMAgent:
    def __init__(self):
        self.client = groq_client

    def generate_steps(self, app: str, instruction: str):
        notion_knowledge = """
        NOTION UI KNOWLEDGE:
        - To create database: Click "New" button → Click "Database" option → Click "New database" → Fill title field
        - Settings/Theme: Click "Settings & members" → "Settings" → "Appearance" → Toggle theme
        - Date & Time Settings: Click "Settings & members" → "Settings" → "Date & time" → Toggle "Start week on Monday"
        - New page: Click "New" button → "Page" option → Fill title field
        - Search: Click "Search" or "Quick Find" field in sidebar
        
        IMPORTANT: For "Start week on Monday" use EXACTLY these steps:
        1. Click "Settings & members"
        2. Click "Settings" 
        3. Click "Date & time"
        4. Click "Start week on Monday"
        
        IMPORTANT: For creating database use EXACTLY these steps:
        1. Click "New"
        2. Click "Database"
        3. Click "New database" 
        4. Fill "Untitled" with database name
        """

        prompt = f"""
        You are an expert Notion automation planner. Convert this instruction into precise, executable steps.
        
        App: {app}
        Instruction: {instruction}
        
        {notion_knowledge}
        
        Use ONLY these exact Notion UI element names:
        - "New" button (for creating anything new)
        - "Database" option (in the New menu) 
        - "Page" option (in the New menu)
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
        
        CRITICAL RULES:
        1. Generate ONLY the steps needed to complete the instruction
        2. Do NOT add extra steps or repeat actions
        3. For toggle actions, perform exactly ONE click
        4. For fill actions, use the full text at once (not character by character)
        5. Stop after the main action is completed
        
        Example for "Toggle 'Start week on Monday'":
        [
        {{
            "action": "click",
            "selector_hint": "Settings & members", 
            "description": "Open settings menu",
            "value": null,
            "url": null
        }},
        {{
            "action": "click",
            "selector_hint": "Settings",
            "description": "Open settings",
            "value": null,
            "url": null
        }},
        {{
            "action": "click",
            "selector_hint": "Date & time",
            "description": "Open date and time settings", 
            "value": null,
            "url": null
        }},
        {{
            "action": "click",
            "selector_hint": "Start week on Monday",
            "description": "Toggle start week on Monday setting",
            "value": null,
            "url": null
        }}
        ]
        
        Example for "Create database named 'Projects'":
        [
        {{
            "action": "click",
            "selector_hint": "New",
            "description": "Open new item menu",
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
            "value": "Projects",
            "url": null
        }}
        ]
        
        Now generate steps for: "{instruction}"
        
        Output ONLY valid JSON array. Do not add explanations.
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