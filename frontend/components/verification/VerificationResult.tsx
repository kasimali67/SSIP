"use client";

import { CircleCheck, CircleX, TriangleAlert } from "lucide-react";
import { BilingualText } from "@/components/civic/BilingualText";
import { StatusBadge, type CivicStatus } from "@/components/civic/StatusBadge";
import { useLanguage } from "@/lib/LanguageContext";
import type { TranslationKey } from "@/lib/i18n/dictionaries";
import type { ComparedField, CrossVerificationResult, FieldStatus, OverallStatus } from "@/lib/api/verification";

const FIELD_LABELS: Record<ComparedField, TranslationKey> = {
  name: "fields.name",
  dob: "fields.dob",
  id_last4: "fields.idLast4",
};

const REASON_KEYS: Record<string, TranslationKey> = {
  exact: "reasons.exact",
  minor_spelling_difference: "reasons.minor_spelling_difference",
  name_differs: "reasons.name_differs",
  different_script: "reasons.different_script",
  year_only: "reasons.year_only",
  date_differs: "reasons.date_differs",
  unreadable_date: "reasons.unreadable_date",
  id_differs: "reasons.id_differs",
  not_found: "reasons.not_found",
};

const FIELD_TO_CIVIC: Record<FieldStatus, CivicStatus> = {
  match: "verified",
  review: "review",
  missing: "review",
  mismatch: "mismatch",
};

const OVERALL = {
  verified: { icon: CircleCheck, tone: "border-[var(--civic-verified)] bg-green-50 text-green-950", key: "overall.verified" },
  needs_review: { icon: TriangleAlert, tone: "border-[var(--civic-review)] bg-orange-50 text-orange-950", key: "overall.needs_review" },
  mismatch: { icon: CircleX, tone: "border-[var(--civic-mismatch)] bg-red-50 text-red-950", key: "overall.mismatch" },
} satisfies Record<OverallStatus, { icon: typeof CircleCheck; tone: string; key: TranslationKey }>;

export function VerificationResult({ result }: { result: CrossVerificationResult }) {
  const { t } = useLanguage();
  const summary = OVERALL[result.overall];
  const SummaryIcon = summary.icon;

  return (
    <section aria-live="polite" className="flex flex-col gap-4">
      <div className={`flex items-start gap-3 rounded-2xl border-2 p-5 ${summary.tone}`}>
        <SummaryIcon aria-hidden className="mt-0.5 h-8 w-8 shrink-0" />
        <p className="text-xl font-bold leading-snug">{t(summary.key)}</p>
      </div>

      <ul className="flex flex-col gap-3">
        {result.fields.map((item) => (
          <li key={item.field} className="rounded-2xl border-2 border-slate-300 bg-[var(--civic-paper)] p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <BilingualText k={FIELD_LABELS[item.field]} />
              <StatusBadge status={FIELD_TO_CIVIC[item.status]} />
            </div>
            <dl className="mt-3 grid gap-3 sm:grid-cols-2">
              <div>
                <dt className="text-sm text-[var(--civic-text-muted)]">{t("verify.yourDocument")}</dt>
                <dd className="break-words text-lg font-semibold">{item.document_value ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-sm text-[var(--civic-text-muted)]">
                  {t("verify.official")}
                  {result.is_sandbox && ` (${t("demo.short")})`}
                </dt>
                <dd className="break-words text-lg font-semibold">{item.official_value ?? "—"}</dd>
              </div>
            </dl>
            <p className="mt-2 text-base">{t(REASON_KEYS[item.reason] ?? "reasons.not_found")}</p>
          </li>
        ))}
      </ul>
      <p className="text-sm text-[var(--civic-text-muted)]">{result.issuer}</p>
    </section>
  );
}
