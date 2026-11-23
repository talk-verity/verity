"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { SSEParser } from "@/lib/sse";
import { parseApiTimestamp } from "@/lib/time";
import { useVoiceRecorder } from "@/hooks/useVoiceRecorder";
import AuthGate from "@/components/AuthGate";
import ContextPanel from "@/components/ContextPanel";
import {
  authedFetch,
  APIError,
  API,
  SESSION_KEY,
  type Scenario,
  type ScenarioDetail,
  type SessionData,
} from "@/lib/api";

const SCENARIO_TIME_LIMIT_SECONDS = 300;

function formatTime(seconds: number) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

export default function ConversationPage() {
  const { isSignedIn, getToken, userId } = useAuth();
  const router = useRouter();
  const [session, setSession] = useState<SessionData | null>(null);
  const [scenarioNames, setScenarioNames] = useState<Record<string, string>>({});
  const [scenarioDetail, setScenarioDetail] = useState<ScenarioDetail | null>(null);
  const [micQuality, setMicQuality] = useState<{
    score: number;
    quality: string;
    recognized: boolean;
    rms_db: number | null;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [aiBusy, setAiBusy] = useState(false);
  const [liveTranscript, setLiveTranscript] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [completing, setCompleting] = useState(false);
  const [now, setNow] = useState<number>(() => Date.now());
  const timedOutHandled = useRef(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const requestRef = useRef<AbortController | null>(null);
  const mounted = useRef(false);
  const busyRef = useRef(false);
  const pendingText = useRef<{ content: string; id: string } | null>(null);
  const pendingVoice = useRef<{ blob: Blob; id: string } | null>(null);
  const [canRetryVoice, setCanRetryVoice] = useState(false);
  const voice = useVoiceRecorder(blob => { void sendVoiceMessage(blob); }, setError);
  const { isRecording } = voice;
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; requestRef.current?.abort(); };
  }, []);

  useEffect(() => {
    if (!isSignedIn) return;
    const controller = new AbortController();
    const signal = controller.signal;
    authedFetch(getToken, "/conversations/scenarios", { signal })
      .then(data => { if (!signal.aborted) setScenarioNames(Object.fromEntries((data as Scenario[]).map(s => [s.id, s.name]))); })
      .catch(() => {});
    const storedId = localStorage.getItem(`${SESSION_KEY}:${userId}`);
    const load = async () => {
      if (!storedId) return null;
      try {
        return await authedFetch(getToken, `/conversations/${storedId}`, { signal }) as SessionData;
      } catch (err) {
        if (err instanceof APIError && err.status === 404) {
          localStorage.removeItem(`${SESSION_KEY}:${userId}`);
          return null;
        }
        throw err;
      }
    };
    load().then(data => {
      if (signal.aborted) return;
      setSession(data);
      if (data) authedFetch(getToken, `/conversations/scenarios/${data.scenario}`, { signal })
        .then(detail => { if (!signal.aborted) setScenarioDetail(detail); }).catch(() => {});
    }).catch(err => { if (!signal.aborted) setError(err.message); })
      .finally(() => { if (!signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [isSignedIn, getToken, userId]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [session?.turns]);

  async function refreshSession(id: string, signal?: AbortSignal) {
    const data = await authedFetch(getToken, `/conversations/${id}`, { signal });
    if (mounted.current) setSession(data);
  }

  async function sendMessage() {
    if (!message.trim() || !session || busyRef.current || isRecording || voice.starting || completing) return;
    busyRef.current = true;
    const content = message.trim();
    if (pendingText.current?.content !== content) pendingText.current = { content, id: crypto.randomUUID() };
    const controller = new AbortController();
    requestRef.current = controller;
    setSending(true); setAiBusy(true); setError(null);
    try {
      await authedFetch(getToken, `/conversations/${session.id}/respond`, {
        method: "POST", signal: controller.signal,
        body: JSON.stringify({ content, request_id: pendingText.current.id }),
      });
      await refreshSession(session.id, controller.signal);
      if (mounted.current) setMessage("");
      pendingText.current = null;
    } catch (err) {
      if (mounted.current) setError(err instanceof Error ? err.message : "Message failed. Retry to recover your response.");
    } finally {
      busyRef.current = false;
      if (mounted.current) { setSending(false); setAiBusy(false); }
    }
  }

  async function toggleRecording() {
    if (isRecording) voice.stop();
    else if (!busyRef.current && !completing) await voice.start();
  }

  async function sendVoiceMessage(blob: Blob) {
    if (!session || busyRef.current || completing) return;
    busyRef.current = true;
    if (pendingVoice.current?.blob !== blob) pendingVoice.current = { blob, id: crypto.randomUUID() };
    const controller = new AbortController();
    requestRef.current = controller;
    setSending(true); setAiBusy(true); setError(null); setCanRetryVoice(false);
    try {
      const token = await getToken();
      if (!token) throw new Error("Please sign in again.");
      const formData = new FormData();
      formData.append("file", blob, "recording");
      formData.append("session_id", session.id);
      formData.append("request_id", pendingVoice.current.id);
      const response = await fetch(`${API}/voice/converse`, {
        method: "POST", signal: controller.signal,
        headers: { Authorization: `Bearer ${token}` }, body: formData,
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(typeof body.detail === "string" ? body.detail : "Voice request failed.");
      }
      if (!response.body) throw new Error("No voice response received.");
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      const parser = new SSEParser();
      let finished = false;
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          for (const event of parser.push(decoder.decode(value, { stream: true }))) {
            const payload = JSON.parse(event.data);
            if (event.event === "error") throw new Error(payload.message);
            if (event.event === "warning" && mounted.current) setError(payload.data);
            if (event.event === "transcription" && mounted.current) setLiveTranscript(payload.data);
            if (event.event === "mic_quality" && mounted.current) setMicQuality(payload.data);
            if (event.event === "ai_response") {
              // The turn is already committed; show text before speech synthesis finishes.
              await refreshSession(session.id, controller.signal);
              if (mounted.current) { setLiveTranscript(""); setAiBusy(false); }
            }
            if (event.event === "audio" && mounted.current) {
              try { await voice.play(payload.data); }
              catch { setError("Your response was saved, but audio playback failed."); }
            }
            if (event.event === "done") finished = true;
          }
        }
      } finally { await reader.cancel(); reader.releaseLock(); }
      if (!finished) throw new Error("Connection interrupted. Retry to recover the response.");
      await refreshSession(session.id, controller.signal);
      pendingVoice.current = null;
    } catch (err) {
      if (mounted.current) {
        setError(err instanceof Error ? err.message : "Voice request failed.");
        setCanRetryVoice(true);
      }
    } finally {
      busyRef.current = false;
      if (mounted.current) { setSending(false); setAiBusy(false); setLiveTranscript(""); }
    }
  }

  const completeConversation = useCallback(async (reason?: string) => {
    if (!session || completing) return;
    if (isRecording) {
      voice.stop();
    }
    busyRef.current = true;
    setCompleting(true);
    setError(null);
    try {
      const controller = new AbortController();
      requestRef.current = controller;
      const data = await authedFetch(getToken, `/conversations/${session.id}/complete`, {
        method: "POST",
        signal: controller.signal,
        body: reason ? JSON.stringify({ reason }) : undefined,
      });
      if (!mounted.current) return;
      if (data.report_id) {
        localStorage.removeItem(`${SESSION_KEY}:${userId}`);
        router.push(`/reports/${data.report_id}`);
      }
    } catch {
      if (mounted.current) {
        setError("Failed to complete the conversation. Try again.");
        setCompleting(false);
      }
      busyRef.current = false;
    }
  }, [session, completing, isRecording, voice, getToken, userId, router]);

  const completeRef = useRef(completeConversation);
  completeRef.current = completeConversation;

  useEffect(() => {
    if (!session || session.status !== "active") return;
    const interval = setInterval(() => {
      setNow(Date.now());
    }, 1000);
    return () => clearInterval(interval);
  }, [session]);

  const startMs = session?.created_at ? parseApiTimestamp(session.created_at) : now;
  const elapsed = Math.floor((now - startMs) / 1000);
  const timeLeft = session ? Math.max(0, SCENARIO_TIME_LIMIT_SECONDS - elapsed) : SCENARIO_TIME_LIMIT_SECONDS;

  useEffect(() => {
    if (!session || session.status !== "active" || timeLeft > 0) return;
    if (timedOutHandled.current) return;
    timedOutHandled.current = true;
    void completeRef.current("time_expired");
  }, [session, timeLeft]);

  function newConversation() {
    if (busyRef.current || isRecording || voice.starting || completing) return;
    pendingText.current = null; pendingVoice.current = null; setCanRetryVoice(false);
    timedOutHandled.current = false;
    setNow(Date.now());
    setSession(null);
    setMessage("");
    setError(null);
    setLiveTranscript("");
    localStorage.removeItem(`${SESSION_KEY}:${userId}`);
  }

  return (
    <AuthGate>
      <main className="flex-1 w-full mx-auto max-w-5xl px-6 py-6 flex flex-col">
        {error && (
          <div className="mb-4 rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {canRetryVoice && pendingVoice.current && (
          <button className="mb-4 text-sm underline" disabled={sending || isRecording || completing} onClick={() => { if (pendingVoice.current) void sendVoiceMessage(pendingVoice.current.blob); }}>
            Retry recorded message
          </button>
        )}
        {loading ? (
          <div className="flex flex-1 items-center justify-center">
            <p className="text-neutral-400 animate-pulse">Loading conversation…</p>
          </div>
        ) : !session ? (
          <div className="flex flex-1 flex-col items-center justify-center text-center">
            <h2 className="text-xl font-semibold">No active conversation</h2>
            <p className="mt-2 text-sm text-neutral-500">
              Pick a scenario to start practicing.
            </p>
            <Link
              href="/scenarios"
              className="mt-6 bg-neutral-900 text-white rounded-2xl px-5 py-2.5 text-sm font-medium"
            >
              Choose a scenario
            </Link>
          </div>
        ) : (
          <div className="flex flex-1 flex-col-reverse md:flex-row gap-6 min-h-0">
            <div className="flex-1 min-w-0 flex flex-col">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <h2 className="text-lg font-medium">
                    {scenarioNames[session.scenario] || session.scenario}
                  </h2>
                  <div
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-medium border transition-colors ${
                      timeLeft <= 30
                        ? "bg-red-50 text-red-700 border-red-300 animate-pulse dark:bg-red-950/60 dark:text-red-300 dark:border-red-800"
                        : timeLeft <= 60
                        ? "bg-amber-50 text-amber-800 border-amber-300 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-800"
                        : "bg-neutral-50 text-neutral-700 border-neutral-200 dark:bg-neutral-800 dark:text-neutral-300 dark:border-neutral-700"
                    }`}
                    title="5-minute scenario limit"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
                    </svg>
                    <span>{timeLeft === 0 ? "0:00" : formatTime(timeLeft)}</span>
                  </div>
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={() => completeConversation()}
                    disabled={completing || sending || isRecording || voice.starting || !session.turns.some(t => t.speaker === "user")}
                    className="text-sm text-emerald-600 hover:text-emerald-700 font-medium disabled:opacity-40"
                  >
                    {completing ? (timeLeft <= 0 ? "Time's up! Generating…" : "Completing…") : "Complete & get feedback"}
                  </button>
                  <button
                    onClick={newConversation}
                    disabled={sending || isRecording || voice.starting || completing}
                    className="text-sm text-neutral-400 hover:text-neutral-600"
                  >
                    New conversation
                  </button>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto space-y-3 mb-4">
                {session.turns.length === 0 && (
                  <p className="text-neutral-400 text-sm text-center mt-8">
                    The conversation starts here...
                  </p>
                )}
                {session.turns.map((turn) => (
                  <div key={turn.id} className={`flex ${turn.speaker === "user" ? "justify-end" : "justify-start"}`}>
                    <div
                      className={`max-w-[75%] rounded-2xl px-4 py-2 text-sm leading-relaxed ${
                        turn.speaker === "user"
                          ? "bg-neutral-900 text-white"
                          : "bg-neutral-100 text-neutral-900 dark:bg-neutral-800 dark:text-neutral-100"
                      }`}
                    >
                      {turn.content}
                    </div>
                  </div>
                ))}
                {(isRecording || sending) && liveTranscript && (
                  <div className="flex justify-end">
                    <div className="max-w-[75%] rounded-2xl px-4 py-2 text-sm leading-relaxed bg-neutral-800 text-neutral-100 italic">
                      {liveTranscript}
                      <span className="inline-block w-1.5 h-4 ml-0.5 align-middle bg-neutral-400 animate-pulse" />
                    </div>
                  </div>
                )}
                {(aiBusy || isRecording) && (
                  <div className="flex justify-center py-2">
                    <span className="inline-flex items-center gap-2 text-sm text-neutral-400">
                      <span className="flex gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-neutral-400 animate-bounce" />
                        <span className="w-1.5 h-1.5 rounded-full bg-neutral-400 animate-bounce [animation-delay:150ms]" />
                        <span className="w-1.5 h-1.5 rounded-full bg-neutral-400 animate-bounce [animation-delay:300ms]" />
                      </span>
                      {isRecording ? "Listening…" : "Responding…"}
                    </span>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              {timeLeft <= 0 && (
                <div className="mb-3 rounded-xl bg-amber-50 border border-amber-200 px-4 py-2 text-xs sm:text-sm text-amber-800 flex items-center gap-2 dark:bg-amber-950/40 dark:border-amber-900/50 dark:text-amber-200">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
                  </svg>
                  <span>5 minutes are up! Automatically completing conversation and generating your feedback…</span>
                </div>
              )}

              <div className="flex gap-2 pb-6">
                <input
                  aria-label="Your response"
                  maxLength={8000}
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
                  placeholder={timeLeft <= 0 ? "Time has expired. Generating feedback…" : "Type your response..."}
                  disabled={sending || isRecording || voice.starting || completing || timeLeft <= 0}
                  className="flex-1 border border-neutral-200 rounded-2xl px-4 py-2.5 text-sm outline-none focus:border-neutral-400 disabled:opacity-50"
                />
                <button
                  onClick={sendMessage}
                  disabled={!message.trim() || sending || isRecording || voice.starting || completing || timeLeft <= 0}
                  className="bg-neutral-900 text-white rounded-2xl px-5 py-2.5 text-sm font-medium disabled:opacity-40"
                >
                  Send
                </button>
                <button
                  onClick={toggleRecording}
                  disabled={sending || completing || voice.starting || timeLeft <= 0}
                  className={`rounded-2xl px-4 py-2.5 text-sm font-medium transition-colors ${
                    isRecording
                      ? "bg-red-600 text-white animate-pulse"
                      : "bg-neutral-100 text-neutral-700 hover:bg-neutral-200 disabled:opacity-40"
                  }`}
                  title={isRecording ? "Stop recording" : "Record voice"}
                >
                  <MicIcon recording={isRecording} />
                </button>
              </div>
            </div>

            <div className="w-full md:w-72 md:shrink-0">
              {scenarioDetail ? (
                <div className="md:sticky md:top-6">
                  <ContextPanel scenario={scenarioDetail} />
                  <MicQualityBadge quality={micQuality} />
                </div>
              ) : (
                <div className="rounded-2xl border border-neutral-200 p-4 text-sm text-neutral-400">
                  Loading context…
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </AuthGate>
  );
}

function MicQualityBadge({
  quality,
}: {
  quality: {
    score: number;
    quality: string;
    recognized: boolean;
    rms_db: number | null;
  } | null;
}) {
  if (!quality) return null;

  const palette: Record<string, string> = {
    good: "bg-emerald-50 text-emerald-700 border-emerald-200",
    low: "bg-amber-50 text-amber-700 border-amber-200",
    poor: "bg-orange-50 text-orange-700 border-orange-200",
    too_quiet: "bg-red-50 text-red-700 border-red-200",
    clipping: "bg-red-50 text-red-700 border-red-200",
    unknown: "bg-neutral-50 text-neutral-500 border-neutral-200",
  };
  const labels: Record<string, string> = {
    good: "Mic sounds good",
    low: "Mic is picking up low audio",
    poor: "Mic audio is weak — speak up",
    too_quiet: "Mic isn't picking up audio",
    clipping: "Audio is clipping — lower input volume",
    unknown: "Couldn't assess mic level",
  };

  const dot: Record<string, string> = {
    good: "bg-emerald-500",
    low: "bg-amber-500",
    poor: "bg-orange-500",
    too_quiet: "bg-red-500",
    clipping: "bg-red-500",
    unknown: "bg-neutral-400",
  };

  return (
    <div
      className={`mt-4 rounded-2xl border px-4 py-3 text-xs ${palette[quality.quality] || palette.unknown}`}
    >
      <div className="flex items-center gap-2 font-medium">
        <span className={`w-2 h-2 rounded-full ${dot[quality.quality] || dot.unknown}`} />
        {labels[quality.quality] || labels.unknown}
        {typeof quality.score === "number" && (
          <span className="ml-auto opacity-60">{Math.round(quality.score)}</span>
        )}
      </div>
      {quality.rms_db != null && (
        <p className="mt-1 opacity-70">
          Level {quality.rms_db.toFixed(0)} dB · {quality.recognized ? "speech recognized" : "no speech recognized"}
        </p>
      )}
    </div>
  );
}

function MicIcon({ recording }: { recording: boolean }) {
  return recording ? (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <rect x="6" y="6" width="12" height="12" rx="2" />
    </svg>
  ) : (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <line x1="12" y1="19" x2="12" y2="23" />
      <line x1="8" y1="23" x2="16" y2="23" />
    </svg>
  );
}
