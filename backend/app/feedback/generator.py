import json
import logging

from app.feedback.schemas import FeedbackAnalysis

logger = logging.getLogger(__name__)


class FeedbackGenerator:
    def generate(
        self,
        analysis: dict,
        scenario_name: str,
        persona_name: str,
        rag_context: str = "",
        suggestions: dict | None = None,
        timed_out: bool = False,
    ) -> str:
        timed_out = timed_out or bool(analysis.get("timed_out"))
        score = analysis.get("overall_score", 0)
        strengths = analysis.get("strengths", [])
        weaknesses = analysis.get("weaknesses", [])
        goal = analysis.get("goal_completion", "unknown")

        recommendations = self._build_recommendations(analysis, timed_out=timed_out)
        suggested_responses = None
        if suggestions:
            if suggestions.get("recommendations"):
                recommendations = suggestions["recommendations"]
            if suggestions.get("suggested_responses"):
                suggested_responses = suggestions["suggested_responses"]

        report = {
            "scenario": scenario_name,
            "persona": persona_name,
            "overall_score": score,
            "assessment_method": analysis.get("assessment_method", "legacy_heuristic"),
            "assessment_note": analysis.get("assessment_note", "Legacy heuristic feedback; not a validated assessment."),
            "timed_out": timed_out,
            "time_limit_seconds": 300,
            "rubric_observations": analysis.get("rubric_observations", []),
            "summary": self._build_summary(score, goal, timed_out=timed_out),
            "metrics": {
                "confidence": analysis.get("confidence_score", 0),
                "clarity": analysis.get("clarity_score", 0),
                "filler_word_count": analysis.get("filler_word_count", 0),
                "filler_words": analysis.get("filler_words", []),
                "total_turns": analysis.get("total_turns", 0),
                "total_user_words": analysis.get("total_user_words", 0),
                "avg_response_length": analysis.get("avg_response_length", 0),
            },
            "goal_completion": goal,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "recommendations": recommendations,
        }

        if analysis.get("transcript_examples"):
            report["transcript_examples"] = analysis["transcript_examples"]

        if rag_context:
            references = self._extract_references(rag_context)
            report["references"] = references

        if suggested_responses:
            report["suggested_responses"] = suggested_responses

        return json.dumps(report, indent=2)

    def _extract_references(self, rag_context: str) -> list[dict]:
        refs = []
        for block in rag_context.split("\n\n---\n\n"):
            lines = block.strip().split("\n")
            if not lines:
                continue
            source = "unknown"
            text = block
            for line in lines:
                if line.startswith("[Source:"):
                    source = line.replace("[Source:", "").replace("]", "").strip()
                    text = "\n".join(lines[1:])
            refs.append({"source": source, "snippet": text[:200]})
        return refs

    def _build_summary(self, score, goal: str, timed_out: bool = False) -> str:
        if timed_out:
            return "The 5-minute time limit expired before the conversation objective was completed. Review your transcript cues below to identify where pacing and concise communication can help you achieve your goals within the time window."
        return "Review the transcript observations below, then choose one skill to practice again. Goal achievement and communication quality require review in context."

    def _build_recommendations(self, analysis: dict, timed_out: bool = False) -> list[str]:
        recs = []
        if timed_out or analysis.get("timed_out"):
            recs.append("Practice pacing: with a 5-minute time limit, aim to establish your key points early so you have time to address the scenario objective before time runs out.")
        for item in analysis.get("rubric_observations", []):
            if not item["observed"]:
                recs.append(f"Review '{item['criterion']}' in your transcript. No matching text cue was found; this does not prove it was absent.")
        if analysis.get("filler_word_count", 0) > 3:
            recs.append("Listen back for repeated filler sounds and consider a pause where it helps your meaning.")
        recs.extend(["Compare your answer with the scenario goal and identify one concrete next step.",
                     "Practice again, focusing on one specific change rather than a numerical score."])
        return recs[:5]
