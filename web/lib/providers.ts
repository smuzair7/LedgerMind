import { apiFetch } from "./api-client";

export interface ModelInfo {
  id: string;
  label: string;
  context_window: number | null;
  supports_tools: boolean;
  family: string | null;
}

export interface ProviderInfo {
  id: string;
  label: string;
  description: string | null;
  website: string | null;
  key_url: string | null;
  requires_key: boolean;
  models: ModelInfo[];
  needs_base_url: boolean;
}

export interface ValidateResponse {
  ok: boolean;
  detail: string | null;
}

export async function listProviders(): Promise<ProviderInfo[]> {
  return apiFetch<ProviderInfo[]>("/api/providers");
}

export async function validateProviderKey(payload: {
  provider: string;
  model?: string;
  base_url?: string;
}): Promise<ValidateResponse> {
  return apiFetch<ValidateResponse>("/api/providers/validate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
