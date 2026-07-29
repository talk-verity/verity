import logging
import re

from app.conversations.scenarios import get_scenario

logger = logging.getLogger(__name__)

_FILLER_WORDS = {
    "um", "uh", "ah", "er", "like", "you know", "actually", "basically",
    "literally", "honestly", "i mean", "sort of", "kind of", "you see",
    "well", "so", "right", "okay", "just",
}

_HEDGING_WORDS = {
    "maybe", "perhaps", "possibly", "probably", "i think", "i guess",
    "i feel", "i believe", "i suppose", "kind of", "sort of",
    "might", "could", "would", "should",
}

_STRENGTH_PATTERNS = [
    (r"\b(i\s+(built|created|led|designed|architected|shipped|launched|grew|improved|optimized|reduced))\b",
     "Uses concrete action verbs to describe achievements"),
    (r"\?\s*$", "Asks thoughtful follow-up questions"),
    (r"\b(thank|appreciate|grateful)\b", "Expresses gratitude and professionalism"),
    (r"\b(we\s+(could|should|might|would))\b", "Shows collaborative problem-solving"),
    (r"\b(specific|example|instance|scenario|situation)\b", "Provides specific examples"),
    (r"\b(i\s+(learned|realized|grew|improved|identified|reflected))\b", "Demonstrates self-awareness and growth mindset"),
    (r"\b(our\s+team|my\s+team|we\s+accomplished)\b", "Shows team-oriented thinking"),
    (r"\b(let me|i'd\s+be\s+happy|i'm\s+open|happy\s+to)\b", "Shows willingness and engagement"),
    (r"\b(clear|concise|straightforward|direct)\b", "Values clarity in communication"),
]

_WEAKNESS_PATTERNS = [
    (r"\b(i\s+dunno|i\s+don't\s+know|not\s+sure|no\s+idea)\b", "Uses uncertain or hedging language"),
    (r"\b(sorry|apologize|my\s+bad)\b", "Over-apologizes"),
    (r"\b(just)\b", "Frequently downplays own contributions with 'just'"),
    (r"\b(i\s+think|i\s+feel|i\s+believe|i\s+guess)\b", "Overuses hedging phrases"),
    (r"\b(actually|basically|literally|honestly)\b", "Overuses filler adverbs"),
]


