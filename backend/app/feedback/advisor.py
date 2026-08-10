import json
import logging
import re

from app.conversations.gemini_client import GeminiClient, GroqClient
from app.conversations.scenarios import get_scenario
from app.core.settings import settings
from app.feedback.rag import RAGService

logger = logging.getLogger(__name__)

_tips_cache: dict[str, list[str]] = {}


def _parse_rag_context(rag_context: str) -> list[dict]:
    chunks = []
    for block in rag_context.split("\n\n---\n\n"):
        lines = block.strip().split("\n")
        if not lines:
            continue
        source = "unknown"
        text_lines = []
        for line in lines:
            if line.startswith("[Source:"):
                source = line.replace("[Source:", "").replace("]", "").strip()
            else:
                text_lines.append(line)
        text = " ".join(text_lines).strip()
        if text:
            chunks.append({"source": source, "text": text})
    return chunks


class ResearchAdvisor:
    def __init__(self, ai_service=None, rag: RAGService | None = None):
        self.ai_service = ai_service
        self.rag = rag or RAGService()

    def _get_ai_service(self):
        if self.ai_service is not None:
            return self.ai_service
        if settings.GROQ_API_KEY:
            self.ai_service = GroqClient()
        elif settings.GEMINI_API_KEY:
            self.ai_service = GeminiClient()
        return self.ai_service

    def suggest(self, scenario: dict, analysis: dict, rag_context: str) -> dict | None:
        chunks = _parse_rag_context(rag_context)
        if not chunks:
            return None

        ai = self._get_ai_service()
        if ai is not None:
            try:
                result = self._suggest_with_llm(scenario, analysis, chunks, ai)
                if result:
                    return result
            except Exception as e:
                logger.warning("LLM suggestions failed, using extractive fallback: %s", e)

        return self._suggest_extractive(analysis, chunks)

    def scenario_tips(self, scenario_id: str, top_k: int = 4) -> list[str] | None:
        cached = _tips_cache.get(scenario_id)
        if cached:
            return list(cached)

        scenario = get_scenario(scenario_id)
        if not scenario:
            return None
        query = f"{scenario.get('name', '')} {scenario.get('goal', '')} {scenario.get('context', '')}"
        chunks = self.rag.retrieve_chunks(query, top_k=top_k * 2, scenario_id=scenario_id)
        if not chunks:
            return None

        ai = self._get_ai_service()
        if ai is not None:
            try:
                tips = self._tips_with_llm(scenario, chunks, ai, top_k)
                if tips:
                    _tips_cache[scenario_id] = list(tips)
                    return tips
            except Exception as e:
                logger.warning("LLM tips failed, using extractive fallback: %s", e)

        tips = self._tips_extractive(chunks, top_k)
        if tips:
            _tips_cache[scenario_id] = list(tips)
        return tips

    def _suggest_with_llm(self, scenario: dict, analysis: dict, chunks: list[dict], ai) -> dict | None:
        weaknesses = analysis.get("weaknesses", []) or []
        strengths = analysis.get("strengths", []) or []
        excerpts = "\n\n".join(f"[Source: {c['source']}]\n{c['text']}" for c in chunks)

        prompt = f"""You are a communication coach grounded in research. A user practiced the "{scenario.get('name')}" scenario.

Detected weaknesses: {', '.join(weaknesses) or 'none'}
Detected strengths: {', '.join(strengths) or 'none'}

Research excerpts:
{excerpts}

Using ONLY the research excerpts, produce actionable feedback as JSON with exactly this shape:
{{
  "recommendations": ["..."],
  "suggested_responses": [{{"weakness": "...", "response": "..."}}]
}}

Each recommendation must be grounded in the excerpts. Each suggested response is a concrete sentence the user could have said, tied to one weakness. Do not cite sources. Return only the JSON object."""
        raw = ai.generate(prompt)
        data = _extract_json_object(raw)
        if not data:
            return None
        suggested = []
        for resp in data.get("suggested_responses", []) or []:
            if not isinstance(resp, dict):
                continue
            suggested.append({
                "weakness": resp.get("weakness", ""),
                "response": resp.get("response", ""),
            })
        return {
            "recommendations": data.get("recommendations", []) or [],
            "suggested_responses": [s for s in suggested if s["response"]],
        }

    def _suggest_extractive(self, analysis: dict, chunks: list[dict]) -> dict:
        weaknesses = analysis.get("weaknesses", []) or []
        recommendations = []
        suggested_responses = []
        for i, chunk in enumerate(chunks[:4]):
            snippet = _first_sentences(chunk["text"], 2)
            if not snippet:
                continue
            recommendations.append(snippet)
            if weaknesses:
                weakness = weaknesses[i % len(weaknesses)]
                suggested_responses.append({
                    "weakness": weakness,
                    "response": f"Ground your next answer in this finding: \"{snippet}\"",
                })
        if not recommendations:
            return None
        return {
            "recommendations": recommendations,
            "suggested_responses": suggested_responses,
        }

    def _tips_with_llm(self, scenario: dict, chunks: list[dict], ai, top_k: int) -> list[str] | None:
        excerpts = "\n\n".join(f"[Source: {c['source']}]\n{c['text']}" for c in chunks)
        prompt = f"""You are a communication coach. Using ONLY the research excerpts below, write {top_k} concise, actionable tips to succeed in this scenario.

Scenario: {scenario.get('name')}
Goal: {scenario.get('goal')}
Situation: {scenario.get('context')}

Research excerpts:
{excerpts}

Return only a JSON array of {top_k} strings, each a short actionable tip grounded in the excerpts."""
        raw = ai.generate(prompt)
        data = _extract_json_array(raw)
        if not data:
            return None
        tips = [str(t).strip() for t in data if str(t).strip()]
        return tips[:top_k] or None

    def _tips_extractive(self, chunks: list[dict], top_k: int) -> list[str]:
        tips = []
        for chunk in chunks[:top_k]:
            snippet = _first_sentences(chunk["text"], 1)
            if snippet:
                tips.append(snippet)
        return tips or None


def _extract_json_object(raw: str) -> dict | None:
    try:
        cleaned = _strip_code_fences(raw)
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end <= start:
            return None
        data = json.loads(cleaned[start:end + 1])
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _extract_json_array(raw: str) -> list | None:
    try:
        cleaned = _strip_code_fences(raw)
        start = cleaned.find("[")
        end = cleaned.rfind("]")
        if start == -1 or end <= start:
            return None
        data = json.loads(cleaned[start:end + 1])
        return data if isinstance(data, list) else None
    except Exception:
        return None


def _strip_code_fences(raw: str) -> str:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _first_sentences(text: str, count: int) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    keep = []
    for p in parts:
        keep.append(p.strip())
        if len(keep) >= count:
            break
    return " ".join(keep)[:300]
