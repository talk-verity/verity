"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";

export default function Home() {
  const [status, setStatus] = useState<string>("Checking...");
  const [user, setUser] = useState<Record<string, unknown> | null>(null);
  const { getToken, isSignedIn } = useAuth();

  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const root = base.replace(/\/api\/v1\/?$/, "");

    fetch(`${root}/health`)
      .then((res) => res.json())
      .then((data) => setStatus(data.status))
      .catch(() => setStatus("Unhealthy"));
  }, []);

  useEffect(() => {
    if (!isSignedIn) return;

    const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    getToken().then((token) => {
      if (!token) return;
      fetch(`${base}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((res) => res.json())
        .then((data) => setUser(data))
        .catch(() => {});
    });
  }, [isSignedIn, getToken]);

  return (
    <div className="flex flex-col flex-1 items-center justify-center bg-zinc-50 font-sans dark:bg-black">
      <main className="flex flex-1 w-full max-w-3xl flex-col items-center justify-center py-32 px-16 bg-white dark:bg-black">
        <h1 className="text-4xl font-semibold tracking-tight text-black dark:text-zinc-50">
          Verity
        </h1>
        <p className="mt-4 text-lg text-zinc-600 dark:text-zinc-400">
          Backend Status: {status === "healthy" ? "Healthy" : status}
        </p>
        {user && (
          <p className="mt-2 text-sm text-zinc-500">
            Signed in as: {user.email as string}
          </p>
        )}
      </main>
    </div>
  );
}
