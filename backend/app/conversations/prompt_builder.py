from app.conversations.context_manager import ContextManager
from app.conversations.scenarios import get_scenario


class PromptBuilder:
    def build(self, scenario_id: str, context_manager: ContextManager) -> str:
        scenario = get_scenario(scenario_id)
        if not scenario:
            return ""

        persona = scenario["persona"]
        transcript = context_manager.get_transcript()

        parts = [
            f"You are {persona['name']}, {persona['role']} at {persona['company']}.",
            f"Personality: {persona['personality']}",
            "",
            f"Context: {scenario['context']}",
            f"Your goal in this conversation: {scenario['goal']}",
            "",
        ]

        if transcript:
            parts.append("Conversation so far:")
            parts.append(transcript)
            parts.append("")

        parts.append("Respond as this persona naturally would. Keep responses conversational and under 3 sentences unless the situation requires more depth.")

        return "\n".join(parts)

    def build_system_prompt(self, scenario_id: str) -> str:
        scenario = get_scenario(scenario_id)
        if not scenario:
            return ""

        persona = scenario["persona"]

        return (
            f"You are roleplaying as {persona['name']}, {persona['role']} at {persona['company']}. "
            f"Personality: {persona['personality']}. "
            f"Context: {scenario['context']}. "
            f"Your goal: {scenario['goal']}. "
            "Stay in character at all times. Keep responses concise and natural. "
            "Do not break character or refer to yourself as an AI."
        )
