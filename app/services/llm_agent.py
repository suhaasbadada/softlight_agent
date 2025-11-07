import json
import re
from app.utils.groq_client import groq_client
from app.utils.config import settings

class LLMAgent:
    def __init__(self):
        self.client = groq_client

    def generate_steps(self, app: str, instruction: str):
        prompt = f"""
        You are an automation planner.
        Convert the following instruction for the app "{app}" 
        into a JSON list of step dictionaries.

        Each step must have:
        - action: one of [click, fill, press, navigate, wait, drag, hover]
        - selector_hint: a simple text hint (like 'Settings icon', 'New Page button')
        - description: short explanation of the step
        - value: optional (for text input or key presses)
        
        Example:
        Instruction: Create a new page in Notion
        Output:
        [
          {{"action":"click", "selector_hint":"New Page button", "description":"Open new page"}},
          {{"action":"fill", "selector_hint":"Page title input", "value":"Untitled", "description":"Enter a title"}},
          {{"action":"press", "selector_hint":"Enter key", "value":"Enter", "description":"Confirm creation"}}
        ]
        
        Now respond for:
        App: {app}
        Instruction: {instruction}
        Output only valid JSON list (no text outside the list).
        """

        response = self.client.chat.completions.create(
            model=settings.MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=400
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
                return steps
            else:
                print("Model returned non-list structure")
                return []
        except json.JSONDecodeError as e:
            print("JSON parse error:", e)
            print("Raw JSON:", json_str)
            return []

llm_agent = LLMAgent()