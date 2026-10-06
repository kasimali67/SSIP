"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { FlaskConical, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useLanguage } from "@/lib/LanguageContext";
import type { TranslationKey } from "@/lib/i18n/dictionaries";

const PERSONAS = [
  { id: "match", label: "consent.persona.match" },
  { id: "spelling_variant", label: "consent.persona.spelling_variant" },
  { id: "dob_mismatch", label: "consent.persona.dob_mismatch" },
] as const satisfies readonly { id: string; label: TranslationKey }[];

const SHARED_FIELDS: TranslationKey[] = ["fields.name", "fields.dob", "fields.gender", "fields.idLast4"];

/**
 * Simulated consent screen for DIGILOCKER_MODE=sandbox. Deliberately labelled
 * as simulated and styled as this app, not as DigiLocker, so it can never be
 * mistaken for the real government service.
 */
export function SandboxConsent() {
  const { t } = useLanguage();
  const router = useRouter();
  const params = useSearchParams();
  const [persona, setPersona] = useState<(typeof PERSONAS)[number]["id"]>("match");
  const state = params.get("state") ?? "";

  if (process.env.NEXT_PUBLIC_DEMO_MODE !== "true") {
    return <p className="text-lg">{t("consent.unavailable")}</p>;
  }
  if (!/^[A-Za-z0-9_-]{20,128}$/.test(state)) {
    return <p className="text-lg">{t("consent.invalid")}</p>;
  }

  const go = (query: Record<string, string>) => router.push(`/verify?${new URLSearchParams({ ...query, state })}`);

  return (
    <section className="rounded-2xl border-2 border-slate-300 bg-[var(--civic-paper)] p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="flex items-center gap-2 text-2xl font-bold text-[var(--civic-ink)]">
          <ShieldCheck aria-hidden className="h-7 w-7" />
          {t("consent.title")}
        </h1>
        <span className="inline-flex items-center gap-1 rounded-full border-2 border-amber-600 bg-amber-100 px-3 py-1 text-sm font-semibold text-amber-950">
          <FlaskConical aria-hidden className="h-4 w-4" />
          {t("consent.simulated")}
        </span>
      </div>

      <p className="mt-4 text-lg">{t("consent.body")}</p>
      <ul className="mt-2 list-disc pl-6 text-lg">
        {SHARED_FIELDS.map((key) => (
          <li key={key}>{t(key)}</li>
        ))}
      </ul>

      <label htmlFor="persona" className="mt-5 block text-base font-semibold">
        {t("consent.persona")}
      </label>
      <select
        id="persona"
        value={persona}
        onChange={(event) => setPersona(event.target.value as typeof persona)}
        className="mt-1 h-14 w-full rounded-xl border-2 border-slate-500 bg-white px-3 text-lg"
      >
        {PERSONAS.map((item) => (
          <option key={item.id} value={item.id}>
            {t(item.label)}
          </option>
        ))}
      </select>

      <div className="mt-6 flex flex-col gap-3 sm:flex-row">
        <Button
          onClick={() => go({ code: `sandbox:${persona}` })}
          className="h-14 flex-1 rounded-xl bg-[var(--civic-ink)] text-lg font-semibold text-white hover:bg-[var(--civic-ink-hover)]"
        >
          {t("consent.allow")}
        </Button>
        <Button
          variant="outline"
          onClick={() => go({ error: "access_denied" })}
          className="h-14 flex-1 rounded-xl border-2 border-slate-500 text-lg font-semibold"
        >
          {t("consent.deny")}
        </Button>
      </div>
    </section>
  );
}
