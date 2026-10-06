"use client";

import { useLanguage } from "@/lib/LanguageContext";
import { LANGS, NATIVE_LANGUAGE_NAMES } from "@/lib/i18n/dictionaries";

/** Languages are shown in their own script ("ગુજરાતી", not "GU") so users recognise them. */
export function LanguageSwitcher() {
  const { lang, setLang, t } = useLanguage();
  return (
    <div role="group" aria-label={t("nav.language")} className="flex gap-1 rounded-xl border-2 border-slate-300 bg-white p-1">
      {LANGS.map((code) => {
        const active = code === lang;
        return (
          <button
            key={code}
            type="button"
            lang={code}
            aria-pressed={active}
            onClick={() => setLang(code)}
            className={`min-h-11 min-w-11 rounded-lg px-3 text-base font-semibold ${
              active ? "bg-[var(--civic-ink)] text-white" : "text-[var(--civic-text)] hover:bg-slate-100"
            }`}
          >
            {NATIVE_LANGUAGE_NAMES[code]}
          </button>
        );
      })}
    </div>
  );
}
