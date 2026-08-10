"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import AuthGate from "@/components/AuthGate";
import StatusBadge from "@/components/StatusBadge";
import { authedFetch, type ReportData } from "@/lib/api";

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function ReportsPage() {
  const { isSignedIn, getToken } = useAuth();
  const [reports, setReports] = useState<ReportData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isSignedIn) return;
    authedFetch(getToken, "/reports")
      .then((data) => setReports(data as ReportData[]))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [isSignedIn, getToken]);

  return (
    <AuthGate>
      <main className="flex-1 max-w-3xl mx-auto w-full px-6 py-10">
        <h1 className="text-2xl font-semibold tracking-tight">Reports</h1>
        <p className="mt-1 text-sm text-neutral-500">
          Feedback from your completed conversations.
        </p>

        {error && (
          <div className="mt-6 rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="mt-8 space-y-2">
          {loading && (
            <div className="flex justify-center py-12">
              <p className="text-sm text-neutral-400 animate-pulse">Loading reports…</p>
            </div>
          )}

          {!loading && reports.length === 0 && !error && (
            <div className="text-center py-16">
              <p className="text-sm text-neutral-400">No reports yet.</p>
              <Link
                href="/scenarios"
                className="inline-block mt-4 bg-neutral-900 text-white rounded-2xl px-5 py-2.5 text-sm font-medium"
              >
                Start practicing
              </Link>
            </div>
          )}

          {reports.map((r) => (
            <Link
              key={r.id}
              href={`/reports/${r.id}`}
              className="flex items-center justify-between border border-neutral-200 rounded-xl px-5 py-4 hover:border-neutral-400 transition-colors"
            >
              <div>
                <div className="text-sm font-medium">{r.title}</div>
                <div className="text-xs text-neutral-400 mt-0.5">{formatDate(r.created_at)}</div>
              </div>
              <StatusBadge status={r.status} />
            </Link>
          ))}
        </div>
      </main>
    </AuthGate>
  );
}
