"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import AuthGate from "@/components/AuthGate";
import StatusBadge from "@/components/StatusBadge";
import { authedFetch, SESSION_KEY, type ReportData, type Scenario } from "@/lib/api";

export default function DashboardPage() {
  const { isSignedIn, getToken, userId } = useAuth();
  const [reports, setReports] = useState<ReportData[]>([]);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [activeSession, setActiveSession] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [latestFeedback, setLatestFeedback] = useState<ReportData | null>(null);

  useEffect(() => {
    if (!isSignedIn) return;
    const controller = new AbortController();
    const signal = controller.signal;
    Promise.all([
      authedFetch(getToken, "/reports", { signal }),
      authedFetch(getToken, "/conversations/scenarios", { signal }),
    ]).then(async ([r, s]) => {
      if (signal.aborted) return;
      setActiveSession(localStorage.getItem(`${SESSION_KEY}:${userId}`));
      setReports(r as ReportData[]);
      setScenarios(s as Scenario[]);
      const latest = (r as ReportData[]).find(report => report.status === "ready");
      if (latest) {
        const detail = await authedFetch(getToken, `/reports/${latest.id}`, { signal });
        if (!signal.aborted) setLatestFeedback(detail);
      }
    }).catch(err => { if (!signal.aborted) setError(err.message); })
      .finally(() => { if (!signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [isSignedIn, getToken, userId]);

  const readyCount = reports.filter((r) => r.status === "ready").length;

  return (
    <AuthGate>
      <main className="flex-1 max-w-4xl mx-auto w-full px-6 py-10">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Dashboard</h1>
            <p className="mt-1 text-sm text-neutral-500">
              Choose one communication skill to practice, then review the transcript.
            </p>
          </div>
          <Link
            href="/scenarios"
            className="bg-neutral-900 text-white rounded-2xl px-5 py-2.5 text-sm font-medium hover:opacity-90"
          >
            Start a conversation
          </Link>
        </div>

        {error && <p role="alert" className="mt-6 text-sm text-red-700">{error}</p>}
        {latestFeedback?.content?.recommendations?.[0] && (
          <section className="mt-6 rounded-2xl border border-indigo-200 px-5 py-4">
            <h2 className="text-sm font-medium">Your next practice</h2>
            <p className="mt-2 text-sm text-neutral-600">{latestFeedback.content.recommendations[0]}</p>
            <Link href={`/reports/${latestFeedback.id}`} className="mt-2 inline-block text-sm underline">Review your latest feedback</Link>
          </section>
        )}
        {activeSession && (
          <Link
            href="/conversation"
            className="mt-6 block border border-emerald-200 bg-emerald-50 rounded-2xl px-5 py-4 hover:border-emerald-400 transition-colors"
          >
            <div className="font-medium text-sm text-emerald-800">
              You have an active conversation
            </div>
            <p className="text-xs text-emerald-600 mt-1">Resume it to keep practicing.</p>
          </Link>
        )}

        <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
          <StatCard label="Reports" value={loading ? "…" : reports.length} />
          <StatCard label="Feedback available" value={loading ? "…" : readyCount} />
          <StatCard label="Scenarios" value={loading ? "…" : scenarios.length} />
        </div>

        <section className="mt-10">
          <h2 className="text-sm font-medium text-neutral-500 uppercase tracking-wide mb-3">
            Practice scenarios
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {scenarios.slice(0, 4).map((s) => (
              <Link
                key={s.id}
                href="/scenarios"
                className="border border-neutral-200 rounded-xl px-4 py-3 hover:border-neutral-400 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-sm">{s.name}</span>
                  <span className="text-xs text-neutral-400 capitalize">{s.difficulty}</span>
                </div>
                <p className="text-xs text-neutral-500 mt-1 line-clamp-2">{s.description}</p>
              </Link>
            ))}
          </div>
        </section>

        {reports.length > 0 && (
          <section className="mt-10">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-medium text-neutral-500 uppercase tracking-wide">
                Recent reports
              </h2>
              <Link href="/reports" className="text-sm text-neutral-500 hover:text-neutral-700">
                View all
              </Link>
            </div>
            <div className="space-y-2">
              {reports.slice(0, 5).map((r) => (
                <Link
                  key={r.id}
                  href={`/reports/${r.id}`}
                  className="flex items-center justify-between border border-neutral-200 rounded-xl px-4 py-3 hover:border-neutral-400 transition-colors"
                >
                  <span className="text-sm font-medium">{r.title}</span>
                  <StatusBadge status={r.status} />
                </Link>
              ))}
            </div>
          </section>
        )}
      </main>
    </AuthGate>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-neutral-200 px-5 py-4">
      <div className="text-xs text-neutral-400 uppercase tracking-wide">{label}</div>
      <div className="text-3xl font-semibold mt-1">{value}</div>
    </div>
  );
}
