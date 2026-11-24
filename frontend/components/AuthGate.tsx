"use client";

import { useAuth } from "@clerk/nextjs";
import Image from "next/image";
import Link from "next/link";

export default function AuthGate({ children }: { children: React.ReactNode }) {
  const { isLoaded, isSignedIn } = useAuth();

  if (!isLoaded) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-neutral-400">Loading...</p>
      </div>
    );
  }

  if (!isSignedIn) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center px-4 text-center">
        <Image
          src="/brand/delphi-logo.svg"
          alt="Delphi"
          width={188}
          height={61}
          priority
        />
        <p className="mt-3 text-neutral-500">
          Sign in to practice professional conversations and get AI coaching.
        </p>
        <div className="mt-6 flex gap-3">
          <Link
            href="/sign-in"
            className="bg-neutral-900 text-white rounded-2xl px-5 py-2.5 text-sm font-medium"
          >
            Sign in
          </Link>
          <Link
            href="/sign-up"
            className="border border-neutral-300 rounded-2xl px-5 py-2.5 text-sm font-medium hover:bg-neutral-50"
          >
            Sign up
          </Link>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
