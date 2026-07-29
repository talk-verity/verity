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

type ReportContent = {
  scenario: string;
  persona: string;
  overall_score: number;
  summary: string;
  metrics: {
    confidence: number;
    clarity: number;
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
};

type ReportData = {
  id: string;
  session_id: string;
  status: string;
  title: string;
  content: ReportContent | null;
  created_at: string;
  updated_at: string;
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
  const [isRecording, setIsRecording] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const [report, setReport] = useState<ReportData | "loading" | null>(null);
  const [completing, setCompleting] = useState(false);

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

  async function toggleRecording() {
    if (isRecording) {
      stopRecording();
    } else {
      await startRecording();
    }
  }

  async function startRecording() {
    if (!session) return;
    try {
      if (!audioCtxRef.current || audioCtxRef.current.state === "closed") {
        audioCtxRef.current = new AudioContext();
      }
      if (audioCtxRef.current.state === "suspended") {
        await audioCtxRef.current.resume();
      }
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
        const blob = new Blob(audioChunksRef.current, { type: recorder.mimeType });
        await sendVoiceMessage(blob);
      };

      recorder.start();
      setIsRecording(true);
    } catch (err) {
      console.error("Mic access denied:", err);
    }
  }

  function stopRecording() {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  }

  async function sendVoiceMessage(blob: Blob) {
    if (!session) return;
    setSending(true);

    const token = await getToken();
    if (!token) { setSending(false); return; }

    const formData = new FormData();
    formData.append("file", blob, "recording." + (blob.type.includes("webm") ? "webm" : "ogg"));
    formData.append("session_id", session.id);

    try {
      const response = await fetch(`${API}/voice/converse`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      if (!response.ok || !response.body) {
        setSending(false);
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        let currentEvent = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            const raw = line.slice(6);
            if (currentEvent === "transcription") {
              const text = JSON.parse(raw).data;
              setSession((prev) =>
                prev
                  ? {
                      ...prev,
                      turns: [
                        ...prev.turns,
                        { id: "voice-user-" + Date.now(), speaker: "user", content: text, created_at: new Date().toISOString() },
                      ],
                    }
                  : prev
              );
            } else if (currentEvent === "ai_response") {
              const text = JSON.parse(raw).data;
              setSession((prev) =>
                prev
                  ? {
                      ...prev,
                      turns: [
                        ...prev.turns,
                        { id: "voice-ai-" + Date.now(), speaker: "ai", content: text, created_at: new Date().toISOString() },
                      ],
                    }
                  : prev
              );
            } else if (currentEvent === "audio") {
              const { data: b64 } = JSON.parse(raw);
              if (b64 && b64.length > 0) {
                try {
                  const binary = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
                  const ctx = audioCtxRef.current;
                  if (ctx && ctx.state !== "closed") {
                    const buffer = await ctx.decodeAudioData(binary.buffer);
                    const source = ctx.createBufferSource();
                    source.buffer = buffer;
                    source.connect(ctx.destination);
                    source.start();
                  }
                } catch (e) {
                  console.error("Audio playback failed:", e);
                }
              }
            }
          }
        }
      }
    } catch (err) {
      console.error("Voice converse failed:", err);
    }
    setSending(false);
  }

  async function completeConversation() {
    if (!session || completing) return;
    setCompleting(true);
    setReport("loading");
    const token = await getToken();
    if (!token) { setCompleting(false); return; }
    try {
      const res = await fetch(`${API}/conversations/${session.id}/complete`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (data.report_id) {
        await pollReport(data.report_id, token);
      }
    } catch (e) {
      console.error("Complete failed:", e);
      setReport(null);
    }
    setCompleting(false);
  }

  async function pollReport(reportId: string, token: string) {
    for (let i = 0; i < 60; i++) {
      await new Promise((r) => setTimeout(r, 2000));
      try {
        const res = await fetch(`${API}/sessions/${session!.id}/report`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) continue;
        const data: ReportData = await res.json();
        if (data.status === "ready") {
          setReport(data);
          return;
        }
      } catch {}
    }
    setReport(null);
  }

  function newConversation() {
    setSession(null);
    setReport(null);
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

  if (session && report && typeof report !== "string") {
    const c = report.content;
    return (
      <div className="flex flex-1 flex-col max-w-2xl mx-auto w-full px-4 py-6 overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-medium">Feedback</h2>
          <button onClick={newConversation} className="text-sm text-zinc-400 hover:text-zinc-600">
            New conversation
          </button>
        </div>

        <div className="space-y-6">
          <div className="flex items-center gap-3">
            <div className="text-4xl font-semibold">{c?.overall_score ?? "—"}</div>
            <div className="text-sm text-zinc-500">overall score</div>
          </div>

          {c?.summary && (
            <p className="text-sm leading-relaxed text-zinc-700">{c.summary}</p>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-xl bg-neutral-50 px-4 py-3">
              <div className="text-xs text-zinc-400 uppercase tracking-wide">Confidence</div>
              <div className="text-lg font-medium mt-1">{c?.metrics.confidence ?? "—"}/100</div>
            </div>
            <div className="rounded-xl bg-neutral-50 px-4 py-3">
              <div className="text-xs text-zinc-400 uppercase tracking-wide">Clarity</div>
              <div className="text-lg font-medium mt-1">{c?.metrics.clarity ?? "—"}/100</div>
            </div>
            <div className="rounded-xl bg-neutral-50 px-4 py-3">
              <div className="text-xs text-zinc-400 uppercase tracking-wide">Filler words</div>
              <div className="text-lg font-medium mt-1">{c?.metrics.filler_word_count ?? 0}</div>
            </div>
            <div className="rounded-xl bg-neutral-50 px-4 py-3">
              <div className="text-xs text-zinc-400 uppercase tracking-wide">Turns</div>
              <div className="text-lg font-medium mt-1">{c?.metrics.total_turns ?? 0}</div>
            </div>
          </div>

          {c?.goal_completion && (
            <div>
              <div className="text-xs text-zinc-400 uppercase tracking-wide mb-1">Goal completion</div>
              <p className="text-sm text-zinc-700 capitalize">{c.goal_completion}</p>
            </div>
          )}

          {c?.strengths && c.strengths.length > 0 && (
            <div>
              <div className="text-xs text-zinc-400 uppercase tracking-wide mb-2">Strengths</div>
              <ul className="space-y-1">
                {c.strengths.map((s, i) => (
                  <li key={i} className="text-sm text-zinc-700 flex gap-2">
                    <span className="text-green-600 shrink-0">+</span>
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {c?.weaknesses && c.weaknesses.length > 0 && (
            <div>
              <div className="text-xs text-zinc-400 uppercase tracking-wide mb-2">Areas to improve</div>
              <ul className="space-y-1">
                {c.weaknesses.map((w, i) => (
                  <li key={i} className="text-sm text-zinc-700 flex gap-2">
                    <span className="text-amber-600 shrink-0">→</span>
                    {w}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {c?.recommendations && c.recommendations.length > 0 && (
            <div>
              <div className="text-xs text-zinc-400 uppercase tracking-wide mb-2">Recommendations</div>
              <ul className="space-y-2">
                {c.recommendations.map((r, i) => (
                  <li key={i} className="text-sm text-zinc-700 bg-neutral-50 rounded-xl px-4 py-3 leading-relaxed">
                    {r}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <button onClick={newConversation} className="w-full bg-neutral-900 text-white rounded-2xl py-3 text-sm font-medium mt-4">
            Practice another scenario
          </button>
        </div>
      </div>
    );
  }

  if (session) {
    return (
      <div className="flex flex-1 flex-col max-w-2xl mx-auto w-full px-4 py-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-medium">{scenarioMap[session.scenario] || session.scenario}</h2>
          <div className="flex gap-2">
            <button
              onClick={completeConversation}
              disabled={completing || session.turns.length === 0}
              className="text-sm text-emerald-600 hover:text-emerald-700 font-medium disabled:opacity-40"
            >
              {completing ? "Completing…" : "Complete & get feedback"}
            </button>
            <button onClick={newConversation} className="text-sm text-zinc-400 hover:text-zinc-600">
              New conversation
            </button>
          </div>
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
          {report === "loading" && (
            <div className="flex justify-center py-8">
              <p className="text-sm text-zinc-400 animate-pulse">Generating feedback…</p>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <div className="flex gap-2 pb-4">
          <input
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
            placeholder="Type your response..."
            disabled={sending || isRecording || report === "loading"}
            className="flex-1 border border-neutral-200 rounded-2xl px-4 py-2.5 text-sm outline-none focus:border-neutral-400 disabled:opacity-50"
          />
          <button
            onClick={sendMessage}
            disabled={!message.trim() || sending || isRecording || report === "loading"}
            className="bg-neutral-900 text-white rounded-2xl px-5 py-2.5 text-sm font-medium disabled:opacity-40"
          >
            Send
          </button>
          <button
            onClick={toggleRecording}
            disabled={sending || report === "loading"}
            className={`rounded-2xl px-4 py-2.5 text-sm font-medium transition-colors ${
              isRecording
                ? "bg-red-600 text-white animate-pulse"
                : "bg-neutral-100 text-neutral-700 hover:bg-neutral-200 disabled:opacity-40"
            }`}
            title={isRecording ? "Stop recording" : "Record voice"}
          >
            {isRecording ? (
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>
            )}
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
