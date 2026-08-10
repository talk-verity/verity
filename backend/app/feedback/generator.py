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
    ) -> str:
        score = analysis.get("overall_score", 0)
        strengths = analysis.get("strengths", [])
        weaknesses = analysis.get("weaknesses", [])
        goal = analysis.get("goal_completion", "unknown")

        recommendations = self._build_recommendations(analysis)
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
            "summary": self._build_summary(score, goal),
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

    def _build_summary(self, score: float, goal: str) -> str:
        if score >= 80:
            return "Strong performance. You communicated effectively and addressed the scenario goals well."
        if score >= 60:
            return "Decent performance with room for improvement in clarity and confidence."
        return "Needs improvement. Focus on reducing filler words and speaking more directly."

    def _build_recommendations(self, analysis: dict) -> list[str]:
        recs = []
        if analysis.get("filler_word_count", 0) > 3:
            recs.append(f"Reduce filler words like '{', '.join(analysis.get('filler_words', [])[:3])}' — pause instead of filling silence.")
        if analysis.get("confidence_score", 100) < 70:
            recs.append("Use fewer hedging words (maybe, I think, I guess). State your points directly.")
        if analysis.get("clarity_score", 100) < 70:
            recs.append("Aim for shorter, more structured sentences. Lead with your main point.")
        if "over-apologizes" in analysis.get("weaknesses", []):
            recs.append("Avoid over-apologizing — replace 'sorry' with 'thank you for your patience'.")
        if not analysis.get("strengths", []):
            recs.append("Ask more questions and provide specific examples to strengthen engagement.")
        if len(recs) < 2:
            recs.append("Keep practicing — each conversation builds your communication skills.")
        return recs
