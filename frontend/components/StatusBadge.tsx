"use client";

const STYLES: Record<string, string> = {
  ready: "bg-emerald-100 text-emerald-800",
  generating: "bg-blue-100 text-blue-800 animate-pulse",
  render_failed: "bg-red-100 text-red-800",
  failed: "bg-red-100 text-red-800",
};

const LABELS: Record<string, string> = {
  ready: "Ready",
  generating: "Generating",
  render_failed: "Failed",
  failed: "Failed",
};

export default function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`text-xs px-2.5 py-1 rounded-full font-medium ${
        STYLES[status] || "bg-neutral-100 text-neutral-600"
      }`}
    >
      {LABELS[status] || status}
    </span>
  );
}
