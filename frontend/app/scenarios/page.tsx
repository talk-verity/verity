"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import Link from "next/link";
import AuthGate from "@/components/AuthGate";
import ScenarioSymbol, { symbolForScenario } from "@/components/ScenarioSymbols";
import { authedFetch, SESSION_KEY, type Scenario } from "@/lib/api";
import { PRACTICE_GOALS, readGoals, writeGoals } from "@/lib/goals";

export default function ScenariosPage() {
  const { isSignedIn, getToken, userId } = useAuth();
  const router = useRouter();
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [creatingId, setCreatingId] = useState<string | null>(null);

  useEffect(() => {
    if (!isSignedIn) return;
    Promise.resolve().then(() => setSelected(readGoals()));
    authedFetch(getToken, "/conversations/scenarios")
      .then((data) => setScenarios(data as Scenario[]))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [isSignedIn, getToken, userId]);

  function toggleGoal(id: string) {
    setSaved(false);
    setSelected((current) =>
      current.includes(id)
        ? current.filter((goal) => goal !== id)
        : current.length < 3
          ? [...current, id]
          : current,
    );
  }

  function saveGoals() {
    writeGoals(selected);
    setSaved(true);
  }

  async function startConversation(scenario: Scenario) {
    setCreatingId(scenario.id);
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
      setCreatingId(null);
    }
  }

  const selectedGoalTitles = PRACTICE_GOALS.filter((g) => selected.includes(g.id)).map((g) => g.title);
  const prioritizedScenarioIds = PRACTICE_GOALS
    .filter((g) => selected.includes(g.id))
    .flatMap((g) => g.scenarioIds);
  const orderedScenarios = [...scenarios].sort((a, b) => {
    const aIndex = prioritizedScenarioIds.indexOf(a.id);
    const bIndex = prioritizedScenarioIds.indexOf(b.id);
    return (aIndex < 0 ? Number.MAX_SAFE_INTEGER : aIndex) -
      (bIndex < 0 ? Number.MAX_SAFE_INTEGER : bIndex);
  });

  return (
    <AuthGate surface="header" title="Practice">
      <main className="w-full bg-canvas px-6 py-8 lg:px-[176px] lg:py-8">
        <Link href="/" className="text-[13px] text-muted hover:text-forest">
          ← Back to home
        </Link>

        <section className="mt-5 flex flex-col gap-[10px]">
          <p className="text-[11px] font-bold tracking-[1px] text-forest">YOUR PRACTICE GOALS</p>
          <h1 className="font-display text-[34px] font-semibold leading-[1.4] text-ink">
            What would you like to work on?
          </h1>
          <p className="max-w-[1088px] text-[16px] leading-6 text-muted">
            Choose the conversations you want to feel more confident in. I&apos;ll help you find a place to start.
          </p>
        </section>

        {error && (
          <div role="alert" className="mt-6 rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="mt-8 flex flex-col gap-8 xl:flex-row xl:items-start">
          <section className="min-w-0 flex-1">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-[15px] font-medium text-ink">Choose up to 3 goals</h2>
              <p className="text-[13px] text-muted">{selected.length} selected</p>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              {PRACTICE_GOALS.map((goal) => {
                const isSelected = selected.includes(goal.id);
                return (
                  <button
                    key={goal.id}
                    type="button"
                    aria-pressed={isSelected}
                    onClick={() => toggleGoal(goal.id)}
                    className={`flex min-h-[125px] gap-[14px] rounded-xl border bg-white p-5 text-left transition-colors ${
                      isSelected ? "border-forest bg-mint-deep" : "border-line hover:border-forest"
                    }`}
                  >
                    <span
                      className={`mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-[5px] border-[1.5px] ${
                        isSelected ? "border-forest bg-forest text-lime" : "border-[#a6b5a8] bg-white"
                      }`}
                    >
                      {isSelected ? <span className="text-[11px] leading-none">✓</span> : null}
                    </span>
                    <span className="min-w-0">
                      <span className="block font-display text-[17px] font-semibold leading-[1.4] text-ink">
                        {goal.title}
                      </span>
                      <span className="mt-2 block text-[13px] leading-[1.5] text-muted">
                        {goal.summary}
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
          </section>

          <aside className="flex w-full shrink-0 flex-col gap-[22px] rounded-2xl bg-forest p-7 text-white xl:w-[336px]">
            <p className="text-[11px] font-bold tracking-[1px] text-lime">PERSONALIZED FOR YOU</p>
            <h2 className="font-display text-[26px] font-semibold leading-[1.4]">
              Your practice.
              <br />
              Your priorities.
            </h2>
            <p className="text-[15px] leading-6 text-[#d4e1d7]">
              Your goals help shape the scenarios you see on your home screen.
            </p>
            <div className="flex min-h-[116px] flex-col gap-2 rounded-[10px] bg-forest-soft px-5 py-[18px]">
              <p className="text-[15px] font-medium text-white">
                {selectedGoalTitles.length ? "Your selected goals" : "Your goals will appear here"}
              </p>
              {selectedGoalTitles.length ? (
                <ul className="flex flex-col gap-1 text-[13px] text-[#d4e1d7]">
                  {selectedGoalTitles.map((title) => <li key={title}>· {title}</li>)}
                </ul>
              ) : (
                <p className="text-[13px] text-[#d4e1d7]">
                  Choose a goal on the left to start making practice your own.
                </p>
              )}
            </div>
            <p className="text-[12px] text-[#d4e1d7]">You can change your goals anytime.</p>
          </aside>
        </div>

        <div className="mt-8 flex flex-col gap-4 rounded-xl border border-line bg-white px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-[14px] font-medium text-ink">Make space for the conversations that matter.</p>
            <p className="mt-1 text-[12px] text-muted">
              {saved ? "Your goals are saved. Your home screen is personalized." : "Select at least one goal to continue."}
            </p>
          </div>
          <button
            type="button"
            onClick={saveGoals}
            disabled={selected.length === 0}
            className="h-[54px] w-full shrink-0 rounded-lg bg-forest px-[22px] text-[16px] font-bold text-white disabled:bg-line disabled:text-muted sm:w-[200px]"
          >
            Save my goals
          </button>
        </div>

        <section className="mt-14">
          <div className="mb-4 flex items-baseline justify-between gap-4">
            <h2 className="font-display text-[20px] font-semibold text-ink">
              Available practice scenarios
            </h2>
            <p className="text-[13px] text-muted">Real scenarios from your Delphi account</p>
          </div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {loading
              ? [0, 1, 2].map((i) => <ScenarioCardSkeleton key={i} />)
              : orderedScenarios.map((scenario) => (
                  <ScenarioCard
                    key={scenario.id}
                    scenario={scenario}
                    starting={creatingId === scenario.id}
                    onStart={startConversation}
                  />
                ))}
          </div>
          {!loading && scenarios.length === 0 && !error && (
            <div className="mt-4 rounded-xl border border-line bg-white p-6 text-[13px] text-muted">
              No scenarios available — is the backend running?
            </div>
          )}
        </section>
      </main>
    </AuthGate>
  );
}

function ScenarioCard({
  scenario,
  starting,
  onStart,
}: {
  scenario: Scenario;
  starting: boolean;
  onStart: (scenario: Scenario) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onStart(scenario)}
      disabled={starting}
      className="flex min-h-[210px] flex-col gap-3 rounded-xl border border-line bg-white p-5 text-left transition-colors hover:border-forest disabled:opacity-60"
    >
      <div className="flex items-center justify-between">
        <ScenarioSymbol kind={symbolForScenario(scenario.id)} />
        <span className="text-[11px] capitalize text-muted">{scenario.difficulty}</span>
      </div>
      <span className="font-display text-[18px] font-semibold text-ink">{scenario.name}</span>
      <span className="text-[13px] leading-5 text-muted">{scenario.description}</span>
      <span className="mt-auto text-[13px] font-bold text-forest">
        {starting ? "Starting…" : "Start practice →"}
      </span>
    </button>
  );
}

function ScenarioCardSkeleton() {
  return (
    <div className="flex min-h-[210px] flex-col gap-3 rounded-xl border border-line bg-white p-5">
      <div className="size-[72px] rounded bg-mint" />
      <div className="h-4 w-2/3 rounded bg-mint" />
      <div className="h-3 w-full rounded bg-mint" />
      <div className="h-3 w-4/5 rounded bg-mint" />
      <div className="mt-auto h-3 w-28 rounded bg-mint-deep" />
    </div>
  );
}
