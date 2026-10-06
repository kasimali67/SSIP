import { Suspense } from "react";
import { VerifyFlow } from "@/components/verification/VerifyFlow";

export default function VerifyPage() {
  return (
    <main className="mx-auto w-full max-w-3xl px-4 py-6">
      <Suspense fallback={null}>
        <VerifyFlow />
      </Suspense>
    </main>
  );
}
