"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { SignOutButton, UserButton, useUser } from "@clerk/nextjs";
import {
  ArrowIcon,
  ChartIcon,
  ChatIcon,
  ExternalIcon,
  HelpIcon,
  HomeIcon,
  LogoutIcon,
} from "@/components/Icons";

export type ShellSurface = "sidebar" | "header";

type Props = {
  children: React.ReactNode;
  surface?: ShellSurface;
  title?: string;
};

const PRIMARY_LINKS = [
  { href: "/", label: "Home", icon: HomeIcon },
  { href: "/scenarios", label: "Practice scenarios", icon: ChatIcon },
  { href: "/reports", label: "My progress", icon: ChartIcon },
  { href: "/conversation", label: "The conversation guide", icon: ExternalIcon },
];

const HEADER_LINKS = [
  { href: "/scenarios", label: "Practice" },
  { href: "/reports", label: "My progress" },
  { href: "/settings", label: "Help & guide" },
  { href: "/settings", label: "My account" },
];

export default function AppShell({
  children,
  surface = "sidebar",
  title,
}: Props) {
  const pathname = usePathname();

  if (surface === "header") {
    return (
      <div className="min-h-dvh bg-canvas">
        <header className="flex h-[90px] w-full items-center gap-10 border-b border-line bg-white px-6 md:px-14">
          <Link href="/" aria-label="Delphi home" className="relative h-[90px] w-[180px] shrink-0">
            <Image
              src="/brand/delphi-logo.svg"
              alt="Delphi"
              fill
              priority
              className="object-contain object-left"
            />
          </Link>
          <nav className="ml-auto flex items-center gap-6 overflow-clip whitespace-nowrap md:gap-9">
            {HEADER_LINKS.map((link) => {
              const active =
                link.href === "/settings"
                  ? pathname === "/settings"
                  : pathname.startsWith(link.href);
              return (
                <Link
                  key={`${link.href}-${link.label}`}
                  href={link.href}
                  className={`text-[14px] md:text-[15px] ${
                    active
                      ? "font-bold text-forest"
                      : "font-normal text-muted hover:text-ink"
                  } ${link.label === "My account" ? "hidden font-medium text-ink sm:block" : ""} ${
                    link.label === "Help & guide" ? "hidden sm:block" : ""
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>
        </header>
        <main className="min-w-0">{children}</main>
      </div>
    );
  }

  return (
    <div className="flex min-h-dvh bg-canvas">
      <Sidebar pathname={pathname} />
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex h-[80px] shrink-0 items-center justify-between border-b border-line bg-white pl-5 pr-5 md:h-[100px] md:pl-[38px]">
          <div className="flex items-center gap-3 lg:hidden">
            <Link href="/" aria-label="Delphi home" className="relative h-10 w-[110px]">
              <Image src="/brand/delphi-logo.svg" alt="Delphi" fill priority className="object-contain object-left" />
            </Link>
          </div>
          {title ? (
            <p className="hidden text-[16px] text-muted lg:block">{title}</p>
          ) : (
            <span className="hidden lg:block" />
          )}
          <div className="flex items-center justify-end gap-9">
            <span className="hidden text-[14px] text-muted sm:block">Your practice space</span>
            <div className="flex size-[35px] items-center justify-center overflow-hidden rounded-[18px] bg-line">
              <UserButton
                appearance={{ elements: { avatarBox: "size-[35px]" } }}
              />
            </div>
          </div>
        </div>
        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  );
}

function Sidebar({ pathname }: { pathname: string }) {
  const { user } = useUser();
  const initials =
    user?.firstName && user?.lastName
      ? `${user.firstName.charAt(0)}${user.lastName.charAt(0)}`
      : user?.firstName?.charAt(0) ||
        user?.username?.charAt(0)?.toUpperCase() ||
        "A";
  const name = user?.fullName || user?.username || "Practice account";

  return (
    <aside className="sticky top-0 hidden h-dvh w-[272px] shrink-0 flex-col border-r border-line bg-white lg:flex">
      <div className="flex h-[210px] shrink-0 flex-col gap-[10px] pl-[29px] pt-[28px]">
        <Link href="/" aria-label="Delphi home" className="relative h-[90px] w-[180px]">
          <Image src="/brand/delphi-logo.svg" alt="Delphi" fill priority className="object-contain object-left" />
        </Link>
        <p className="text-[14px] leading-5 text-muted">Conversation practice</p>
      </div>

      <nav className="flex shrink-0 flex-col gap-[12px] pl-4">
        {PRIMARY_LINKS.map((link) => {
          const active =
            link.href === "/"
              ? pathname === "/"
              : pathname.startsWith(link.href);
          const Icon = link.icon;
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`flex h-[61px] w-[240px] items-center gap-4 rounded-[8px] px-4 ${
                active ? "bg-lime" : "hover:bg-mint"
              }`}
            >
              <Icon size={24} className={active ? "text-ink" : "text-muted"} />
              <span
                className={`flex-1 text-[16px] leading-6 ${
                  active
                    ? "font-medium text-ink"
                    : pathname.startsWith("/conversation") && link.href === "/conversation"
                      ? "font-medium text-forest"
                      : "text-muted"
                }`}
              >
                {link.label}
              </span>
              {active && <span className="size-[6px] rounded-full bg-forest" />}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto flex flex-col gap-[19px] px-[22px] pb-6 pt-[46px]">
        <div className="h-px w-full bg-line" />
        <div className="flex flex-col gap-[10px]">
          <p className="text-[17px] font-medium leading-6 text-ink">New to Delphi?</p>
          <p className="text-[14px] leading-5 text-muted">
            See what to expect before
            <br />
            your first conversation.
          </p>
        </div>
        <Link href="/scenarios" className="flex h-[30px] w-[200px] items-center gap-[18px]">
          <span className="text-[14px] font-bold text-ink">How it works</span>
          <ArrowIcon size={20} className="text-ink" />
        </Link>
        <Link href="/settings" className="flex h-11 items-center gap-[14px]">
          <HelpIcon size={22} className="text-muted" />
          <span className="text-[14px] text-muted">Help & guidance</span>
        </Link>
      </div>

      <div className="flex h-[92px] shrink-0 items-center gap-4 border border-line pl-5 pr-[18px]">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-[20px] bg-line text-[14px] text-ink">
          {initials}
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-[14px] font-bold text-ink">{name}</p>
          <p className="text-[10px] text-muted">Practice account</p>
        </div>
        <SignOutButton>
          <button type="button" aria-label="Sign out" className="text-muted hover:text-forest">
            <LogoutIcon size={20} />
          </button>
        </SignOutButton>
      </div>
    </aside>
  );
}
