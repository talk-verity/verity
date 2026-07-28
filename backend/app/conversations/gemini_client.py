import logging
import random
import re

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


_PATTERNS: list = [
    (r"\b(project|built|build|create|made|developed)\b", "project"),
    (r"\b(startup|company|venture|business)\b", "startup"),
    (r"\b(learn|study|course|teach|mentor|grow)\b", "learning"),
    (r"\b(help|advice|suggest|recommend|opinion)\b", "advice"),
    (r"\b(problem|issue|bug|error|fail|challenge|hard)\b", "challenge"),
    (r"\b(team|manager|boss|colleague|coworker|peer)\b", "team"),
    (r"\b(hire|job|role|position|interview|promotion)\b", "career"),
    (r"\b(difficult|tough|struggle|stress|pressure)\b", "difficulty"),
    (r"\b(great|awesome|amazing|excellent|wonderful)\b", "positive"),
    (r"\b(interesting|curious|tell me more|explain)\b", "curious"),
    (r"\b(thank|appreciate|grateful)\b", "thanks"),
    (r"\byes\b|\bagree\b|\bright\b", "agree"),
    (r"\bno\b|\bdisagree\b|\bwrong\b|\bdifferent\b", "disagree"),
    (r"\?", "question"),
]


def _categorize(msg: str) -> str:
    for pattern, category in _PATTERNS:
        if re.search(pattern, msg.lower()):
            return category
    return "general"


# Response templates keyed by category — each returns a response given persona & user message
def _respond(category: str, persona_name: str, user_msg: str, context: str) -> str:
    templates = _TEMPLATES.get(category, _TEMPLATES["general"])(persona_name, user_msg, context)
    return _pick(templates)


def _pick(options: list[str]) -> str:
    return random.choice(options)


# Each template function receives persona_name and user_msg
_TEMPLATES = {
    "project": lambda p, u, c: [
        f"That sounds like a meaningful project. What was the most important lesson you took away from building it?",
        f"I love hearing about personal projects. What tech stack did you use for it?",
        f"That's impressive. How did you get started with it, and what kept you motivated?",
        f"What impact has that project had on you or the people using it?",
    ],
    "startup": lambda p, u, c: [
        f"A startup — that takes courage. What problem are you trying to solve?",
        f"Exciting! What stage are you at — still building or already live with users?",
        f"I admire the hustle. What's been the hardest part so far?",
        f"That's inspiring. How are you thinking about finding your first customers?",
    ],
    "learning": lambda p, u, c: [
        f"That's a great mindset. How do you usually go about learning something new?",
        f"Continuous learning is so important. What's one thing you've learned recently that changed your perspective?",
        f"I respect that. Do you prefer learning by doing, or do you study theory first?",
        f"What resources have you found most helpful for growing your skills?",
    ],
    "advice": lambda p, u, c: [
        f"Here's my take — I think the most important thing is to stay curious and keep shipping. What specific area are you looking for advice on?",
        f"From my experience, the best advice is to focus on the user and iterate quickly. Does that resonate with you?",
        f"I'd say don't be afraid to ask for help early. What's the specific challenge you're facing?",
    ],
    "challenge": lambda p, u, c: [
        f"Challenges are where we grow the most. How did you end up solving it?",
        f"That sounds tough. What did you learn from going through it?",
        f"I've faced similar situations before. The key is to break it down into smaller pieces. What part was the hardest?",
        f"Resilience is everything. How are you approaching the situation now?",
    ],
    "team": lambda p, u, c: [
        f"Team dynamics can be complex. How are you handling communication across the group?",
        f"That's relatable. What do you think makes a team truly effective?",
        f"I've found that clear ownership and trust are the foundation of good teamwork. How does your team handle that?",
    ],
    "career": lambda p, u, c: [
        f"That's a big step. What excites you most about this opportunity?",
        f"Career moves are always interesting. What factors are you weighing in your decision?",
        f"I've been through similar transitions. The key is finding somewhere your values align. What matters most to you?",
    ],
    "difficulty": lambda p, u, c: [
        f"I hear you. It's normal to feel that way in challenging situations. What would help right now?",
        f"Those moments are tough but they often lead to the most growth. How are you coping?",
        f"Remember that every successful person has been through difficult periods. What's one small step you can take today?",
    ],
    "positive": lambda p, u, c: [
        f"That's wonderful to hear! What do you think contributed most to that success?",
        f"I love that energy. How do you plan to build on that momentum?",
        f"Celebrating wins is important. What's next on your list?",
    ],
    "curious": lambda p, u, c: [
        f"I'm glad you're curious! What specifically would you like to know more about?",
        f"Curiosity is the best trait you can have. What sparked your interest in this?",
        f"That's exactly the right question to ask. Here's what I think — the key is to start small and experiment.",
    ],
    "thanks": lambda p, u, c: [
        f"You're welcome! I'm happy to chat anytime.",
        f"Of course! This is exactly the kind of conversation I enjoy.",
        f"Anytime! Let me know if you have more questions.",
    ],
    "agree": lambda p, u, c: [
        f"Great, we're on the same page then. Where would you like to go from here?",
        f"I'm glad we agree. What do you think the next step should be?",
        f"Perfect. I think this alignment is a great starting point for a deeper conversation.",
    ],
    "disagree": lambda p, u, c: [
        f"That's fair — differing perspectives make conversations productive. Can you tell me more about your viewpoint?",
        f"I respect that you see it differently. What brought you to that conclusion?",
        f"Interesting. I'd love to understand your reasoning better. What evidence or experience shaped that view?",
    ],
    "question": lambda p, u, c: [
        f"Great question. Here's my perspective — I think the most important thing is to stay focused on what you can control and keep moving forward.",
        f"That's a smart thing to ask. Based on my experience, it really depends on your specific context and goals. What's driving the question?",
        f"I'm glad you asked. The way I see it, there's no one right answer — it's about finding what works for you. What have you tried so far?",
    ],
    "general": lambda p, u, c: [
        f"That's really helpful context, thank you for sharing. How long have you been thinking about this?",
        f"I appreciate you being open about that. What do you hope to get out of this conversation?",
        f"Thanks for explaining that. Can you tell me more about what led you to that conclusion?",
        f"That makes sense. How does that connect to what you're hoping to achieve?",
    ],
}


class GroqClient(AIService):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        from groq import Groq
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.GROQ_MODEL
        self._client = Groq(api_key=self.api_key)

    def generate(self, prompt: str) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.warning("Groq API call failed (attempt 1/2): %s", e)
            try:
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.choices[0].message.content
            except Exception as e2:
                logger.error("Groq API call failed (attempt 2/2): %s", e2)
                raise


class MockAIService(AIService):
    def generate(self, prompt: str) -> str:
        name = self._extract_name(prompt)
        msg = self._extract_last_message(prompt)
        context = self._extract_context(prompt)
        category = _categorize(msg)
        return _respond(category, name, msg, context)

    def _extract_name(self, prompt: str) -> str:
        m = re.search(r"^You are (\w+)", prompt)
        return m.group(1) if m else ""

    def _extract_last_message(self, prompt: str) -> str:
        for line in reversed(prompt.split("\n")):
            if line.startswith("User:"):
                return line[len("User:"):].strip()
        return ""

    def _extract_context(self, prompt: str) -> str:
        m = re.search(r"Context: (.+)", prompt)
        return m.group(1) if m else ""
