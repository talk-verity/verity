"use client";

import { useEffect, useRef, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { useRouter } from "next/navigation";
import AuthGate from "@/components/AuthGate";
import ContextPanel from "@/components/ContextPanel";
import {
  authedFetch,
  API,
  SESSION_KEY,
  type Scenario,
  type ScenarioDetail,
  type SessionData,
  type Turn,
} from "@/lib/api";

export default function ConversationPage() {
  const { isSignedIn, getToken } = useAuth();
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
  const [isRecording, setIsRecording] = useState(false);
  const [liveTranscript, setLiveTranscript] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [completing, setCompleting] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const interimLastSentRef = useRef(0);
  const interimInFlightRef = useRef(false);

  useEffect(() => {
    if (!isSignedIn) return;
    authedFetch(getToken, "/conversations/scenarios")
      .then((data) => setScenarioNames(Object.fromEntries((data as Scenario[]).map((s) => [s.id, s.name]))))
      .catch(() => {});

    const storedId = localStorage.getItem(SESSION_KEY);
    const load = async () => {
      if (!storedId) return null;
      try {
        const data = await authedFetch(getToken, `/conversations/${storedId}`);
        if (data?.id) return data as SessionData;
      } catch {}
      localStorage.removeItem(SESSION_KEY);
      return null;
    };
    load()
      .then((data) => {
        if (data) {
          setSession(data);
          authedFetch(getToken, `/conversations/scenarios/${data.scenario}`)
            .then((detail) => setScenarioDetail(detail as ScenarioDetail))
            .catch(() => {});
        }
      })
      .finally(() => setLoading(false));
  }, [isSignedIn, getToken]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [session?.turns]);

  async function sendMessage() {
    if (!message.trim() || !session || sending || isRecording) return;
    const content = message.trim();
    setMessage("");
    setSending(true);
    setAiBusy(true);
    setError(null);

    const userTurn: Turn = {
      id: "user-" + Date.now(),
      speaker: "user",
      content,
      created_at: new Date().toISOString(),
    };
    setSession((prev) => (prev ? { ...prev, turns: [...prev.turns, userTurn] } : prev));

    try {
      const data: Turn = await authedFetch(getToken, `/conversations/${session.id}/respond`, {
        method: "POST",
        body: JSON.stringify({ content }),
      });
      setSession((prev) => (prev ? { ...prev, turns: [...prev.turns, data] } : prev));
    } catch {
      setError("Your message didn't get through — check the backend and try again.");
      setSession((prev) =>
        prev ? { ...prev, turns: prev.turns.filter((t) => t.id !== userTurn.id) } : prev
      );
    }
    setSending(false);
    setAiBusy(false);
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
    setError(null);
    try {
      if (!audioCtxRef.current || audioCtxRef.current.state === "closed") {
        audioCtxRef.current = new AudioContext();
      }
      if (audioCtxRef.current.state === "suspended") {
        await audioCtxRef.current.resume();
      }
      let stream: MediaStream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      } catch {
        setError("Microphone access was denied. Check browser permissions and try again.");
        return;
      }
      streamRef.current = stream;
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];
      interimLastSentRef.current = 0;
      setLiveTranscript("");

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data);
          maybeSendInterim();
        }
      };

      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
        const blob = new Blob(audioChunksRef.current, { type: recorder.mimeType });
        sendVoiceMessage(blob);
      };

      recorder.start(1000);
      setIsRecording(true);
    } catch (err) {
      setError("Could not start recording.");
      console.error("Recording failed:", err);
    }
  }

  function stopRecording() {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  }

  async function maybeSendInterim() {
    const recorder = mediaRecorderRef.current;
    if (!recorder || recorder.state !== "recording") return;
    const now = Date.now();
    if (interimInFlightRef.current || now - interimLastSentRef.current < 2000) return;
    interimLastSentRef.current = now;
    interimInFlightRef.current = true;
    try {
      const token = await getToken();
      if (!token) return;
      const blob = new Blob(audioChunksRef.current, { type: recorder.mimeType });
      const formData = new FormData();
      formData.append("file", blob, "interim." + (blob.type.includes("webm") ? "webm" : "ogg"));
      const res = await fetch(`${API}/voice/stt`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      if (!res.ok) return;
      const data = await res.json();
      if (mediaRecorderRef.current === recorder && recorder.state === "recording" && data?.text) {
        setLiveTranscript(data.text);
      }
    } catch {
      // transient interim failure — ignore, final transcription still runs
    } finally {
      interimInFlightRef.current = false;
    }
  }

  async function sendVoiceMessage(blob: Blob) {
    if (!session) return;
    setSending(true);
    setAiBusy(true);
    setError(null);

    const token = await getToken();
    if (!token) {
      setSending(false);
      setAiBusy(false);
      return;
    }

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
        setError("Voice request failed.");
        setSending(false);
        setAiBusy(false);
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
              setLiveTranscript("");
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
            } else if (currentEvent === "mic_quality") {
              setMicQuality(JSON.parse(raw).data);
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
                    const buf = await ctx.decodeAudioData(binary.buffer);
                    const source = ctx.createBufferSource();
                    source.buffer = buf;
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
      setError("Voice conversation failed — try typing instead.");
      console.error("Voice converse failed:", err);
    }
    setSending(false);
    setAiBusy(false);
  }

  async function completeConversation() {
    if (!session || completing) return;
    setCompleting(true);
    setError(null);
    try {
      const token = await getToken();
      const res = await fetch(`${API}/conversations/${session.id}/complete`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Could not complete conversation");
      const data = await res.json();
      if (data.report_id) {
        localStorage.removeItem(SESSION_KEY);
        router.push(`/reports/${data.report_id}`);
      }
    } catch {
      setError("Failed to complete the conversation. Try again.");
      setCompleting(false);
    }
  }

  function newConversation() {
    setSession(null);
    setMessage("");
    setError(null);
    setLiveTranscript("");
    localStorage.removeItem(SESSION_KEY);
  }

  return (
    <AuthGate>
      <main className="flex-1 w-full mx-auto max-w-5xl px-6 py-6 flex flex-col">
        {error && (
          <div className="mb-4 rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
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
                <h2 className="text-lg font-medium">
                  {scenarioNames[session.scenario] || session.scenario}
                </h2>
                <div className="flex gap-3">
                  <button
                    onClick={completeConversation}
                    disabled={completing || session.turns.length === 0}
                    className="text-sm text-emerald-600 hover:text-emerald-700 font-medium disabled:opacity-40"
                  >
                    {completing ? "Completing…" : "Complete & get feedback"}
                  </button>
                  <button
                    onClick={newConversation}
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
                {isRecording && liveTranscript && (
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

              <div className="flex gap-2 pb-6">
                <input
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
                  placeholder="Type your response..."
                  disabled={sending || isRecording || completing}
                  className="flex-1 border border-neutral-200 rounded-2xl px-4 py-2.5 text-sm outline-none focus:border-neutral-400 disabled:opacity-50"
                />
                <button
                  onClick={sendMessage}
                  disabled={!message.trim() || sending || isRecording || completing}
                  className="bg-neutral-900 text-white rounded-2xl px-5 py-2.5 text-sm font-medium disabled:opacity-40"
                >
                  Send
                </button>
                <button
                  onClick={toggleRecording}
                  disabled={sending || completing}
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
