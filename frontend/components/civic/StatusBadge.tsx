"use client";

import { CircleCheck, CircleX, Clock, TriangleAlert, type LucideIcon } from "lucide-react";
import { useLanguage } from "@/lib/LanguageContext";
import type { TranslationKey } from "@/lib/i18n/dictionaries";

export type CivicStatus = "verified" | "review" | "mismatch" | "pending";

const STYLES: Record<CivicStatus, { icon: LucideIcon; className: string; label: TranslationKey }> = {
  verified: { icon: CircleCheck, className: "border-[var(--civic-verified)] bg-green-50 text-green-900", label: "status.verified" },
  review: { icon: TriangleAlert, className: "border-[var(--civic-review)] bg-orange-50 text-orange-950", label: "status.review" },
  mismatch: { icon: CircleX, className: "border-[var(--civic-mismatch)] bg-red-50 text-red-900", label: "status.mismatch" },
  pending: { icon: Clock, className: "border-slate-500 bg-slate-100 text-slate-800", label: "status.pending" },
};

/** Icon + colour + words: status is never carried by colour alone. */
export function StatusBadge({ status }: { status: CivicStatus }) {
  const { t } = useLanguage();
  const { icon: Icon, className, label } = STYLES[status];
  return (
    <span className={`inline-flex min-h-10 items-center gap-2 rounded-full border-2 px-3 text-base font-semibold ${className}`}>
      <Icon aria-hidden className="h-5 w-5 shrink-0" />
      {t(label)}
    </span>
  );
}
