export type PracticeGoal = {
  id: string;
  title: string;
  summary: string;
  scenarioIds: string[];
};

export const GOALS_KEY = "delphi_practice_goals";

export const PRACTICE_GOALS: PracticeGoal[] = [
  {
    id: "meet_new_people",
    title: "Meet new people",
    summary: "Feel more at ease starting conversations.",
    scenarioIds: ["networking_event"],
  },
  {
    id: "speak_up",
    title: "Speak up at work",
    summary: "Share your ideas and join the discussion.",
    scenarioIds: ["workplace_conflict", "promotion_discussion"],
  },
  {
    id: "clear_updates",
    title: "Share clear updates",
    summary: "Talk through your work with confidence.",
    scenarioIds: ["performance_review", "job_interview"],
  },
  {
    id: "ask_feedback",
    title: "Ask for feedback",
    summary: "Explore another perspective on your work.",
    scenarioIds: ["performance_review"],
  },
  {
    id: "tricky_conversations",
    title: "Handle tricky conversations",
    summary: "Find the words for moments that feel hard.",
    scenarioIds: ["workplace_conflict"],
  },
  {
    id: "everyday_confidence",
    title: "Build everyday confidence",
    summary: "Get comfortable with conversations, your way.",
    scenarioIds: ["networking_event", "job_interview"],
  },
];

export function readGoals(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const parsed: unknown = JSON.parse(window.localStorage.getItem(GOALS_KEY) || "[]");
    return Array.isArray(parsed) ? parsed.filter((id): id is string => typeof id === "string") : [];
  } catch {
    return [];
  }
}

export function writeGoals(ids: string[]) {
  window.localStorage.setItem(GOALS_KEY, JSON.stringify(ids));
}
