from app.conversations.scenarios import get_scenario


class ContextManager:
    def __init__(self, scenario_id: str, turns: list | None = None):
        self.scenario_id = scenario_id
        self.scenario = get_scenario(scenario_id) or {}
        self._turns = turns or []

    def add_turn(self, speaker: str, content: str) -> None:
        self._turns.append({"speaker": speaker, "content": content})

    def get_transcript(self) -> str:
        lines = []
        for t in self._turns:
            prefix = "User" if t["speaker"] == "user" else "AI"
            lines.append(f"{prefix}: {t['content']}")
        return "\n".join(lines)

    def get_transcript_json(self) -> list[dict]:
        return list(self._turns)

    def get_memory(self) -> str:
        if not self._turns:
            return "No prior conversation."
        recent = self._turns[-4:]
        summary = "; ".join(f"{t['speaker']} said: {t['content'][:100]}" for t in recent)
        return f"Recent context: {summary}"

    def get_scenario_goal(self) -> str:
        return self.scenario.get("goal", "")

    def get_state(self) -> dict:
        persona = self.scenario.get("persona", {})
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario.get("name", ""),
            "goal": self.get_scenario_goal(),
            "context": self.scenario.get("context", ""),
            "turn_count": len(self._turns),
            "persona_name": persona.get("name", ""),
            "persona_role": persona.get("role", ""),
        }

    def to_dict(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "turns": list(self._turns),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ContextManager":
        return cls(scenario_id=data["scenario_id"], turns=data.get("turns", []))
