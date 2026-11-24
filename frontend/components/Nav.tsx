"use client";

import { UserButton } from "@clerk/nextjs";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Dashboard" },
  { href: "/scenarios", label: "Scenarios" },
  { href: "/conversation", label: "Conversation" },
  { href: "/reports", label: "Reports" },
  { href: "/settings", label: "Settings" },
];

export default function Nav() {
  const pathname = usePathname();

  return (
    <nav className="flex items-center justify-between px-6 py-3 border-b border-neutral-200 sticky top-0 bg-white/90 backdrop-blur z-10">
      <div className="flex items-center gap-6">
        <Link href="/" aria-label="Delphi home">
          <Image
            src="/brand/delphi-logo.svg"
            alt="Delphi"
            width={104}
            height={34}
            priority
          />
        </Link>
        <div className="hidden md:flex items-center gap-1">
          {LINKS.map((link) => {
            const active =
              link.href === "/"
                ? pathname === "/"
                : pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                  active
                    ? "bg-neutral-900 text-white"
                    : "text-neutral-600 hover:bg-neutral-100"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </div>
      </div>
      <UserButton />
    </nav>
  );
}
