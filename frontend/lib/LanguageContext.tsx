"use client";

/**
 * Replaces the earlier placeholder LanguageContext.
 * - t(key): label in the selected language (falls back to English)
 * - tEn(key): English label, used for the secondary line of bilingual labels
 * - keeps <html lang> in sync so fonts and screen readers switch script
 *
 * The selection lives in localStorage, read through useSyncExternalStore so the
 * server render (English) and the first client render never mismatch.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useSyncExternalStore, type ReactNode } from "react";
import { dictionaries, LANGS, type Lang, type TranslationKey } from "@/lib/i18n/dictionaries";

const STORAGE_KEY = "preferred-language";
const listeners = new Set<() => void>();
let memoryLang: Lang = "en"; // used when localStorage is unavailable

function readLang(): Lang {
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (LANGS.includes(saved as Lang)) return saved as Lang;
  } catch {
    /* fall through to in-memory value */
  }
  return memoryLang;
}

function writeLang(next: Lang): void {
  memoryLang = next;
  try {
    window.localStorage.setItem(STORAGE_KEY, next);
  } catch {
    /* selection still applies for this visit */
  }
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  window.addEventListener("storage", listener);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", listener);
  };
}

type LanguageContextValue = {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: (key: TranslationKey) => string;
  tEn: (key: TranslationKey) => string;
};

const LanguageContext = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const lang = useSyncExternalStore(subscribe, readLang, () => "en" as Lang);
  const setLang = useCallback((next: Lang) => writeLang(next), []);

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const value = useMemo<LanguageContextValue>(
    () => ({
      lang,
      setLang,
      t: (key) => dictionaries[lang][key] ?? dictionaries.en[key],
      tEn: (key) => dictionaries.en[key],
    }),
    [lang, setLang],
  );

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage(): LanguageContextValue {
  const context = useContext(LanguageContext);
  if (!context) throw new Error("useLanguage must be used inside <LanguageProvider>");
  return context;
}
