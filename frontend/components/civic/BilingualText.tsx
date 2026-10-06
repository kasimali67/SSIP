"use client";

import type { ElementType } from "react";
import { useLanguage } from "@/lib/LanguageContext";
import type { TranslationKey } from "@/lib/i18n/dictionaries";

type Props = {
  k: TranslationKey;
  as?: ElementType;
  htmlFor?: string;
  className?: string;
};

/**
 * Regional label first, English underneath. Many users read one script
 * better than the other, and CSC operators often work in English.
 */
export function BilingualText({ k, as: Tag = "span", htmlFor, className = "" }: Props) {
  const { lang, t, tEn } = useLanguage();
  return (
    <Tag htmlFor={htmlFor} className={`flex flex-col ${className}`}>
      <span className="text-lg font-semibold text-[var(--civic-text)]">{t(k)}</span>
      {lang !== "en" && (
        <span lang="en" className="text-sm text-[var(--civic-text-muted)]">
          {tEn(k)}
        </span>
      )}
    </Tag>
  );
}
