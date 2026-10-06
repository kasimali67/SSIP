/**
 * Typed client for the verification endpoints. Attaches the Supabase session
 * token when one exists (mock auth mode works without it).
 * MERGE NOTE: adjust the supabase import if your client is exported differently.
 */
import { getSupabaseClient } from "@/lib/supabaseClient";
import type { PendingFields } from "@/lib/verificationStore";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type FieldStatus = "match" | "review" | "mismatch" | "missing";
export type OverallStatus = "verified" | "needs_review" | "mismatch";
export type ComparedField = "name" | "dob" | "id_last4";

export type FieldComparison = {
  field: ComparedField;
  status: FieldStatus;
  reason: string;
  score: number;
  low_ocr_confidence: boolean;
  document_value: string | null;
  official_value: string | null;
};

export type CrossVerificationResult = {
  overall: OverallStatus;
  fields: FieldComparison[];
  issuer: string;
  is_sandbox: boolean;
};

export type DigiLockerStart = { authorization_url: string; state: string; is_sandbox: boolean };

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
  }
}

async function authHeaders(): Promise<Record<string, string>> {
  const { data } = await getSupabaseClient().auth.getSession();
  const token = data.session?.access_token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await authHeaders()) },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);
    const message =
      typeof payload === "object" && payload !== null && "message" in payload
        ? String((payload as { message: unknown }).message)
        : `Request failed (${response.status})`;
    throw new ApiError(response.status, message);
  }
  return (await response.json()) as T;
}

export function startDigiLocker(): Promise<DigiLockerStart> {
  return postJson<DigiLockerStart>("/api/verification/digilocker/start", { document_type: "aadhaar" });
}

export function completeDigiLocker(input: { code: string; state: string; fields: PendingFields }): Promise<CrossVerificationResult> {
  return postJson<CrossVerificationResult>("/api/verification/digilocker/complete", input);
}
