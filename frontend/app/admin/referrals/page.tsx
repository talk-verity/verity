"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import AuthGate from "@/components/AuthGate";
import { APIError, authedFetch } from "@/lib/api";

type Referral = {
  code: string;
  label: string;
  unique_users: number;
  created_at: string;
};

export default function ReferralsPage() {
  const { isSignedIn, getToken } = useAuth();
  const [referrals, setReferrals] = useState<Referral[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isSignedIn) return;
    authedFetch(getToken, "/admin/referrals")
      .then((data) => setReferrals((data as { referrals: Referral[] }).referrals))
      .catch((e) => setError(
        e instanceof APIError && e.status === 403
          ? "You are not authorized to view these numbers."
          : e.message,
      ))
      .finally(() => setLoading(false));
  }, [isSignedIn, getToken]);

  return (
    <AuthGate>
      <main className="flex-1 max-w-3xl mx-auto w-full px-6 py-10">
        <h1 className="text-2xl font-semibold tracking-tight">Partner referrals</h1>
        <p className="mt-1 text-sm text-neutral-500">
          Unique Verity accounts created through each partner link.
        </p>

        {error && (
          <div className="mt-6 rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {loading && <p className="mt-8 text-sm text-neutral-400 animate-pulse">Loading…</p>}

        {!loading && !error && (
          <div className="mt-8 overflow-hidden rounded-xl border border-neutral-200">
            <table className="w-full text-sm">
              <thead className="bg-neutral-50 text-left text-neutral-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Partner</th>
                  <th className="px-4 py-3 font-medium">Link code</th>
                  <th className="px-4 py-3 text-right font-medium">Unique users</th>
                </tr>
              </thead>
              <tbody>
                {referrals.map((referral) => (
                  <tr key={referral.code} className="border-t border-neutral-200">
                    <td className="px-4 py-3">{referral.label}</td>
                    <td className="px-4 py-3 font-mono text-xs">{referral.code}</td>
                    <td className="px-4 py-3 text-right tabular-nums">{referral.unique_users}</td>
                  </tr>
                ))}
                {referrals.length === 0 && (
                  <tr>
                    <td colSpan={3} className="px-4 py-6 text-center text-neutral-400">
                      No referral links configured.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </AuthGate>
  );
}
