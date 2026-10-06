import { Suspense } from "react";
import { SandboxConsent } from "@/components/verification/SandboxConsent";

export default function SandboxConsentPage() {
  return (
    <main className="mx-auto w-full max-w-xl px-4 py-8">
      <Suspense fallback={null}>
        <SandboxConsent />
      </Suspense>
    </main>
  );
}
