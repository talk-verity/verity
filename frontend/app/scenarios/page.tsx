"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import AuthGate from "@/components/AuthGate";
import { authedFetch, SESSION_KEY, type Scenario } from "@/lib/api";

export default function ScenariosPage() {
  const { isSignedIn, getToken } = useAuth();
  const router = useRouter();
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creatingId, setCreatingId] = useState<string | null>(null);

  useEffect(() => {
    if (!isSignedIn) return;
    authedFetch(getToken, "/conversations/scenarios")
      .then((data) => setScenarios(data as Scenario[]))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [isSignedIn, getToken]);

  async function startConversation(scenario: Scenario) {
    setCreatingId(scenario.id);
    setError(null);
    try {
      const data = await authedFetch(getToken, "/conversations", {
        method: "POST",
        body: JSON.stringify({ scenario_id: scenario.id }),
      });
      localStorage.setItem(SESSION_KEY, data.id);
      router.push("/conversation");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start conversation");
      setCreatingId(null);
    }
  }

  return (
    <AuthGate>
      <main className="flex-1 max-w-2xl mx-auto w-full px-6 py-10">
        <h1 className="text-2xl font-semibold tracking-tight">Choose a scenario</h1>
        <p className="mt-1 text-sm text-neutral-500">
          Pick a professional situation to practice.
        </p>

        {error && (
          <div className="mt-6 rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="mt-8 space-y-3">
          {loading && (
            <div className="flex justify-center py-12">
              <p className="text-sm text-neutral-400 animate-pulse">Loading scenarios…</p>
            </div>
          )}

          {!loading && scenarios.length === 0 && !error && (
            <div className="flex justify-center py-12">
              <p className="text-sm text-neutral-400">
                No scenarios available — is the backend running?
              </p>
            </div>
          )}

          {scenarios.map((s) => (
            <button
              key={s.id}
              onClick={() => startConversation(s)}
              disabled={creatingId !== null}
              className="w-full text-left border border-neutral-200 rounded-xl px-5 py-4 hover:border-neutral-400 transition-colors disabled:opacity-40"
            >
              <div className="flex items-center justify-between">
                <span className="font-medium text-sm">{s.name}</span>
                <span className="text-xs text-neutral-400 capitalize">{s.difficulty}</span>
              </div>
              <p className="text-xs text-neutral-500 mt-1 leading-relaxed">{s.description}</p>
              <p className="text-xs text-neutral-400 mt-2">
                {creatingId === s.id ? "Starting…" : "Start practicing →"}
              </p>
            </button>
          ))}
        </div>
      </main>
    </AuthGate>
  );
}
