from groq import Groq
from app.utils.config import settings

class GroqClient:
    def __init__(self):
        if not settings.GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY is not set in environment (.env)")
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.chat = self.client.chat

    def __getattr__(self, name: str):
        """Forward unknown attributes to the underlying Groq client."""
        return getattr(self.client, name)

    def generate_json(self, prompt: str) -> str:
        """
        Sends the prompt to the model and returns the raw text output.
        (We parse JSON in the agent layer).
        """
        resp = self.client.chat.completions.create(
            model=settings.MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are an assistant that outputs valid JSON instructions."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=800,
        )

        content = resp.choices[0].message.content.strip()
        return content

groq_client = GroqClient()