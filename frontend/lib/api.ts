import { getReferralCode } from "@/lib/referral";

export const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
export const ROOT = API.replace(/\/api\/v1\/?$/, "");

export type Scenario = {
  id: string;
  name: string;
  description: string;
  difficulty: string;
};

export type ScenarioDetail = Scenario & {
  persona: {
    name: string;
    role: string;
    company: string;
    personality: string;
  };
  goal: string;
  context: string;
  opening_line: string;
  tips: string[];
};

export type Turn = {
  id: string;
  speaker: string;
  content: string;
  created_at: string;
};

export type SessionData = {
  id: string;
  scenario: string;
  status: string;
  created_at?: string;
  updated_at?: string;
  time_limit_seconds?: number;
  turns: Turn[];
};

export type TranscriptExample = {
  type: "strength" | "weakness";
  label: string;
  quote: string;
};

export type ReportContent = {
  scenario: string;
  persona: string;
  overall_score: number | null;
  assessment_note?: string;
  assessment_method?: string;
  timed_out?: boolean;
  time_limit_seconds?: number;
  rubric_observations?: { criterion: string; observed: boolean; quote: string | null }[];
  summary: string;
  metrics: {
    confidence: number | null;
    clarity: number | null;
    filler_word_count: number;
    filler_words: string[];
    total_turns: number;
    total_user_words: number;
    avg_response_length: number;
  };
  goal_completion: string;
  strengths: string[];
  weaknesses: string[];
  recommendations: string[];
  transcript_examples?: TranscriptExample[];
  references?: { source: string; snippet: string }[];
  suggested_responses?: { weakness?: string; response: string }[];
};

export type ReportData = {
  id: string;
  session_id: string | null;
  status: string;
  title: string;
  content: ReportContent | null;
  storage_url?: string | null;
  created_at: string;
  updated_at: string;
};

export const SESSION_KEY = "delphi_session_id";

export class APIError extends Error {
  constructor(message: string, public status: number) { super(message); }
}

export async function authedFetch(getToken: () => Promise<string | null>, path: string, init?: RequestInit) {
  const token = await getToken();
  if (!token) {
    throw new Error("Not authenticated");
  }
  const referral = getReferralCode();
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      ...init?.headers,
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(referral ? { "X-Delphi-Referral": referral } : {}),
    },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {}
    throw new APIError(typeof detail === "string" ? detail : "Invalid request", res.status);
  }
  if (res.status === 204) return null;
  return res.json();
}
