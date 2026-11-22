"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { useParams } from "next/navigation";
import AuthGate from "@/components/AuthGate";
import ReportView from "@/components/ReportView";
import StatusBadge from "@/components/StatusBadge";
import { API, authedFetch, type ReportData } from "@/lib/api";

function formatDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function ReportDetailPage() {
  const params = useParams<{ id: string }>();
  const { isSignedIn, getToken } = useAuth();
  const [report, setReport] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);

  const fetchReport = useCallback((signal?: AbortSignal) => {
    if (!isSignedIn) return Promise.resolve();
    return authedFetch(getToken, `/reports/${params.id}`, { signal })
      .then(async data => {
        if (signal?.aborted) return;
        setReport(data);
        setError(null);
        if (data.status === "generating") {
          await authedFetch(getToken, `/reports/${params.id}/process`, { method: "POST", signal });
          const updated = await authedFetch(getToken, `/reports/${params.id}`, { signal });
          if (!signal?.aborted) setReport(updated);
        }
      })
      .catch(err => { if (!signal?.aborted) setError(err instanceof Error ? err.message : "Could not load feedback"); })
      .finally(() => { if (!signal?.aborted) setLoading(false); });
  }, [isSignedIn, getToken, params.id]);

  useEffect(() => {
    const controller = new AbortController();
    void fetchReport(controller.signal);
    return () => controller.abort();
  }, [fetchReport]);

  useEffect(() => {
    if (report?.status !== "generating") return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      await fetchReport(controller.signal);
      if (!controller.signal.aborted) timer = setTimeout(poll, 3000);
    }
    timer = setTimeout(poll, 3000);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [report?.status, fetchReport]);

  async function handleRetry() {
    setRetrying(true);
    setError(null);
    try {
      await authedFetch(getToken, `/reports/${params.id}/retry`, { method: "POST" });
      setLoading(true);
      await fetchReport();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Retry failed");
    }
    setRetrying(false);
  }

  async function handleDownload() {
    const token = await getToken();
    if (!token) return;
    try {
      const res = await fetch(`${API}/reports/${params.id}/download`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Download failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${report?.title.replace(/[^a-z0-9]+/gi, "-") || "verity-report"}.html`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Download failed");
    }
  }

  return (
    <AuthGate>
      <main className="flex-1 max-w-2xl mx-auto w-full px-6 py-10">
        <Link href="/reports" className="text-sm text-neutral-400 hover:text-neutral-600">
          ← Back to reports
        </Link>

        {error && (
          <div className="mt-6 rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {loading && !report && (
          <div className="flex justify-center py-16">
            <p className="text-sm text-neutral-400 animate-pulse">Loading report…</p>
          </div>
        )}

        {!loading && !report && !error && (
          <div className="text-center py-16">
            <p className="text-sm text-neutral-400">Report not found.</p>
          </div>
        )}

        {report && (
          <div className="mt-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-xl font-semibold">{report.title}</h1>
                <p className="text-xs text-neutral-400 mt-1">{formatDate(report.created_at)}</p>
              </div>
              <StatusBadge status={report.status} />
            </div>

            {report.status === "generating" && (
              <div className="rounded-2xl border border-blue-200 bg-blue-50 px-6 py-10 text-center">
                <div className="mx-auto w-8 h-8 border-2 border-blue-300 border-t-blue-600 rounded-full animate-spin" />
                <p className="mt-4 text-sm text-blue-800 font-medium">Generating your report…</p>
                <p className="mt-1 text-xs text-blue-600">
                  Your feedback is queued. This page updates automatically.
                </p>
              </div>
            )}

            {report.status === "render_failed" && (
              <div className="rounded-2xl border border-red-200 bg-red-50 px-6 py-8 text-center">
                <p className="text-sm text-red-800 font-medium">
                  Rendering failed — your feedback was preserved.
                </p>
                <button
                  onClick={handleRetry}
                  disabled={retrying}
                  className="mt-4 bg-red-700 text-white rounded-2xl px-5 py-2.5 text-sm font-medium hover:bg-red-800 disabled:opacity-40"
                >
                  {retrying ? "Retrying…" : "Retry rendering"}
                </button>
              </div>
            )}

            {report.status === "failed" && (
              <div className="rounded-2xl border border-red-200 bg-red-50 px-6 py-8 text-center">
                <p className="text-sm text-red-800 font-medium">
                  This report failed to generate.
                </p>
                <button onClick={handleRetry} disabled={retrying} className="mt-4 underline">
                  {retrying ? "Retrying…" : "Retry feedback for this conversation"}
                </button>
              </div>
            )}

            {report.status === "ready" && report.content && (
              <>
                <ReportView content={report.content} />
                <button
                  onClick={handleDownload}
                  className="mt-8 w-full bg-neutral-900 text-white rounded-2xl py-3 text-sm font-medium hover:opacity-90"
                >
                  Download HTML report
                </button>
              </>
            )}

            {report.status === "render_failed" && report.content && (
              <div className="mt-6 opacity-60">
                <ReportView content={report.content} />
              </div>
            )}
          </div>
        )}
      </main>
    </AuthGate>
  );
}
