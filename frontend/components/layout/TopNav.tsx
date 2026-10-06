"use client";

import Link from "next/link";

import { LanguageSwitcher } from "@/components/civic/LanguageSwitcher";

export function TopNav() {
  return (
    <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur">
      <div className="container flex h-14 items-center justify-between">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <span className="inline-flex h-7 w-7 items-center justify-center rounded-md bg-[var(--civic-ink)] text-xs text-white">
            SG
          </span>
          <span>SSIP GovTech</span>
        </Link>

        <nav className="flex items-center gap-2">
          <Link href="/upload" className="text-sm font-medium hover:underline">
            Upload
          </Link>
          <Link href="/login" className="text-sm font-medium hover:underline">
            Sign in
          </Link>
          <LanguageSwitcher />
        </nav>
      </div>
    </header>
  );
}
