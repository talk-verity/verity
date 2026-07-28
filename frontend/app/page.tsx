"use client";

import { useEffect, useState, useRef } from "react";
import { useAuth } from "@clerk/nextjs";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const ROOT = API.replace(/\/api\/v1\/?$/, "");

type Scenario = {
  id: string;
  name: string;
  description: string;
  difficulty: string;
};

type Turn = {
  id: string;
  speaker: string;
  content: string;
  created_at: string;
};

type SessionData = {
  id: string;
  scenario: string;
  status: string;
  turns: Turn[];
};

export default function Home() {
  const { isLoaded, isSignedIn, getToken } = useAuth();
  const [healthStatus, setHealthStatus] = useState("Checking...");
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [scenarioMap, setScenarioMap] = useState<Record<string, string>>({});
  const [session, setSession] = useState<SessionData | null>(null);
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [creating, setCreating] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch(`${ROOT}/health`)
      .then((r) => r.json())
      .then((d) => setHealthStatus(d.status))
      .catch(() => setHealthStatus("Unhealthy"));
  }, []);

  useEffect(() => {
    if (!isSignedIn) return;
    getToken().then(async (token) => {
      if (!token) return;
      try {
        const data: Scenario[] = await fetch(`${API}/conversations/scenarios`, {
          headers: { Authorization: `Bearer ${token}` },
        }).then((r) => r.json());
        setScenarios(data);
        setScenarioMap(Object.fromEntries(data.map((s) => [s.id, s.name])));
      } catch {}
    });
  }, [isSignedIn, getToken]);

  useEffect(() => {
    if (!isSignedIn) return;
    const storedId = localStorage.getItem("verity_session_id");
    if (!storedId) return;
    getToken().then(async (token) => {
      if (!token) return;
      try {
        const data: SessionData = await fetch(`${API}/conversations/${storedId}`, {
          headers: { Authorization: `Bearer ${token}` },
        }).then((r) => r.json());
        if (data.id) {
          setSession(data);
        } else {
          localStorage.removeItem("verity_session_id");
        }
      } catch {
        localStorage.removeItem("verity_session_id");
      }
    });
  }, [isSignedIn, getToken]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [session?.turns]);

  function startConversation(scenarioId: string) {
    setCreating(true);
    getToken()
      .then((token) => {
        if (!token) { setCreating(false); return; }
        return fetch(`${API}/conversations`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
          body: JSON.stringify({ scenario_id: scenarioId }),
        });
      })
      .then((res) => {
        if (!res) return;
        if (!res.ok) { setCreating(false); return; }
        return res.json();
      })
      .then((data) => {
        if (!data || !data.id) { setCreating(false); return; }
        setSession({ ...data, turns: [] });
        localStorage.setItem("verity_session_id", data.id);
      })
      .catch(() => {})
      .finally(() => setCreating(false));
  }

  async function sendMessage() {
    if (!message.trim() || !session || sending) return;
    const content = message.trim();
    setMessage("");
    setSending(true);

    const userTurn: Turn = {
      id: "user-" + Date.now(),
      speaker: "user",
      content,
      created_at: new Date().toISOString(),
    };
    setSession((prev) => (prev ? { ...prev, turns: [...prev.turns, userTurn] } : prev));

    const token = await getToken();
    if (!token) { setSending(false); return; }

    try {
      const data: Turn = await fetch(`${API}/conversations/${session.id}/respond`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      }).then((r) => r.json());
      if (data.id) {
        setSession((prev) => (prev ? { ...prev, turns: [...prev.turns, data] } : prev));
      }
    } catch {
      setSession((prev) =>
        prev ? { ...prev, turns: prev.turns.filter((t) => t.id !== userTurn.id) } : prev
      );
    }
    setSending(false);
  }

  function newConversation() {
    setSession(null);
    localStorage.removeItem("verity_session_id");
  }

  if (!isLoaded) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-zinc-400">Loading...</p>
      </div>
    );
  }

  if (!isSignedIn) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center px-4">
        <h1 className="text-4xl font-semibold tracking-tight">Verity</h1>
        <p className="mt-4 text-zinc-600">Sign in to practice conversations</p>
        <p className="mt-2 text-sm text-zinc-400">Backend: {healthStatus}</p>
      </div>
    );
  }

  if (session) {
    return (
      <div className="flex flex-1 flex-col max-w-2xl mx-auto w-full px-4 py-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-medium">{scenarioMap[session.scenario] || session.scenario}</h2>
          <button onClick={newConversation} className="text-sm text-zinc-400 hover:text-zinc-600">
            New conversation
          </button>
        </div>

        <div className="flex-1 overflow-y-auto space-y-3 mb-4">
          {session.turns.length === 0 && (
            <p className="text-zinc-400 text-sm text-center mt-8">The conversation starts here...</p>
          )}
          {session.turns.map((turn) => (
            <div key={turn.id} className={`flex ${turn.speaker === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[75%] rounded-2xl px-4 py-2 text-sm leading-relaxed ${
                  turn.speaker === "user"
                    ? "bg-neutral-900 text-white"
                    : "bg-neutral-100 text-neutral-900"
                }`}
              >
                {turn.content}
              </div>
            </div>
          ))}
          <div ref={chatEndRef} />
        </div>

        <div className="flex gap-2 pb-4">
          <input
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
            placeholder="Type your response..."
            disabled={sending}
            className="flex-1 border border-neutral-200 rounded-2xl px-4 py-2.5 text-sm outline-none focus:border-neutral-400 disabled:opacity-50"
          />
          <button
            onClick={sendMessage}
            disabled={!message.trim() || sending}
            className="bg-neutral-900 text-white rounded-2xl px-5 py-2.5 text-sm font-medium disabled:opacity-40"
          >
            Send
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col items-center max-w-lg mx-auto w-full px-4 py-16">
      <h1 className="text-4xl font-semibold tracking-tight mb-1">Verity</h1>
      <p className="text-sm text-zinc-400 mb-10">Backend: {healthStatus}</p>
      <div className="w-full space-y-2">
        {scenarios.map((s) => (
          <button
            key={s.id}
            onClick={() => startConversation(s.id)}
            disabled={creating}
            className="w-full text-left border border-neutral-200 rounded-xl px-5 py-4 hover:border-neutral-400 transition-colors disabled:opacity-40"
          >
            <div className="flex items-center justify-between">
              <span className="font-medium text-sm">{s.name}</span>
              <span className="text-xs text-neutral-400 capitalize">{s.difficulty}</span>
            </div>
            <p className="text-xs text-neutral-500 mt-1 leading-relaxed">{s.description}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
