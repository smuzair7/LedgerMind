"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, Check, CircleAlert } from "lucide-react";

import { SiteHeader } from "@/components/site-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardHeader, CardTitle, CardBody } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { ProviderGrid } from "@/components/setup/provider-grid";
import { KeyInput } from "@/components/setup/key-input";
import { ApiError } from "@/lib/api-client";
import { listProviders, validateProviderKey, type ProviderInfo } from "@/lib/providers";
import { setProviderKey } from "@/lib/api-client";
import { last4, useAuth } from "@/lib/auth-store";

type Status = "idle" | "validating" | "ok" | "error";

export default function SetupPage() {
  const router = useRouter();
  const setSelection = useAuth((s) => s.setSelection);

  const [providers, setProviders] = React.useState<ProviderInfo[]>([]);
  const [loadingProviders, setLoadingProviders] = React.useState(true);
  const [providerId, setProviderId] = React.useState<string | null>(null);
  const [model, setModel] = React.useState<string>("");
  const [baseUrl, setBaseUrl] = React.useState<string>("");
  const [key, setKey] = React.useState<string>("");
  const [status, setStatus] = React.useState<Status>("idle");
  const [errorMsg, setErrorMsg] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    listProviders()
      .then((list) => {
        if (!cancelled) setProviders(list);
      })
      .catch(() => {
        if (!cancelled) setErrorMsg("Could not reach the backend at /api/providers.");
      })
      .finally(() => {
        if (!cancelled) setLoadingProviders(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const provider = providers.find((p) => p.id === providerId) ?? null;

  React.useEffect(() => {
    if (provider && provider.models.length > 0 && !model) {
      setModel(provider.models[0].id);
    }
  }, [provider, model]);

  const canValidate =
    Boolean(provider && model && key) &&
    (!provider?.needs_base_url || Boolean(baseUrl));

  async function onValidate() {
    if (!provider) return;
    setStatus("validating");
    setErrorMsg(null);
    setProviderKey(key);
    try {
      const result = await validateProviderKey({
        provider: provider.id,
        model,
        base_url: provider.needs_base_url ? baseUrl : undefined,
      });
      if (!result.ok) {
        setStatus("error");
        setErrorMsg(result.detail ?? "Validation failed");
        return;
      }
      setStatus("ok");
      setSelection({
        provider: provider.id,
        model,
        baseUrl: provider.needs_base_url ? baseUrl : null,
        keyLast4: last4(key),
        validatedAt: Date.now(),
      });
      setTimeout(() => router.push("/chat"), 700);
    } catch (e) {
      setStatus("error");
      if (e instanceof ApiError) {
        const code = e.status;
        if (code === 401) setErrorMsg("Invalid key (401).");
        else if (code === 403) setErrorMsg("Key valid but lacks access to this model (403).");
        else if (code === 429) setErrorMsg("Rate limited (429). Try again in a moment.");
        else setErrorMsg(e.message);
      } else {
        setErrorMsg(String(e));
      }
    }
  }

  return (
    <div className="min-h-screen">
      <SiteHeader />
      <main className="container-tight py-12">
        <Link
          href="/"
          className="mb-6 inline-flex items-center gap-1 text-sm text-muted hover:text-ink"
        >
          <ArrowLeft className="h-4 w-4" /> Back
        </Link>

        <h1 className="text-3xl font-semibold tracking-tight">Connect your model</h1>
        <p className="mt-2 max-w-xl text-muted">
          Your key is stored in this browser tab only. It is forwarded per-request in
          the <code>X-Provider-Key</code> header, scrubbed from logs, and never
          persisted on our disk.
        </p>

        {/* Step 1 — provider */}
        <section className="mt-10 space-y-3">
          <div className="flex items-center gap-2">
            <Badge variant="muted">1</Badge>
            <h2 className="text-lg font-semibold">Pick a provider</h2>
          </div>
          {loadingProviders ? (
            <Card className="p-10 text-center text-muted">
              <Spinner className="text-accent" /> Loading providers…
            </Card>
          ) : (
            <ProviderGrid
              providers={providers}
              selected={providerId}
              onSelect={(id) => {
                setProviderId(id);
                setModel("");
                setStatus("idle");
                setErrorMsg(null);
              }}
            />
          )}
        </section>

        {/* Step 2 — model + optional base_url */}
        {provider && (
          <section className="mt-10 space-y-3 animate-fade-in">
            <div className="flex items-center gap-2">
              <Badge variant="muted">2</Badge>
              <h2 className="text-lg font-semibold">Choose a model</h2>
            </div>
            <Card>
              <CardHeader>
                <CardTitle>{provider.label}</CardTitle>
              </CardHeader>
              <CardBody className="space-y-4">
                <div>
                  <label htmlFor="model" className="block text-xs font-medium text-muted">
                    Model
                  </label>
                  <select
                    id="model"
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    className="mt-1 h-10 w-full rounded-md border border-border bg-surface2 px-3 text-sm text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
                  >
                    {provider.models.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.label}
                        {m.context_window
                          ? ` — ${(m.context_window / 1000).toFixed(0)}K ctx`
                          : ""}
                      </option>
                    ))}
                  </select>
                </div>
                {provider.needs_base_url && (
                  <div>
                    <label
                      htmlFor="base_url"
                      className="block text-xs font-medium text-muted"
                    >
                      Base URL (OpenAI-compatible)
                    </label>
                    <Input
                      id="base_url"
                      value={baseUrl}
                      onChange={(e) => setBaseUrl(e.target.value)}
                      placeholder="https://openrouter.ai/api/v1"
                      className="mt-1"
                    />
                  </div>
                )}
              </CardBody>
            </Card>
          </section>
        )}

        {/* Step 3 — key */}
        {provider && model && (
          <section className="mt-10 space-y-3 animate-fade-in">
            <div className="flex items-center gap-2">
              <Badge variant="muted">3</Badge>
              <h2 className="text-lg font-semibold">Paste your API key</h2>
            </div>
            <Card>
              <CardBody className="space-y-4 pt-5">
                <KeyInput value={key} onChange={setKey} />
                <div className="flex flex-wrap items-center gap-3">
                  <Button
                    onClick={onValidate}
                    disabled={!canValidate || status === "validating"}
                    size="md"
                  >
                    {status === "validating" && <Spinner />}
                    {status === "ok" ? "Validated" : "Validate key"}
                  </Button>
                  {status === "ok" && (
                    <span className="inline-flex items-center gap-1.5 text-sm text-positive">
                      <Check className="h-4 w-4" /> Key works. Redirecting…
                    </span>
                  )}
                  {status === "error" && errorMsg && (
                    <span className="inline-flex items-center gap-1.5 text-sm text-negative">
                      <CircleAlert className="h-4 w-4" /> {errorMsg}
                    </span>
                  )}
                </div>
                <p className="text-xs text-muted">
                  We send one minimal completion to confirm the key works with the
                  selected model. Nothing is persisted.
                </p>
              </CardBody>
            </Card>
          </section>
        )}
      </main>
    </div>
  );
}
