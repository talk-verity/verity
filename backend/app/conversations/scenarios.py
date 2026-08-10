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
        "tips": [
            "Prepare a 15-second intro: name, role, and one memorable thing you're working on.",
            "Jordan is friendly but busy — get to the point fast and respect their time.",
            "Close with a concrete next step, like exchanging contact info or a follow-up topic.",
            "Show you listen by referencing something they said before pivoting to yourself.",
        ],
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
        "tips": [
            "Lead with quantified wins before Sarah asks — she appreciates preparation.",
            "Own the production incident: explain what happened, what you learned, and the fix.",
            "Bring 2–3 concrete goals for next quarter and ask how they align with team priorities.",
            "End by asking for specific feedback on one area you're working to improve.",
        ],
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
        "tips": [
            "Anchor your case in measurable impact, not tenure — Marcus wants evidence.",
            "Pre-empt skepticism: address the gap between your level and the next level directly.",
            "Reference 2–3 specific projects where you led and the results you drove.",
            "Ask what a 'clear yes' looks like so you leave with an actionable path.",
        ],
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
        "tips": [
            "Use STAR (Situation, Task, Action, Result) to structure project stories.",
            "Expect follow-up probes — go one level deeper than your first answer.",
            "Show collaboration and curiosity: Alex values working well with peers.",
            "Have a few thoughtful questions ready to ask Alex about the team and roadmap.",
        ],
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
        "tips": [
            "Acknowledge Priya's stake in the product before stating your own — it lowers defensiveness.",
            "Stay focused on the outcome for the customer, not who 'wins' ownership.",
            "Propose a concrete option (e.g. split ownership, shared roadmap) to move forward.",
            "Protect the relationship: agree on how you'll both handle it going forward.",
        ],
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
