"use client";

import { Check } from "lucide-react";
import { useLanguage } from "@/lib/LanguageContext";
import type { TranslationKey } from "@/lib/i18n/dictionaries";

const STEPS: TranslationKey[] = ["steps.ask", "steps.upload", "steps.check", "steps.verify", "steps.submit"];

/**
 * The one strong visual element of the app: a numbered journey, because the
 * application process genuinely is a fixed sequence the citizen moves through.
 */
export function StepProgress({ current }: { current: number }) {
  const { t } = useLanguage();
  return (
    <nav aria-label={t("steps.label")} className="relative w-full">
      <span aria-hidden className="absolute left-[10%] right-[10%] top-6 h-1 rounded bg-slate-300" />
      <span
        aria-hidden
        className="absolute left-[10%] top-6 h-1 rounded bg-[var(--civic-ink)] transition-[width] duration-500"
        style={{ width: `${(Math.min(current, STEPS.length - 1) / (STEPS.length - 1)) * 80}%` }}
      />
      <ol className="relative grid grid-cols-5">
        {STEPS.map((key, index) => {
          const done = index < current;
          const active = index === current;
          const circle = done
            ? "border-[var(--civic-verified)] bg-[var(--civic-verified)] text-white"
            : active
              ? "border-[var(--civic-ink)] bg-[var(--civic-ink)] text-white"
              : "border-slate-400 bg-white text-slate-600";
          return (
            <li key={key} aria-current={active ? "step" : undefined} className="relative flex flex-col items-center gap-2 text-center">
              <span className={`flex h-12 w-12 items-center justify-center rounded-full border-2 text-lg font-bold ${circle}`}>
                {done ? <Check aria-hidden className="h-6 w-6" /> : index + 1}
              </span>
              <span className={`px-1 text-sm leading-tight ${active ? "font-bold text-[var(--civic-ink)]" : "text-[var(--civic-text-muted)]"}`}>
                {t(key)}
              </span>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
