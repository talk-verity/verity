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
    <AuthGate title="My account">
      <main className="w-full px-6 pb-16 pt-9 lg:px-[38px]">
        <section className="flex flex-col gap-3 pb-9">
          <p className="text-[11px] font-bold tracking-[1px] text-forest">MY ACCOUNT</p>
          <h1 className="font-display text-[34px] font-semibold leading-tight text-ink">
            Settings
          </h1>
          <p className="text-[16px] text-muted">Your account and practice environment.</p>
        </section>

        <div className="flex max-w-[820px] flex-col gap-7">
          <SettingsSection title="Account">
            <Row label="Name" value={user?.fullName || user?.username || "—"} />
            <Row label="Email" value={user?.primaryEmailAddress?.emailAddress || "—"} />
          </SettingsSection>

          <SettingsSection title="Backend">
            <Row label="Status" value={health} />
            <Row label="API URL" value={ROOT} />
          </SettingsSection>

          <SettingsSection title="Preferences">
            <div className="flex items-center justify-between px-5 py-4">
              <div>
                <p className="text-[14px] font-medium text-ink">Dark mode</p>
                <p className="mt-1 text-[12px] text-muted">Coming soon</p>
              </div>
              <button
                disabled
                aria-label="Dark mode coming soon"
                className="pointer-events-none relative h-6 w-10 rounded-full bg-line"
              >
                <span className="absolute left-0.5 top-0.5 size-5 rounded-full bg-white shadow" />
              </button>
            </div>
          </SettingsSection>
        </div>
      </main>
    </AuthGate>
  );
}

function SettingsSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="mb-3 text-[11px] font-bold tracking-[1px] text-muted">{title}</h2>
      <div className="divide-y divide-line rounded-xl border border-line bg-white">{children}</div>
    </section>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 px-5 py-4">
      <p className="text-[13px] text-muted">{label}</p>
      <p className="text-right text-[14px] font-medium text-ink">{value}</p>
    </div>
  );
}
