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
    <AuthGate title="My progress">
      <main className="w-full px-6 pb-16 pt-9 lg:px-[38px]">
        <section className="flex flex-col gap-3 pb-9">
          <p className="text-[11px] font-bold tracking-[1px] text-forest">YOUR PRACTICE</p>
          <h1 className="font-display text-[34px] font-semibold leading-tight text-ink">
            My progress
          </h1>
          <p className="text-[16px] text-muted">Feedback from your completed conversations.</p>
        </section>

        {error && (
          <div role="alert" className="mb-6 rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="flex flex-col gap-3">
          {loading && (
            <>
              <div className="h-[84px] rounded-xl border border-line bg-white" />
              <div className="h-[84px] rounded-xl border border-line bg-white" />
              <div className="h-[84px] rounded-xl border border-line bg-white" />
            </>
          )}

          {!loading && reports.length === 0 && !error && (
            <div className="flex flex-col items-center gap-4 rounded-xl border border-line bg-white px-6 py-16 text-center">
              <p className="text-[14px] text-muted">No reports yet. Your feedback will appear here.</p>
              <Link
                href="/scenarios"
                className="rounded-lg bg-forest px-5 py-3 text-[13px] font-bold text-white"
              >
                Start practicing
              </Link>
            </div>
          )}

          {reports.map((r) => (
            <Link
              key={r.id}
              href={`/reports/${encodeURIComponent(String(r.id))}`}
              className="flex items-center justify-between gap-4 rounded-xl border border-line bg-white px-5 py-4 transition-colors hover:border-forest"
            >
              <div className="min-w-0">
                <p className="text-[15px] font-medium text-ink">{r.title}</p>
                <p className="mt-1 text-[12px] text-muted">{formatDate(r.created_at)}</p>
              </div>
              <StatusBadge status={r.status} />
            </Link>
          ))}
        </div>
      </main>
    </AuthGate>
  );
}