class Analyzer:
    def analyze(self, scenario_id: str, user_turns: list[str], ai_turns: list[str]) -> dict:
        analysis = {}
        analysis.update(self._count_metrics(user_turns))
        analysis.update(self._analyze_filler_words(user_turns))
        analysis.update(self._analyze_strengths(user_turns))
        analysis.update(self._analyze_weaknesses(user_turns))
        analysis.update(self._calculate_confidence(user_turns))
        analysis.update(self._calculate_clarity(user_turns))
        analysis.update(self._analyze_interruptions(ai_turns, user_turns))
        analysis.update(self._analyze_goal_completion(scenario_id, user_turns, ai_turns))
        analysis.update(self._calculate_overall_score(analysis))
        return analysis

    def _count_metrics(self, user_turns: list[str]) -> dict:
        total_words = sum(len(t.split()) for t in user_turns)
        num_turns = len(user_turns)
        avg_len = round(total_words / num_turns, 1) if num_turns > 0 else 0
        return {
            "total_turns": num_turns,
            "total_user_words": total_words,
            "avg_response_length": avg_len,
        }

    def _analyze_filler_words(self, user_turns: list[str]) -> dict:
        found = []
        for turn in user_turns:
            lower = turn.lower()
            for filler in _FILLER_WORDS:
                count = len(re.findall(rf"\b{re.escape(filler)}\b", lower))
                for _ in range(count):
                    found.append(filler)
        return {
            "filler_word_count": len(found),
            "filler_words": list(set(found)),
        }

    def _analyze_strengths(self, user_turns: list[str]) -> dict:
        strengths = set()
        for turn in user_turns:
            lower = turn.lower()
            for pattern, label in _STRENGTH_PATTERNS:
                if re.search(pattern, lower):
                    strengths.add(label)
        return {"strengths": sorted(strengths)}

    def _analyze_weaknesses(self, user_turns: list[str]) -> dict:
        weaknesses = set()
        for turn in user_turns:
            lower = turn.lower()
            for pattern, label in _WEAKNESS_PATTERNS:
                if re.search(pattern, lower):
                    weaknesses.add(label)
        return {"weaknesses": sorted(weaknesses)}

    def _calculate_confidence(self, user_turns: list[str]) -> dict:
        if not user_turns:
            return {"confidence_score": 0.0}

        total = len(user_turns)
        hedging_count = 0
        question_count = 0
        exclamation_count = 0

        for turn in user_turns:
            lower = turn.lower()
            for word in _HEDGING_WORDS:
                if re.search(rf"\b{re.escape(word)}\b", lower):
                    hedging_count += 1
            if "?" in turn:
                question_count += 1
            if "!" in turn:
                exclamation_count += 1

        hedging_ratio = hedging_count / max(total, 1)
        question_ratio = question_count / max(total, 1)

        score = 100.0
        score -= hedging_ratio * 25
        score -= question_ratio * 10
        score = max(0, min(100, round(score, 1)))
        return {"confidence_score": score}

    def _calculate_clarity(self, user_turns: list[str]) -> dict:
        if not user_turns:
            return {"clarity_score": 0.0}

        total_words = sum(len(t.split()) for t in user_turns)
        total_sentences = sum(len(re.findall(r"[.!?]+", t)) or 1 for t in user_turns)
        avg_sentence_length = total_words / max(total_sentences, 1)

        filler_penalty = 0
        for turn in user_turns:
            lower = turn.lower()
            for filler in _FILLER_WORDS:
                filler_penalty += len(re.findall(rf"\b{re.escape(filler)}\b", lower))

        sentence_score = 100.0
        if avg_sentence_length < 5:
            sentence_score = 60
        elif avg_sentence_length > 30:
            sentence_score = 70
        else:
            sentence_score = 100 - abs(avg_sentence_length - 15) * 2

        filler_ratio = filler_penalty / max(total_words, 1)
        filler_score = max(0, 100 - filler_ratio * 500)

        score = sentence_score * 0.5 + filler_score * 0.5
        return {"clarity_score": round(max(0, min(100, score)), 1)}

    def _analyze_interruptions(self, ai_turns: list[str], user_turns: list[str]) -> dict:
        return {"interruption_count": 0}

    def _analyze_goal_completion(self, scenario_id: str, user_turns: list[str], ai_turns: list[str]) -> dict:
        scenario = get_scenario(scenario_id)
        if not scenario:
            return {"goal_completion": "unknown"}

        goal = scenario.get("goal", "").lower()
        goal_keywords = set(re.findall(r"\b[a-z]+\b", goal))
        stop_words = {"a", "an", "the", "and", "or", "in", "on", "at", "to", "for",
                      "of", "with", "by", "your", "you", "i", "we", "our"}
        goal_keywords -= stop_words

        all_text = " ".join(user_turns + ai_turns).lower()
        matched = sum(1 for kw in goal_keywords if kw in all_text)
        ratio = matched / max(len(goal_keywords), 1)

        if ratio >= 0.6:
            level = "highly addressed"
        elif ratio >= 0.3:
            level = "partially addressed"
        elif ratio >= 0.1:
            level = "minimally addressed"
        else:
            level = "not addressed"
        return {"goal_completion": level}

    def _calculate_overall_score(self, analysis: dict) -> dict:
        confidence = analysis.get("confidence_score", 0)
        clarity = analysis.get("clarity_score", 0)
        filler_count = analysis.get("filler_word_count", 0)
        strengths_count = len(analysis.get("strengths", []))
        weaknesses_count = len(analysis.get("weaknesses", []))

        base = (confidence + clarity) / 2
        filler_penalty = min(filler_count * 2, 20)
        strength_bonus = min(strengths_count * 5, 15)
        weakness_penalty = min(weaknesses_count * 5, 15)

        score = base - filler_penalty + strength_bonus - weakness_penalty
        return {"overall_score": round(max(0, min(100, score)), 1)}
