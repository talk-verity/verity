"use client";

import { useEffect, useState } from "react";
import { useAuth, useUser } from "@clerk/nextjs";
import Link from "next/link";
import { useRouter } from "next/navigation";
import AuthGate from "@/components/AuthGate";
import ScenarioSymbol, { symbolForScenario } from "@/components/ScenarioSymbols";
import {
  authedFetch,
  SESSION_KEY,
  type ReportData,
  type Scenario,
} from "@/lib/api";
import { PRACTICE_GOALS, readGoals } from "@/lib/goals";

export default function DashboardPage() {
  const { isSignedIn, getToken, userId } = useAuth();
  const { user } = useUser();
  const router = useRouter();
  const [reports, setReports] = useState<ReportData[]>([]);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [activeSession, setActiveSession] = useState<string | null>(null);
  const [goals, setGoals] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [startingId, setStartingId] = useState<string | null>(null);
  const [latestFeedback, setLatestFeedback] = useState<ReportData | null>(null);

  useEffect(() => {
    if (!isSignedIn) return;
    const controller = new AbortController();
    const signal = controller.signal;
    Promise.all([
      authedFetch(getToken, "/reports", { signal }),
      authedFetch(getToken, "/conversations/scenarios", { signal }),
    ])
      .then(async ([r, s]) => {
        if (signal.aborted) return;
        const readyReports = (r as ReportData[]).filter((report) => report.status === "ready");
        setActiveSession(localStorage.getItem(`${SESSION_KEY}:${userId}`));
        setReports(r as ReportData[]);
        setScenarios(s as Scenario[]);
        setGoals(readGoals());
        if (readyReports.length) {
          const detail = await authedFetch(getToken, `/reports/${encodeURIComponent(String(readyReports[0].id))}`, { signal });
          if (!signal.aborted) setLatestFeedback(detail);
        }
      })
      .catch((err) => { if (!signal.aborted) setError(err.message); })
      .finally(() => { if (!signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [isSignedIn, getToken, userId]);

  async function startConversation(scenario: Scenario) {
    setStartingId(scenario.id);
    setError(null);
    try {
      const data = await authedFetch(getToken, "/conversations", {
        method: "POST",
        body: JSON.stringify({ scenario_id: scenario.id }),
      });
      localStorage.setItem(`${SESSION_KEY}:${userId}`, data.id);
      router.push("/conversation");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start conversation");
      setStartingId(null);
    }
  }

  const readyCount = reports.filter((r) => r.status === "ready").length;
  const practicedNames = reports.map((r) => r.title);
  const recentScenarios = scenarios.filter((s) => practicedNames.includes(s.name));
  const recent = (recentScenarios.length ? recentScenarios : scenarios).slice(0, 2);
  const recommended = scenarios.filter((s) => !recent.some((r) => r.id === s.id)).slice(0, 2);
  const selectedGoals = PRACTICE_GOALS.filter((g) => goals.includes(g.id));
  const firstName = user?.firstName || "there";

  return (
    <AuthGate title="Home">
      <main className="w-full px-5 pb-16 pt-9 sm:px-8 lg:px-[38px]">
        <section className="flex flex-col gap-4 pb-9">
          <p className="text-[11px] font-bold tracking-[1px] text-muted">CONVERSATION PRACTICE</p>
          <h1 className="font-display text-[34px] font-semibold leading-tight text-ink">
            Welcome back, {firstName}.
          </h1>
          <p className="text-[17px] text-muted">Make time for the conversations that matter.</p>
        </section>

        {error && (
          <div role="alert" className="mb-8 rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {activeSession && (
          <Link
            href="/conversation"
            className="mb-8 flex items-center justify-between rounded-xl border border-line bg-white px-5 py-4 transition-colors hover:border-forest"
          >
            <span>
              <span className="block text-[15px] font-medium text-ink">You have an active conversation</span>
              <span className="mt-1 block text-[13px] text-muted">Resume it to keep practicing.</span>
            </span>
            <span className="text-[13px] font-bold text-forest">Resume →</span>
          </Link>
        )}

        {latestFeedback?.content?.recommendations?.[0] && (
          <Link
            href={`/reports/${encodeURIComponent(String(latestFeedback.id))}`}
            className="mb-8 flex items-center justify-between rounded-xl border border-line bg-mint px-5 py-4 transition-colors hover:border-forest"
          >
            <span>
              <span className="block text-[15px] font-medium text-ink">Your next practice</span>
              <span className="mt-1 block text-[13px] text-muted">{latestFeedback.content.recommendations[0]}</span>
            </span>
            <span className="shrink-0 pl-4 text-[13px] font-bold text-forest">Review feedback →</span>
          </Link>
        )}

        <div className="flex flex-col gap-10 xl:flex-row xl:items-start">
          <div className="min-w-0 flex-1">
            <ScenarioSection
              title="Recently practiced"
              note={readyCount === 0 ? "No sessions completed yet — choose a scenario to begin." : undefined}
              scenarios={recent}
              loading={loading}
              startingId={startingId}
              onStart={startConversation}
            />
            <div className="mt-9">
              <ScenarioSection
                title="Recommended"
                note="Chosen from your real practice scenarios."
                scenarios={recommended}
                loading={loading}
                startingId={startingId}
                onStart={startConversation}
              />
            </div>
          </div>

          <aside className="flex w-full shrink-0 flex-col gap-[18px] xl:w-[304px]">
            <SummaryCard
              metric="Conversations practiced"
              value={loading ? "…" : readyCount}
              summary={readyCount ? "Keep the momentum" : "Ready when you are"}
              detail="Your completed conversations will appear here."
            />
            <SummaryCard
              metric="Minutes practiced"
              value="—"
              summary="Not tracked yet"
              detail="Practice duration is not measured in this version."
            />
            <div className="flex flex-col gap-[10px] rounded-xl border border-line bg-mint px-[22px] py-5">
              <h2 className="text-[17px] font-bold text-ink">Your goals</h2>
              {selectedGoals.length ? (
                <ul className="flex flex-col gap-2 text-[13px] text-muted">
                  {selectedGoals.map((goal) => (
                    <li key={goal.id} className="flex items-start gap-2">
                      <span className="mt-[7px] size-[6px] shrink-0 rounded-full bg-forest" />
                      <span>{goal.title}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-[13px] leading-5 text-muted">
                  Your personal goals will appear here once you complete onboarding.
                </p>
              )}
              <Link href="/scenarios" className="pt-1 text-[13px] font-bold text-forest">
                {selectedGoals.length ? "Update your goals →" : "Complete onboarding →"}
              </Link>
            </div>
          </aside>
        </div>
      </main>
    </AuthGate>
  );
}

function ScenarioSection({
  title,
  note,
  scenarios,
  loading,
  startingId,
  onStart,
}: {
  title: string;
  note?: string;
  scenarios: Scenario[];
  loading: boolean;
  startingId: string | null;
  onStart: (scenario: Scenario) => void;
}) {
  return (
    <section>
      <div className="mb-[14px] flex items-baseline justify-between gap-4">
        <h2 className="font-display text-[20px] font-semibold text-ink">{title}</h2>
        <Link href="/scenarios" className="shrink-0 text-[13px] font-bold text-forest">
          View all scenarios →
        </Link>
      </div>
      {note && <p className="mb-3 text-[12px] text-muted">{note}</p>}
      <div className="grid gap-5 md:grid-cols-2">
        {loading
          ? [0, 1].map((i) => <ScenarioModuleSkeleton key={i} />)
          : scenarios.map((scenario) => (
              <ScenarioModule
                key={scenario.id}
                scenario={scenario}
                starting={startingId === scenario.id}
                action={startingId === scenario.id ? "Starting…" : "Start practice →"}
                onStart={onStart}
              />
            ))}
      </div>
    </section>
  );
}

function ScenarioModule({
  scenario,
  action,
  starting,
  onStart,
}: {
  scenario: Scenario;
  action: string;
  starting: boolean;
  onStart: (scenario: Scenario) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onStart(scenario)}
      disabled={starting}
      className="flex min-h-[246px] w-full flex-col gap-[10px] rounded-[14px] border border-line bg-white px-[22px] py-[18px] text-left transition-colors hover:border-forest disabled:opacity-60"
    >
      <div className="flex h-[76px] items-center justify-between gap-4">
        <span className="text-[12px] leading-[1.45] text-muted">5 min · Guided practice</span>
        <ScenarioSymbol kind={symbolForScenario(scenario.id)} />
      </div>
      <span className="font-display text-[20px] font-semibold leading-[1.45] text-ink">{scenario.name}</span>
      <span className="text-[14px] leading-[1.45] text-muted">{scenario.description}</span>
      <span className="mt-auto text-[13px] font-bold text-forest">{action}</span>
    </button>
  );
}

function ScenarioModuleSkeleton() {
  return (
    <div className="flex min-h-[246px] flex-col gap-[10px] rounded-[14px] border border-line bg-white px-[22px] py-[18px]">
      <div className="flex h-[76px] items-center justify-between">
        <div className="h-3 w-32 rounded bg-mint" />
        <div className="size-[72px] rounded bg-mint" />
      </div>
      <div className="h-5 w-40 rounded bg-mint" />
      <div className="h-3 w-full rounded bg-mint" />
      <div className="h-3 w-2/3 rounded bg-mint" />
      <div className="mt-auto h-3 w-28 rounded bg-mint-deep" />
    </div>
  );
}

function SummaryCard({
  metric,
  value,
  summary,
  detail,
}: {
  metric: string;
  value: string | number;
  summary: string;
  detail: string;
}) {
  return (
    <div className="flex min-h-[205px] flex-col gap-[10px] rounded-xl border border-line bg-white p-5">
      <p className="text-[15px] font-bold text-ink">{metric}</p>
      <p className="font-display text-[30px] font-semibold leading-none text-forest">{value}</p>
      <p className="text-[12px] font-medium text-forest">{summary}</p>
      <p className="text-[13px] leading-5 text-muted">{detail}</p>
    </div>
  );
}
