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
    def analyze(self, scenario_id: str, user_turns: list[str], ai_turns: list[str], timed_out: bool = False) -> dict:
        words = sum(len(t.split()) for t in user_turns)
        fillers = [m.group().lower() for t in user_turns for m in _FILLERS.finditer(t)]
        observations = []
        examples = []
        for label, pattern in RUBRICS.get(scenario_id, []):
            quote = next((t for t in user_turns if re.search(pattern, t, re.I)), None)
            default_interp = "No response was recorded before time expired." if (timed_out and not user_turns) else "Text cue only; review in context."
            observations.append({"criterion": label, "observed": quote is not None,
                                 "quote": quote, "interpretation": default_interp})
            if quote:
                examples.append({"type": "strength", "label": f"{label}: text cue", "quote": quote})

        if timed_out:
            note = "Time limit reached (5:00). You were unable to complete the conversation objective within the allotted 5 minutes."
            goal_completion = "Objective not completed — 5-minute time limit expired"
            weaknesses = ["Time management: The 5-minute session expired before the objective could be completed. Practice pacing your conversation to reach key goals within the time limit."]
        else:
            note = "These are text observations, not validated scores. They do not measure confidence, vocal delivery, or whether your goal was achieved. Transcription may omit filler sounds."
            goal_completion = "Not assessed automatically"
            weaknesses = []

        return {
            "assessment_method": "transcript_observations_v1",
            "assessment_note": note,
            "overall_score": None, "confidence_score": None, "clarity_score": None,
            "interruption_count": None, "goal_completion": goal_completion,
            "timed_out": timed_out, "time_limit_seconds": 300,
            "total_turns": len(user_turns), "total_user_words": words,
            "avg_response_length": round(words / len(user_turns), 1) if user_turns else 0,
            "filler_word_count": len(fillers), "filler_words": sorted(set(fillers)),
            "strengths": [], "weaknesses": weaknesses, "transcript_examples": examples,
            "rubric_observations": observations,
        }
