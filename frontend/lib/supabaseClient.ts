import {
  createClient as createSupabaseClient,
  type SupabaseClient,
} from "@supabase/supabase-js";

export function createClient(): SupabaseClient {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!url || !anonKey) {
    throw new Error(
      "Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY. Copy .env.local.example to .env.local and fill in values.",
    );
  }

  return createSupabaseClient(url, anonKey);
}

let browserClient: SupabaseClient | null = null;

export function getSupabaseClient(): SupabaseClient {
  if (!browserClient) {
    browserClient = createClient();
  }
  return browserClient;
}
