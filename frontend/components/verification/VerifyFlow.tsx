"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { StepProgress } from "@/components/civic/StepProgress";
import { VerificationResult } from "@/components/verification/VerificationResult";
import { useLanguage } from "@/lib/LanguageContext";
import type { TranslationKey } from "@/lib/i18n/dictionaries";
import { completeDigiLocker, startDigiLocker, type CrossVerificationResult } from "@/lib/api/verification";
import { clearPendingFields, loadPendingFields, type PendingFields } from "@/lib/verificationStore";

type Phase =
  | { kind: "idle"; fields: PendingFields | null }
  | { kind: "redirecting" }
  | { kind: "verifying"; code: string; state: string; fields: PendingFields }
  | { kind: "done"; result: CrossVerificationResult }
  | { kind: "error"; message: TranslationKey; canRetry: boolean };

function initialPhase(params: URLSearchParams): Phase {
  const fields = loadPendingFields();
  if (params.get("error")) return { kind: "error", message: "verify.denied", canRetry: Boolean(fields) };
  const code = params.get("code");
  const state = params.get("state");
  if (code && state) {
    return fields
      ? { kind: "verifying", code, state, fields }
      : { kind: "error", message: "verify.noDocument", canRetry: false };
  }
  return { kind: "idle", fields };
}

export function VerifyFlow() {
  const { t } = useLanguage();
  const params = useSearchParams();
  const [phase, setPhase] = useState<Phase>(() => initialPhase(new URLSearchParams(params.toString())));
  const started = useRef(false); // the state token is single-use: never submit it twice

  useEffect(() => {
    if (phase.kind !== "verifying" || started.current) return;
    started.current = true;
    completeDigiLocker({ code: phase.code, state: phase.state, fields: phase.fields })
      .then((result) => {
        clearPendingFields();
        window.history.replaceState(null, "", "/verify");
        setPhase({ kind: "done", result });
      })
      .catch(() => setPhase({ kind: "error", message: "verify.failed", canRetry: true }));
  }, [phase]);

  const begin = async () => {
    setPhase({ kind: "redirecting" });
    try {
      const { authorization_url } = await startDigiLocker();
      window.location.assign(authorization_url);
    } catch {
      setPhase({ kind: "error", message: "verify.failed", canRetry: true });
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <StepProgress current={3} />
      <h1 className="text-2xl font-bold text-[var(--civic-ink)]">{t("verify.title")}</h1>

      {phase.kind === "idle" &&
        (phase.fields ? (
          <>
            <p className="text-lg">{t("verify.intro")}</p>
            <Button onClick={begin} className="h-14 rounded-xl bg-[var(--civic-ink)] text-lg font-semibold text-white hover:bg-[var(--civic-ink-hover)]">
              {t("actions.verifyDigilocker")}
            </Button>
          </>
        ) : (
          <NoDocument />
        ))}

      {(phase.kind === "redirecting" || phase.kind === "verifying") && (
        <p role="status" className="flex items-center gap-3 text-lg font-medium">
          <Loader2 aria-hidden className="h-6 w-6 animate-spin" />
          {t(phase.kind === "redirecting" ? "verify.redirecting" : "verify.working")}
        </p>
      )}

      {phase.kind === "done" && <VerificationResult result={phase.result} />}

      {phase.kind === "error" && (
        <div role="alert" className="flex flex-col gap-4">
          <p className="text-lg">{t(phase.message)}</p>
          {phase.canRetry ? (
            <Button onClick={begin} variant="outline" className="h-14 rounded-xl border-2 border-slate-500 text-lg font-semibold">
              {t("actions.tryAgain")}
            </Button>
          ) : (
            <NoDocument />
          )}
        </div>
      )}
    </div>
  );
}

function NoDocument() {
  const { t } = useLanguage();
  return (
    <div className="flex flex-col gap-4">
      <p className="text-lg">{t("verify.noDocument")}</p>
      <Button asChild className="h-14 rounded-xl bg-[var(--civic-ink)] text-lg font-semibold text-white hover:bg-[var(--civic-ink-hover)]">
        <Link href="/upload">{t("actions.uploadDocument")}</Link>
      </Button>
    </div>
  );
}
