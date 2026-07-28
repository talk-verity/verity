from app.conversations.scenarios import get_scenario, list_scenarios, SCENARIOS


class TestScenarios:
    def test_list_scenarios(self):
        scenarios = list_scenarios()
        assert len(scenarios) == 5
        ids = [s["id"] for s in scenarios]
        assert "networking_event" in ids
        assert "job_interview" in ids

    def test_get_scenario_valid(self):
        scenario = get_scenario("networking_event")
        assert scenario is not None
        assert scenario["name"] == "Networking Event"
        assert "persona" in scenario
        assert "goal" in scenario
        assert "context" in scenario
        assert "opening_line" in scenario

    def test_get_scenario_invalid(self):
        assert get_scenario("nonexistent") is None

    def test_all_scenarios_have_required_fields(self):
        required = {"id", "name", "description", "persona", "goal", "context", "opening_line", "difficulty"}
        for sid, scenario in SCENARIOS.items():
            missing = required - set(scenario.keys())
            assert not missing, f"Scenario '{sid}' missing: {missing}"
            persona_required = {"name", "role", "company", "personality"}
            p_missing = persona_required - set(scenario["persona"].keys())
            assert not p_missing, f"Scenario '{sid}' persona missing: {p_missing}"
