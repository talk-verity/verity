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
            f"You are roleplaying as {persona['name']}, {persona['role']} at {persona['company']}.",
            f"Personality: {persona['personality']}",
            "",
            "THE USER'S SITUATION",
            scenario['context'],
            "",
            "THE USER'S GOAL",
            scenario['goal'],
            "",
            "YOUR ROLE",
            f"You are {persona['name']}. The user is talking to you. "
            "Respond in character — stay true to your personality. "
            "Do NOT act as the user or advocate for them. "
            "Ask questions, challenge them, react naturally as this character would.",
            "",
        ]

        if transcript:
            parts.append("CONVERSATION SO FAR")
            parts.append(transcript)
            parts.append("")

        parts.append("Keep responses conversational and under 3 sentences unless the situation requires more depth.")

        return "\n".join(parts)

    def build_system_prompt(self, scenario_id: str) -> str:
        scenario = get_scenario(scenario_id)
        if not scenario:
            return ""

        persona = scenario["persona"]

        return (
            f"You are roleplaying as {persona['name']}, {persona['role']} at {persona['company']}. "
            f"Personality: {persona['personality']}. "
            f"The user's situation: {scenario['context']}. "
            f"The user's goal: {scenario['goal']}. "
            f"Stay in character as {persona['name']}. "
            "Do not act as the user or advocate for them. "
            "Keep responses concise and natural. "
            "Do not break character or refer to yourself as an AI."
        )
