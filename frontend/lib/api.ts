import { getSupabaseClient } from "@/lib/supabaseClient";

export interface OcrField {
  value: string | null;
  confidence: number;
}

export interface OcrExtractResponse {
  name: OcrField;
  dob: OcrField;
  id_number: OcrField;
  audit_logged?: boolean;
}

export interface RagQueryRequest {
  question: string;
}

export interface RagQueryResponse {
  answer: string;
  sources: string[];
}

interface ApiErrorBody {
  code: number;
  message: string;
  details?: Record<string, unknown>;
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  readonly status: number;
  readonly details: Record<string, unknown> | undefined;

  constructor(
    status: number,
    message: string,
    details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

async function getAuthToken(): Promise<string> {
  const { data, error } = await getSupabaseClient().auth.getSession();

  if (error) {
    throw new ApiError(401, "Unable to read the current session.");
  }

  const token = data.session?.access_token;
  if (!token) {
    throw new ApiError(401, "You must be signed in to use this feature.");
  }
  return token;
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
  const token = await getAuthToken();
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  });

  const payload: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const body = payload as Partial<ApiErrorBody> | null;
    throw new ApiError(
      response.status,
      body?.message ?? "The request failed.",
      body?.details,
    );
  }

  return payload as T;
}

export async function extractOcr(file: File): Promise<OcrExtractResponse> {
  const formData = new FormData();
  formData.append("file", file);

  return request<OcrExtractResponse>("/api/ocr/extract", {
    method: "POST",
    body: formData,
  });
}

export async function queryRag(question: string): Promise<RagQueryResponse> {
  const body: RagQueryRequest = { question };

  return request<RagQueryResponse>("/api/rag/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
