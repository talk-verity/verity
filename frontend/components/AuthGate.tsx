"use client";

import Image from "next/image";
import Link from "next/link";
import { useAuth } from "@clerk/nextjs";
import AppShell, { type ShellSurface } from "@/components/AppShell";

type Props = {
  children: React.ReactNode;
  surface?: ShellSurface;
  title?: string;
};

export default function AuthGate({ children, surface = "sidebar", title }: Props) {
  const { isLoaded, isSignedIn } = useAuth();

  if (!isLoaded) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-canvas">
        <p className="text-[13px] text-muted">Loading your practice space…</p>
      </div>
    );
  }

  if (!isSignedIn) {
    return <SignedOutPanel />;
  }

  return (
    <AppShell surface={surface} title={title}>
      {children}
    </AppShell>
  );
}

function SignedOutPanel() {
  return (
    <div className="flex min-h-dvh flex-col bg-white md:flex-row md:items-stretch">
      <section className="flex shrink-0 flex-col gap-12 bg-forest px-8 py-12 text-white md:w-[680px] md:px-16 md:py-[52px]">
        <div className="relative h-[62px] w-[192px]">
          <Image src="/brand/delphi-logo-white.svg" alt="Delphi" fill priority className="object-contain object-left" />
        </div>
        <div className="flex flex-col gap-6">
          <p className="text-[12px] font-medium tracking-[1px] text-pale-lime">
            SPEAK BETTER, LIVE BETTER
          </p>
          <h1 className="font-display text-[36px] font-semibold leading-[1.4] md:text-[48px]">
            You have the ideas, we’ll give you the words.
          </h1>
          <p className="text-[16px] leading-6 text-pale-forest">
            Build confidence for the conversations ahead.
            <br />
            Practice in here, perform out there.
          </p>
        </div>
        <div className="mt-auto rounded-[16px] bg-lime p-7">
          <p className="text-[24px] font-medium leading-8 text-ink">
            “I’ve got an idea I’d love to build on.”
          </p>
          <p className="mt-4 text-[15px] text-muted">~ You, at the team meeting tomorrow</p>
        </div>
      </section>

      <section className="flex flex-1 flex-col items-center justify-center px-8 py-16 text-center md:px-[140px]">
        <p className="text-[11px] font-bold text-muted">WE’RE HAPPY TO SEE YOU</p>
        <h2 className="mt-3 font-display text-[36px] font-semibold leading-tight text-ink">
          Welcome back.
        </h2>
        <p className="mt-2 text-[17px] text-muted">Pick up where you left off.</p>
        <Link
          href="/sign-in"
          className="mt-9 flex h-[54px] w-full max-w-[480px] items-center justify-center rounded-[8px] bg-forest px-[22px] text-[16px] font-bold text-white"
        >
          Log in
        </Link>
        <Link href="/sign-up" className="mt-6 text-[14px] font-medium text-forest">
          New to Delphi? Create an account
        </Link>
        <p className="mt-8 text-[12px] leading-5 text-muted">
          A space to practice, not perform.
          <br />
          Your sessions are private by default.
        </p>
      </section>
    </div>
  );
}
