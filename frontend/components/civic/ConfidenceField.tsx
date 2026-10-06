"use client";

import { TriangleAlert } from "lucide-react";
import { Input } from "@/components/ui/input";
import { BilingualText } from "@/components/civic/BilingualText";
import { useLanguage } from "@/lib/LanguageContext";
import type { TranslationKey } from "@/lib/i18n/dictionaries";

const LOW_CONFIDENCE = 0.75;

type Props = {
  id: string;
  labelKey: TranslationKey;
  value: string;
  confidence: number;
  onChange: (value: string) => void;
  inputMode?: "text" | "numeric";
};

/** Every OCR field stays editable; low-confidence fields are flagged in orange with words, not just colour. */
export function ConfidenceField({ id, labelKey, value, confidence, onChange, inputMode = "text" }: Props) {
  const { t } = useLanguage();
  const low = confidence < LOW_CONFIDENCE;
  const warningId = `${id}-warning`;
  return (
    <div
      className={`rounded-2xl border-2 p-4 ${
        low ? "border-[var(--civic-review)] bg-orange-50" : "border-slate-300 bg-[var(--civic-paper)]"
      }`}
    >
      <BilingualText as="label" htmlFor={id} k={labelKey} />
      <Input
        id={id}
        value={value}
        inputMode={inputMode}
        onChange={(event) => onChange(event.target.value)}
        aria-describedby={low ? warningId : undefined}
        className="mt-2 h-14 rounded-xl border-2 border-slate-500 bg-white px-4 text-lg text-[var(--civic-text)]"
      />
      {low && (
        <p id={warningId} className="mt-2 flex items-start gap-2 text-base font-medium text-orange-950">
          <TriangleAlert aria-hidden className="mt-1 h-5 w-5 shrink-0 text-[var(--civic-review)]" />
          {t("status.lowConfidence")}
        </p>
      )}
      <p className="mt-1 text-sm text-[var(--civic-text-muted)]">
        {t("fields.readQuality")}: {Math.round(confidence * 100)}%
      </p>
    </div>
  );
}
