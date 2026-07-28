SCENARIOS = {
    "networking_event": {
        "id": "networking_event",
        "name": "Networking Event",
        "description": "Practice making connections at a professional networking event.",
        "persona": {
            "name": "Jordan Chen",
            "role": "Senior Engineering Manager",
            "company": "TechCorp",
            "personality": "Friendly but busy. Appreciates concise, confident introductions.",
        },
        "goal": "Make a memorable impression and exchange contact information within 2 minutes.",
        "context": "You're at a crowded industry mixer at a tech conference. Jordan is standing near the drinks table, between conversations. You have one chance to make a good impression.",
        "opening_line": "Hi, I don't think we've met. I'm Jordan.",
        "difficulty": "medium",
    },
    "performance_review": {
        "id": "performance_review",
        "name": "Performance Review",
        "description": "Navigate a performance review conversation with your manager.",
        "persona": {
            "name": "Sarah Park",
            "role": "Director of Engineering",
            "company": "TechCorp",
            "personality": "Direct, data-driven, and supportive. Values preparation and self-awareness.",
        },
        "goal": "Discuss your accomplishments, address a recent project setback, and align on goals for next quarter.",
        "context": "It's your quarterly performance review. Overall you've had a strong quarter, but a recent production incident set back a key deliverable. Sarah values honesty and initiative.",
        "opening_line": "Thanks for making time. Let's start with how you think the quarter went.",
        "difficulty": "medium",
    },
    "promotion_discussion": {
        "id": "promotion_discussion",
        "name": "Promotion Discussion",
        "description": "Advocate for your promotion in a one-on-one with your manager.",
        "persona": {
            "name": "Marcus Williams",
            "role": "VP of Engineering",
            "company": "TechCorp",
            "personality": "Strategic, results-oriented, and slightly skeptical. Needs to be convinced with evidence.",
        },
        "goal": "Present a compelling case for your promotion to Senior Engineer, backed by specific achievements and impact.",
        "context": "You've been in your current role for 18 months and believe you're ready for the next level. Marcus has a reputation for setting the bar high. This is your formal promotion discussion.",
        "opening_line": "So, you asked to discuss your career trajectory. I'm listening.",
        "difficulty": "hard",
    },
    "job_interview": {
        "id": "job_interview",
        "name": "Job Interview",
        "description": "Interview for a role at a company you're excited about.",
        "persona": {
            "name": "Alex Rivera",
            "role": "Staff Engineer",
            "company": "GrowthStartup",
            "personality": "Curious, technical, and collaborative. Asks follow-up questions to probe depth of knowledge.",
        },
        "goal": "Successfully answer behavioral and technical questions, demonstrating both competence and cultural fit.",
        "context": "You're interviewing for a mid-level engineering role at a fast-growing startup. Alex will be your peer if you get the job. The interview covers both technical and behavioral questions.",
        "opening_line": "Great to meet you! Tell me about a project you're proud of.",
        "difficulty": "hard",
    },
    "workplace_conflict": {
        "id": "workplace_conflict",
        "name": "Workplace Conflict",
        "description": "Resolve a disagreement with a colleague over project ownership.",
        "persona": {
            "name": "Priya Patel",
            "role": "Product Manager",
            "company": "TechCorp",
            "personality": "Passionate and opinionated, but reasonable. Cares deeply about the product and can be defensive about her territory.",
        },
        "goal": "Reach a mutually acceptable resolution about who leads the upcoming feature rollout without damaging the working relationship.",
        "context": "You and Priya both believe your teams should own the upcoming customer-facing dashboard feature. There's been tension in recent meetings. You need to find a way to collaborate or agree on a path forward.",
        "opening_line": "I know we've gone back and forth on the dashboard. Let's figure this out.",
        "difficulty": "hard",
    },
}


def get_scenario(scenario_id: str) -> dict | None:
    return SCENARIOS.get(scenario_id)


def list_scenarios() -> list[dict]:
    return [
        {
            "id": s["id"],
            "name": s["name"],
            "description": s["description"],
            "difficulty": s["difficulty"],
        }
        for s in SCENARIOS.values()
    ]
