"""Conservative transcript observations, not a validated performance assessment."""
import re

# Context-dependent words such as "like", "just", "could" and "sorry" are not
# automatically counted as mistakes. ASR may omit even these vocalizations.
_FILLERS = re.compile(r"\b(?:umm?|uhh?|uhm|erm?)\b", re.I)
RUBRICS = {
    "networking_event": [("Introduction", r"\b(i am|i'm|my name|i work)\b"), ("Follow-up question", r"\?"), ("Next contact", r"\b(connect|contact|email|linkedin|follow up)\b")],
    "job_interview": [("Action described", r"\bi (built|led|created|designed|improved|reduced|shipped)\b"), ("Result mentioned", r"\b(result|outcome|impact|increased|reduced)\b|\d+%"), ("Question asked", r"\?")],
    "promotion_discussion": [("Promotion request", r"\b(promotion|promote|senior|next level)\b"), ("Contribution described", r"\b(led|built|delivered|improved|achieved|achievements)\b"), ("Next steps", r"\b(timeline|criteria|next steps|expectations)\b")],
    "performance_review": [("Contribution described", r"\b(built|led|delivered|improved|achieved)\b"), ("Learning mentioned", r"\b(learned|learning|improve|feedback)\b"), ("Future plan", r"\b(plan|next quarter|goal|next steps)\b")],
    "workplace_conflict": [("Situation described", r"\b(when|happened|situation|noticed)\b"), ("Other perspective invited", r"\?"), ("Proposal mentioned", r"\b(propose|suggest|agree|we could|next steps)\b")],
}

class Analyzer:
    def analyze(self, scenario_id: str, user_turns: list[str], ai_turns: list[str]) -> dict:
        words = sum(len(t.split()) for t in user_turns)
        fillers = [m.group().lower() for t in user_turns for m in _FILLERS.finditer(t)]
        observations = []
        examples = []
        for label, pattern in RUBRICS.get(scenario_id, []):
            quote = next((t for t in user_turns if re.search(pattern, t, re.I)), None)
            observations.append({"criterion": label, "observed": quote is not None,
                                 "quote": quote, "interpretation": "Text cue only; review in context."})
            if quote:
                examples.append({"type": "strength", "label": f"{label}: text cue", "quote": quote})
        return {
            "assessment_method": "transcript_observations_v1",
            "assessment_note": "These are text observations, not validated scores. They do not measure confidence, vocal delivery, or whether your goal was achieved. Transcription may omit filler sounds.",
            "overall_score": None, "confidence_score": None, "clarity_score": None,
            "interruption_count": None, "goal_completion": "Not assessed automatically",
            "total_turns": len(user_turns), "total_user_words": words,
            "avg_response_length": round(words / len(user_turns), 1) if user_turns else 0,
            "filler_word_count": len(fillers), "filler_words": sorted(set(fillers)),
            "strengths": [], "weaknesses": [], "transcript_examples": examples,
            "rubric_observations": observations,
        }
