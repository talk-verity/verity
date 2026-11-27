"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { parseVoiceEvent, SSEParser } from "@/lib/sse";
import { parseApiTimestamp } from "@/lib/time";
import { useVoiceRecorder } from "@/hooks/useVoiceRecorder";
import AuthGate from "@/components/AuthGate";
import ContextPanel from "@/components/ContextPanel";
import {
  CheckIcon,
  ClockIcon,
  KeyboardIcon,
  MicIcon,
  PauseIcon,
  SparklesIcon,
  StatusDot,
} from "@/components/Icons";
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
  const [inputMode, setInputMode] = useState<"type" | "speak">("type");
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
        return await authedFetch(getToken, `/conversations/${encodeURIComponent(storedId)}`, { signal }) as SessionData;
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
      if (data) authedFetch(getToken, `/conversations/scenarios/${encodeURIComponent(data.scenario)}`, { signal })
        .then(detail => { if (!signal.aborted) setScenarioDetail(detail); }).catch(() => {});
    }).catch(err => { if (!signal.aborted) setError(err.message); })
      .finally(() => { if (!signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [isSignedIn, getToken, userId]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [session?.turns]);

  async function refreshSession(id: string, signal?: AbortSignal) {
    const data = await authedFetch(getToken, `/conversations/${encodeURIComponent(id)}`, { signal });
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
      await authedFetch(getToken, `/conversations/${encodeURIComponent(session.id)}/respond`, {
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
          for (const streamEvent of parser.push(decoder.decode(value, { stream: true }))) {
            const payload = parseVoiceEvent(streamEvent);
            if (payload.event === "error") throw new Error(payload.message);
            if (payload.event === "unknown") continue;
            if (payload.event === "warning" && mounted.current) setError(payload.data);
            if (payload.event === "transcription" && mounted.current) setLiveTranscript(payload.data);
            if (payload.event === "mic_quality" && mounted.current) setMicQuality(payload.data);
            if (payload.event === "ai_response") {
              // The turn is already committed; show text before speech synthesis finishes.
              await refreshSession(session.id, controller.signal);
              if (mounted.current) { setLiveTranscript(""); setAiBusy(false); }
            }
            if (payload.event === "audio" && mounted.current) {
              try { await voice.play(payload.data); }
              catch { setError("Your response was saved, but audio playback failed."); }
            }
            if (payload.event === "done") finished = true;
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

  const completeConversation = useCallback(async (reason?: "time_expired") => {
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
      const data = await authedFetch(getToken, `/conversations/${encodeURIComponent(session.id)}/complete`, {
        method: "POST",
        signal: controller.signal,
        body: reason ? JSON.stringify({ reason }) : undefined,
      });
      if (!mounted.current) return;
      if (data.report_id) {
        localStorage.removeItem(`${SESSION_KEY}:${userId}`);
        router.push(`/reports/${encodeURIComponent(String(data.report_id))}`);
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

  function selectMode(mode: "type" | "speak") {
    if (mode === "type" && isRecording) voice.stop();
    setInputMode(mode);
  }

  const partnerName = scenarioDetail?.persona?.name || "Your partner";
  const partnerInitial = partnerName.charAt(0);
  const scenarioTitle = session
    ? scenarioNames[session.scenario] || session.scenario
    : "Conversation practice";

  return (
    <AuthGate title="Conversation practice">
      <main className="w-full bg-canvas px-5 pb-16 pt-8 sm:px-8 lg:px-[38px]">
        {error && (
          <div role="alert" className="mb-6 rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {canRetryVoice && pendingVoice.current && (
          <button
            type="button"
            className="mb-6 text-[13px] font-bold text-forest underline"
            disabled={sending || isRecording || completing}
            onClick={() => { if (pendingVoice.current) void sendVoiceMessage(pendingVoice.current.blob); }}
          >
            Retry recorded message
          </button>
        )}

        <Link href="/scenarios" className="text-[14px] text-muted hover:text-forest">
          ← Back to scenarios
        </Link>

        <div className="mt-4 flex flex-wrap items-start justify-between gap-6">
          <div>
            <h1 className="font-display text-[30px] font-semibold leading-[1.4] text-ink">
              {loading ? "Preparing your practice…" : scenarioTitle}
            </h1>
            <p className="mt-2 text-[14px] text-muted">
              {scenarioDetail?.difficulty
                ? `${scenarioDetail.difficulty} · 5-minute guided conversation`
                : "Guided practice · 5-minute conversation"}
            </p>
          </div>
          <div
            className={`flex w-[206px] shrink-0 flex-col items-center gap-[5px] rounded-xl border px-5 py-4 ${
              timeLeft <= 30
                ? "border-red-200 bg-red-50 text-red-700"
                : timeLeft <= 60
                  ? "border-amber-200 bg-amber-50 text-amber-800"
                  : "border-line bg-mint text-forest"
            }`}
            title="5-minute scenario limit"
          >
            <div className="flex w-full items-center justify-between">
              <ClockIcon size={22} />
              <span className="font-display text-[32px] font-semibold leading-none">
                {timeLeft === 0 ? "0:00" : formatTime(timeLeft)}
              </span>
              <PauseIcon size={20} />
            </div>
            <span className="text-[10px] text-muted">Time remaining</span>
          </div>
        </div>

        <div className="mt-6 flex flex-col items-start gap-6 lg:flex-row">
          <div className="w-full lg:w-[306px] lg:shrink-0">
            {scenarioDetail ? (
              <ContextPanel scenario={scenarioDetail} />
            ) : (
              <GuidancePlaceholder loading={loading} />
            )}
            <MicQualityBadge quality={micQuality} />
          </div>

          <section className="flex min-h-[690px] w-full flex-col overflow-hidden rounded-2xl border border-line bg-white">
            <div className="flex items-center gap-4 px-7 py-5">
              <div className="flex size-[52px] shrink-0 items-center justify-center rounded-[26px] bg-line text-[28px] font-semibold leading-none text-ink">
                {partnerInitial}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-[18px] font-medium leading-6 text-ink">{partnerName}</p>
                <div className="mt-1 flex items-center gap-[7px]">
                  <StatusDot className="text-forest" />
                  <span className="text-[12px] text-muted">Your practice partner</span>
                </div>
              </div>
              <span className="shrink-0 rounded border border-line px-3 py-2 text-[10px] text-muted">
                Guided simulation
              </span>
            </div>

            <div className="h-px bg-line" />

            <div className="flex min-h-[360px] flex-1 flex-col gap-10 overflow-y-auto px-[30px] py-[30px]">
              <p className="text-center text-[12px] text-muted">
                A small moment to try something new. You&apos;ve got this.
              </p>

              {loading && (
                <>
                  <div className="h-16 rounded-xl bg-mint" />
                  <div className="h-24 rounded-xl bg-mint-deep" />
                </>
              )}

              {!loading && !session && (
                <div className="mx-auto flex w-full max-w-[520px] flex-col gap-3 rounded-xl border border-line bg-mint px-6 py-8 text-center">
                  <p className="font-display text-[18px] font-semibold text-ink">
                    Your conversation starts here
                  </p>
                  <p className="text-[13px] leading-5 text-muted">
                    Choose a scenario to meet your practice partner. Your opening message and guidance will appear here.
                  </p>
                  <Link
                    href="/scenarios"
                    className="mx-auto rounded-lg bg-forest px-5 py-3 text-[13px] font-bold text-white"
                  >
                    Choose a scenario
                  </Link>
                </div>
              )}

              {session && session.turns.length === 0 && (
                <p className="text-center text-[13px] text-muted">The conversation starts here…</p>
              )}

              {session?.turns.map((turn) =>
                turn.speaker === "user" ? (
                  <div key={turn.id} className="flex justify-end">
                    <div className="max-w-[85%] rounded-2xl bg-forest px-5 py-3 text-[14px] leading-relaxed text-white">
                      {turn.content}
                    </div>
                  </div>
                ) : (
                  <div key={turn.id} className="flex items-start gap-[14px]">
                    <div className="flex size-[35px] shrink-0 items-center justify-center rounded-[17px] bg-line text-[19px] font-semibold text-ink">
                      {partnerInitial}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="mb-2 text-[12px] text-muted">{partnerName}</p>
                      <div className="rounded-br-[14px] rounded-tl-[14px] rounded-tr-[14px] bg-mint px-[22px] py-[17px] text-[16px] leading-[1.75] text-ink">
                        {turn.content}
                      </div>
                    </div>
                  </div>
                )
              )}

              {(isRecording || sending) && liveTranscript && (
                <div className="flex justify-end">
                  <div className="max-w-[85%] rounded-2xl bg-forest px-5 py-3 text-[14px] italic leading-relaxed text-white">
                    {liveTranscript}
                    <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-white/60 align-middle" />
                  </div>
                </div>
              )}

              {(aiBusy || isRecording) && (
                <div className="flex justify-center py-2">
                  <span className="inline-flex items-center gap-2 text-[13px] text-muted">
                    <span className="flex gap-1">
                      <span className="size-1.5 animate-bounce rounded-full bg-muted" />
                      <span className="size-1.5 animate-bounce rounded-full bg-muted [animation-delay:150ms]" />
                      <span className="size-1.5 animate-bounce rounded-full bg-muted [animation-delay:300ms]" />
                    </span>
                    {isRecording ? "Listening…" : "Responding…"}
                  </span>
                </div>
              )}

              <div ref={chatEndRef} />
            </div>

            {timeLeft <= 0 && (
              <div className="mx-6 mb-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-[12px] text-amber-800">
                5 minutes are up! Automatically completing your conversation and generating feedback…
              </div>
            )}

            <div className="h-px bg-line" />

            <div className="flex flex-col gap-2 px-[26px] py-3">
              <div className="flex items-center gap-[14px]">
                <button
                  type="button"
                  onClick={() => selectMode("speak")}
                  className={`flex h-10 items-center gap-2 text-[14px] ${
                    inputMode === "speak" ? "font-medium text-forest" : "text-muted"
                  }`}
                >
                  <MicIcon size={20} />
                  Speak
                </button>
                <button
                  type="button"
                  onClick={() => selectMode("type")}
                  className={`flex h-10 items-center gap-2 rounded-[5px] px-3 text-[14px] ${
                    inputMode === "type" ? "bg-mint font-medium text-forest" : "text-muted"
                  }`}
                >
                  <KeyboardIcon size={20} />
                  Type
                </button>
                <p className="ml-auto text-right text-[10px] text-muted">No perfect words needed.</p>
              </div>

              {inputMode === "type" ? (
                <div className="flex h-16 items-center gap-[30px] rounded-[9px] border border-line pl-[18px] pr-[14px]">
                  <input
                    aria-label="Your response"
                    maxLength={8000}
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
                    placeholder={timeLeft <= 0 || !session ? "Choose a scenario to begin…" : "Type your response…"}
                    disabled={!session || sending || isRecording || voice.starting || completing || timeLeft <= 0}
                    className="min-w-0 flex-1 bg-transparent text-[14px] text-ink outline-none placeholder:text-muted disabled:opacity-50"
                  />
                  <button
                    type="button"
                    onClick={sendMessage}
                    aria-label="Send response"
                    disabled={!message.trim() || sending || isRecording || voice.starting || completing || timeLeft <= 0}
                    className="flex h-11 w-[46px] shrink-0 items-center justify-center rounded-lg bg-forest text-[16px] font-bold text-white disabled:opacity-40"
                  >
                    ↑
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={toggleRecording}
                  disabled={!session || sending || completing || voice.starting || timeLeft <= 0}
                  className={`flex h-16 items-center justify-center gap-2 rounded-lg border text-[14px] font-medium disabled:opacity-40 ${
                    isRecording
                      ? "animate-pulse border-red-200 bg-red-50 text-red-700"
                      : "border-line bg-mint text-forest"
                  }`}
                >
                  <MicIcon size={20} />
                  {isRecording ? "Stop recording" : "Start speaking"}
                </button>
              )}

              <div className="flex items-center gap-4">
                <button
                  type="button"
                  onClick={() => completeConversation()}
                  disabled={!session || completing || sending || isRecording || voice.starting || !session?.turns.some(t => t.speaker === "user")}
                  className="flex h-9 shrink-0 items-center justify-center rounded-md border border-forest px-[22px] text-[12px] font-bold text-forest disabled:opacity-40"
                >
                  {completing ? (timeLeft <= 0 ? "Time's up! Generating…" : "Completing…") : "End conversation"}
                </button>
                <button
                  type="button"
                  onClick={newConversation}
                  disabled={sending || isRecording || voice.starting || completing}
                  className="shrink-0 text-[12px] text-muted underline disabled:opacity-40"
                >
                  New conversation
                </button>
                <p className="ml-auto hidden text-right text-[11px] text-muted sm:block">
                  You can switch between typing and speaking at any time.
                </p>
              </div>
            </div>
          </section>
        </div>
      </main>
    </AuthGate>
  );
}

function GuidancePlaceholder({ loading }: { loading: boolean }) {
  return (
    <aside className="flex w-full flex-col gap-7">
      <section className="flex flex-col gap-5">
        <h2 className="text-[12px] font-bold tracking-[1.2px] text-muted">MEET YOUR PARTNER</h2>
        <div className="flex items-center gap-[14px]">
          <div className="size-[62px] shrink-0 rounded-full bg-line" />
          <div>
            <p className="text-[18px] font-medium text-ink">
              {loading ? "Finding your partner…" : "Your practice partner"}
            </p>
            <p className="mt-1 text-[11px] text-muted">
              {loading ? "Loading scenario" : "Choose a scenario to meet your partner"}
            </p>
          </div>
        </div>
        <div className="h-10 rounded bg-mint" />
      </section>
      <section className="flex flex-col gap-3 rounded-xl border border-line bg-mint p-6">
        <SparklesIcon size={24} className="text-forest" />
        <h2 className="text-[18px] font-bold leading-6 text-ink">Your conversation goal</h2>
        <p className="text-[14px] leading-6 text-muted">
          {loading ? "Loading your goal…" : "Your goal will appear here once you choose a scenario."}
        </p>
      </section>
      <section>
        <h2 className="text-[17px] font-medium leading-6 text-ink">A few gentle pointers</h2>
        <ul className="mt-2 flex flex-col gap-2">
          {["Start with a simple hello and your name.", "Ask an open-ended question and be curious.", "Share a little about your work or interests."].map((tip) => (
            <li key={tip} className="flex items-start gap-[14px]">
              <CheckIcon size={18} className="mt-0.5 shrink-0 text-forest" />
              <span className="text-[12px] leading-[1.8] text-muted">{tip}</span>
            </li>
          ))}
        </ul>
      </section>
    </aside>
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
