import { createClient } from "@supabase/supabase-js";
import type { ZoneDef } from "../types";

export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_ANON_KEY,
);

export async function loadZones(storeId = "default"): Promise<ZoneDef[]> {
  const { data, error } = await supabase
    .from("zones")
    .select("*")
    .eq("store_id", storeId)
    .order("created_at");
  if (error) throw error;
  return (data ?? []) as unknown as ZoneDef[];
}

export async function saveZone(
  name: string,
  polygon: { x: number; y: number }[],
  storeId = "default",
): Promise<void> {
  const { error } = await supabase
    .from("zones")
    .insert({ store_id: storeId, name, polygon });
  if (error) throw error;
}
