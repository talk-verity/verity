import logging

from app.core.settings import settings

logger = logging.getLogger(__name__)


class AIService:
    def generate(self, prompt: str) -> str:
        raise NotImplementedError


class GeminiClient(AIService):
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def generate(self, prompt: str) -> str:
        client = self._get_client()
        try:
            response = client.models.generate_content(model=self.model, contents=prompt)
            return response.text
        except Exception as e:
            logger.warning("Gemini API call failed (attempt 1/2): %s", e)
            try:
                response = client.models.generate_content(model=self.model, contents=prompt)
                return response.text
            except Exception as e2:
                logger.error("Gemini API call failed (attempt 2/2): %s", e2)
                raise


class MockAIService(AIService):
    def __init__(self, responses: list[str] | None = None):
        self._call_count = 0
        self._responses = responses or [
            "That's a great question. Let me think about it from my perspective.",
            "I appreciate you bringing that up. Here's what I think we should consider.",
            "Interesting point. I'd like to hear more about your thoughts on this.",
        ]

    def generate(self, prompt: str) -> str:
        response = self._responses[self._call_count % len(self._responses)]
        self._call_count += 1
        return response
