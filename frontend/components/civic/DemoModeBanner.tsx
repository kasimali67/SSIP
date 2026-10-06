"use client";

import { FlaskConical } from "lucide-react";
import { useLanguage } from "@/lib/LanguageContext";

/**
 * Not dismissible on purpose: anyone watching the demo should always know the
 * DigiLocker record is simulated.
 */
export function DemoModeBanner() {
  const { t } = useLanguage();
  if (process.env.NEXT_PUBLIC_DEMO_MODE !== "true") return null;
  return (
    <div role="note" className="border-b-2 border-amber-600 bg-amber-100 px-4 py-2 text-amber-950">
      <p className="mx-auto flex max-w-5xl items-center gap-2 text-base font-medium">
        <FlaskConical aria-hidden className="h-5 w-5 shrink-0" />
        {t("demo.banner")}
      </p>
    </div>
  );
}
