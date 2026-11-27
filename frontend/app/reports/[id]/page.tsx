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
  const params = useParams<{ id: string | string[] }>();
  const reportId = Array.isArray(params.id) ? params.id[0] : params.id;
  const encodedReportId = encodeURIComponent(reportId ?? "");
  const { isSignedIn, getToken } = useAuth();
  const [report, setReport] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);

  const fetchReport = useCallback((signal?: AbortSignal) => {
    if (!isSignedIn) return Promise.resolve();
    return authedFetch(getToken, `/reports/${encodedReportId}`, { signal })
      .then(async data => {
        if (signal?.aborted) return;
        setReport(data);
        setError(null);
        if (data.status === "generating") {
          await authedFetch(getToken, `/reports/${encodedReportId}/process`, { method: "POST", signal });
          const updated = await authedFetch(getToken, `/reports/${encodedReportId}`, { signal });
          if (!signal?.aborted) setReport(updated);
        }
      })
      .catch(err => { if (!signal?.aborted) setError(err instanceof Error ? err.message : "Could not load feedback"); })
      .finally(() => { if (!signal?.aborted) setLoading(false); });
  }, [isSignedIn, getToken, encodedReportId]);

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
      await authedFetch(getToken, `/reports/${encodedReportId}/retry`, { method: "POST" });
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
      const res = await fetch(`${API}/reports/${encodedReportId}/download`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Download failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${report?.title.replace(/[^a-z0-9]+/gi, "-") || "delphi-report"}.html`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Download failed");
    }
  }

  return (
    <AuthGate>
      <main className="flex-1 w-full bg-canvas text-ink">
        <div className="mx-auto max-w-[1440px] px-6 py-10 lg:px-14">
          <Link href="/reports" className="text-sm text-muted hover:text-forest">
            ← Back to reports
          </Link>

          {error && (
            <div className="mt-6 rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          {loading && !report && (
            <div className="mt-6 flex flex-col gap-6" aria-label="Loading report">
              <div className="h-5 w-52 rounded bg-mint" />
              <div className="h-11 w-2/3 rounded bg-mint" />
              <div className="h-[204px] rounded-[20px] bg-forest/85" />
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
                {[0, 1, 2, 3, 4].map((i) => (
                  <div key={i} className="h-[260px] rounded-[14px] border border-line bg-white p-5">
                    <div className="h-5 w-2/3 rounded bg-mint" />
                    <div className="mt-4 h-9 w-1/2 rounded bg-mint-deep" />
                  </div>
                ))}
              </div>
              <p className="text-[13px] text-muted">Loading your feedback…</p>
            </div>
          )}

          {!loading && !report && !error && (
            <div className="mt-6 rounded-xl border border-line bg-white px-6 py-16 text-center">
              <p className="text-[14px] text-muted">Report not found.</p>
            </div>
          )}

          {report && (
            <div className="mt-6">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h1 className="text-xl font-semibold text-ink">{report.title}</h1>
                  <p className="mt-1 text-xs text-muted">{formatDate(report.created_at)}</p>
                </div>
                <StatusBadge status={report.status} />
              </div>

              {report.status === "generating" && (
                <div className="flex flex-col items-center rounded-[20px] border border-line bg-mint px-6 py-12 text-center">
                  <div className="size-8 animate-spin rounded-full border-2 border-bar border-t-forest" />
                  <p className="mt-4 text-[18px] font-medium text-ink">Generating your report…</p>
                  <p className="mt-1 text-[13px] text-muted">
                    Your feedback is queued. This page updates automatically.
                  </p>
                </div>
              )}

              {report.status === "render_failed" && (
                <div className="rounded-[20px] border border-line bg-white px-6 py-10 text-center">
                  <p className="text-[18px] font-medium text-ink">
                    Rendering failed — your feedback was preserved.
                  </p>
                  <button
                    onClick={handleRetry}
                    disabled={retrying}
                    className="mt-5 rounded-lg bg-forest px-5 py-3 text-[13px] font-bold text-white disabled:opacity-40"
                  >
                    {retrying ? "Retrying…" : "Retry rendering"}
                  </button>
                </div>
              )}

              {report.status === "failed" && (
                <div className="rounded-[20px] border border-line bg-white px-6 py-10 text-center">
                  <p className="text-[18px] font-medium text-ink">
                    This report failed to generate.
                  </p>
                  <button onClick={handleRetry} disabled={retrying} className="mt-5 text-[13px] font-bold text-forest underline">
                    {retrying ? "Retrying…" : "Retry feedback for this conversation"}
                  </button>
                </div>
              )}

              {report.status === "ready" && report.content && (
                <>
                  <ReportView content={report.content} />
                  <button
                    onClick={handleDownload}
                    className="mt-8 w-full rounded-xl border border-line bg-white py-3 text-[13px] font-bold text-forest hover:border-forest"
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
        </div>
      </main>
    </AuthGate>
  );
}
