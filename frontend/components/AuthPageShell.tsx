import type { ReactNode } from "react";
import Image from "next/image";

export default function AuthPageShell({
  eyebrow,
  heading,
  subheading,
  children,
}: {
  eyebrow: string;
  heading: string;
  subheading: string;
  children: ReactNode;
}) {
  return (
    <main className="flex min-h-dvh flex-col bg-white md:flex-row">
      <section className="flex shrink-0 flex-col gap-12 bg-forest px-8 py-12 text-white md:w-[680px] md:px-16 md:py-[52px]">
        <div className="relative h-[62px] w-[192px]">
          <Image
            src="/brand/delphi-logo-white.svg"
            alt="Delphi"
            fill
            priority
            className="object-contain object-left"
          />
        </div>
        <div className="flex flex-col gap-6">
          <p className="text-[12px] font-medium tracking-[1px] text-pale-lime">
            SPEAK BETTER, LIVE BETTER
          </p>
          <h2 className="font-display text-[38px] font-semibold leading-[1.4] md:text-[52px]">
            You have the ideas, we&apos;ll give you the words.
          </h2>
          <p className="text-[18px] leading-6 text-[#d4e1d7]">
            Build confidence for the conversations ahead.
            <br />
            Practice in here, perform out there.
          </p>
        </div>
        <div className="mt-auto rounded-2xl bg-lime p-7">
          <p className="text-[16px] font-bold leading-6 text-ink">
            Make space for what you have to say.
          </p>
          <p className="mt-4 text-[24px] font-medium leading-8 text-ink">
            &ldquo;I&apos;ve got an idea I&apos;d love to build on.&rdquo;
          </p>
          <p className="mt-4 text-[15px] text-muted">
            ~ You, at the team meeting tomorrow
          </p>
        </div>
        <p className="text-[13px] text-[#d4e1d7]">Small steps. Stronger conversations.</p>
      </section>

      <section className="flex flex-1 flex-col justify-center px-6 py-12 md:px-[140px] md:py-[84px]">
        <div className="mx-auto flex w-full max-w-[480px] flex-col gap-7">
          <div className="flex flex-col gap-[10px]">
            <p className="text-[11px] font-bold tracking-[1px] text-muted">{eyebrow}</p>
            <h1 className="font-display text-[36px] font-semibold leading-[1.4] text-ink">
              {heading}
            </h1>
            <p className="text-[17px] text-muted">{subheading}</p>
          </div>
          {children}
          <p className="text-center text-[12px] leading-5 text-muted">
            A space to practice, not perform.
            <br />
            Your sessions are private by default.
          </p>
        </div>
      </section>
    </main>
  );
}
