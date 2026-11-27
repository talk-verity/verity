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
    <AuthGate title="Partner referrals">
      <main className="w-full px-6 pb-16 pt-9 lg:px-[38px]">
        <section className="flex flex-col gap-3 pb-9">
          <p className="text-[11px] font-bold tracking-[1px] text-forest">PARTNER REFERRALS</p>
          <h1 className="font-display text-[34px] font-semibold leading-tight text-ink">
            Partner referrals
          </h1>
          <p className="text-[16px] text-muted">
            Unique Delphi accounts created through each partner link.
          </p>
        </section>

        {error && (
          <div role="alert" className="mb-6 rounded-xl border border-line bg-red-50 px-5 py-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {loading && (
          <div className="flex flex-col gap-3">
            <div className="h-12 rounded-xl bg-mint" />
            <div className="h-16 rounded-xl border border-line bg-white" />
            <div className="h-16 rounded-xl border border-line bg-white" />
          </div>
        )}

        {!loading && !error && (
          <div className="overflow-hidden rounded-xl border border-line bg-white">
            <table className="w-full text-[13px]">
              <thead className="bg-mint text-left text-muted">
                <tr>
                  <th className="px-5 py-4 font-medium">Partner</th>
                  <th className="px-5 py-4 font-medium">Link code</th>
                  <th className="px-5 py-4 text-right font-medium">Unique users</th>
                </tr>
              </thead>
              <tbody>
                {referrals.map((referral) => (
                  <tr key={referral.code} className="border-t border-line">
                    <td className="px-5 py-4 text-ink">{referral.label}</td>
                    <td className="px-5 py-4 text-[12px] text-muted">{referral.code}</td>
                    <td className="px-5 py-4 text-right tabular-nums text-ink">{referral.unique_users}</td>
                  </tr>
                ))}
                {referrals.length === 0 && (
                  <tr>
                    <td colSpan={3} className="px-5 py-10 text-center text-muted">
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
