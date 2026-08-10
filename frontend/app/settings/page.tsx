"use client";

import { useEffect, useState } from "react";
import { useUser } from "@clerk/nextjs";
import AuthGate from "@/components/AuthGate";
import { ROOT } from "@/lib/api";

export default function SettingsPage() {
  const { user } = useUser();
  const [health, setHealth] = useState("Checking...");

  useEffect(() => {
    fetch(`${ROOT}/health`)
      .then((r) => r.json())
      .then((d) => setHealth(d.status))
      .catch(() => setHealth("Unhealthy"));
  }, []);

  return (
    <AuthGate>
      <main className="flex-1 max-w-2xl mx-auto w-full px-6 py-10">
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>

        <section className="mt-8">
          <h2 className="text-sm font-medium text-neutral-500 uppercase tracking-wide mb-3">
            Account
          </h2>
          <div className="rounded-2xl border border-neutral-200 divide-y divide-neutral-100">
            <Row label="Name" value={user?.fullName || user?.username || "—"} />
            <Row label="Email" value={user?.primaryEmailAddress?.emailAddress || "—"} />
          </div>
        </section>

        <section className="mt-8">
          <h2 className="text-sm font-medium text-neutral-500 uppercase tracking-wide mb-3">
            Backend
          </h2>
          <div className="rounded-2xl border border-neutral-200 divide-y divide-neutral-100">
            <Row label="Status" value={health} />
            <Row label="API URL" value={ROOT} />
          </div>
        </section>

        <section className="mt-8">
          <h2 className="text-sm font-medium text-neutral-500 uppercase tracking-wide mb-3">
            Preferences
          </h2>
          <div className="rounded-2xl border border-neutral-200 divide-y divide-neutral-100">
            <div className="flex items-center justify-between px-5 py-3">
              <div>
                <div className="text-sm">Dark mode</div>
                <div className="text-xs text-neutral-400">Coming soon</div>
              </div>
              <button
                disabled
                className="w-10 h-6 rounded-full bg-neutral-200 relative pointer-events-none"
              >
                <span className="absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow" />
              </button>
            </div>
          </div>
        </section>
      </main>
    </AuthGate>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between px-5 py-3">
      <div className="text-sm text-neutral-500">{label}</div>
      <div className="text-sm font-medium">{value}</div>
    </div>
  );
}
