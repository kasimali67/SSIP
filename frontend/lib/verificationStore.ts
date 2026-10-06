/**
 * Holds the confirmed OCR fields across the DigiLocker redirect.
 * sessionStorage (tab-scoped, cleared when the tab closes) holds name, date of
 * birth and only the LAST 4 ID digits. Cleared as soon as verification returns.
 */
export type PendingField = { value: string | null; confidence: number };

export type PendingFields = {
  name: PendingField;
  dob: PendingField;
  id_last4: PendingField;
};

const KEY = "pending-verification-fields";

function isField(value: unknown): value is PendingField {
  if (typeof value !== "object" || value === null) return false;
  const field = value as Record<string, unknown>;
  return (
    (field.value === null || typeof field.value === "string") &&
    typeof field.confidence === "number" &&
    field.confidence >= 0 &&
    field.confidence <= 1
  );
}

/** Accepts "XXXX-XXXX-4821", "4821" or a full number and keeps only the last 4 digits. */
export function toLast4(raw: string | null | undefined): string | null {
  const digits = (raw ?? "").replace(/\D/g, "").slice(-4);
  return digits.length === 4 ? digits : null;
}

export function savePendingFields(fields: PendingFields): void {
  const safe: PendingFields = { ...fields, id_last4: { ...fields.id_last4, value: toLast4(fields.id_last4.value) } };
  window.sessionStorage.setItem(KEY, JSON.stringify(safe));
}

export function loadPendingFields(): PendingFields | null {
  if (typeof window === "undefined") return null;
  try {
    const parsed: unknown = JSON.parse(window.sessionStorage.getItem(KEY) ?? "null");
    if (typeof parsed !== "object" || parsed === null) return null;
    const record = parsed as Record<string, unknown>;
    return isField(record.name) && isField(record.dob) && isField(record.id_last4)
      ? { name: record.name, dob: record.dob, id_last4: record.id_last4 }
      : null;
  } catch {
    return null;
  }
}

export function clearPendingFields(): void {
  window.sessionStorage.removeItem(KEY);
}
