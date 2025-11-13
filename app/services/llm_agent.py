import json
import re
from app.utils.groq_client import groq_client
from app.utils.config import settings

class LLMAgent:
    def __init__(self):
        self.client = groq_client

    def generate_steps(self, app: str, instruction: str):
        # Notion-specific knowledge base
        notion_knowledge = """
                NOTION UI KNOWLEDGE:
                - To create database: Click "New" button → Click "Database" option → Click "New database" → Fill title field
                - Settings/Theme: Click "Settings & members" → "Settings" → "Appearance" → Toggle theme
                - New page: Click "New" button → "Page" option → Fill title field
                - Search: Click "Search" or "Quick Find" field in sidebar
        """
        
        prompt = f"""
        You are an expert Notion automation planner. You know the exact UI structure of Notion.
        
        {notion_knowledge}
        
        Convert this instruction into precise, executable steps using EXACT Notion UI elements:
        
        App: {app}
        Instruction: {instruction}
        
        CRITICAL: Use ONLY these exact Notion UI element names:
        - "New" button (for creating anything new)
        - "Database" option (in the New menu) 
        - "Page" option (in the New menu)
        - "New database" button (after selecting Database)
        - "Untitled" field (for page/database titles)
        - "Settings & members" button
        - "Settings" option 
        - "Appearance" option
        - "Dark mode" toggle
        - "Light mode" toggle
        - "Search" or "Quick Find" field
        
        Example for creating database:
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
            "value": "My Database",
            "url": null
        }}
        ]
        
        Example for theme toggle:
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
            "selector_hint": "Appearance",
            "description": "Open appearance settings",
            "value": null, 
            "url": null
        }},
        {{
            "action": "click", 
            "selector_hint": "Dark mode",
            "description": "Toggle theme mode",
            "value": null,
            "url": null
        }}
        ]
        
        Now generate steps for: {instruction}
        
        Output ONLY valid JSON array with exact Notion UI elements.
        """

        response = self.client.chat.completions.create(
            model=settings.MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,  # Lower temperature for more consistent results
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
                # Ensure all steps have the required fields
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
        """
        This is the function that capture_service.py calls
        We'll use page_context if available, but fall back to the simple generator
        """
        print(f"Generating steps for: {app} - {instruction}")
        if page_context:
            print(f"Page context available: {page_context.get('url', 'No URL')}")

        return self.generate_steps(app, instruction)

    async def generate_steps_direct_test(self, app: str, instruction: str, page_context: dict = None):
        """For debug endpoints"""
        steps = await self.analyze_page_and_generate_steps(app, instruction, page_context)
        return {
            "raw_output": "See server logs",
            "parsed_steps": steps,
            "prompt_used": f"Simple prompt for {app} - {instruction}",
            "page_context": page_context or {}
        }

    def _build_context_description(self, page_context: dict) -> str:
        """Simple context description for compatibility"""
        if not page_context:
            return "No page context"
        return f"URL: {page_context.get('url', 'Unknown')}, Title: {page_context.get('title', 'Unknown')}"

    def _parse_json_response(self, raw_output: str):
        """Compatibility method"""
        return self.generate_steps("temp", "temp")

llm_agent = LLMAgent()