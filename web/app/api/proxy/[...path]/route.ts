/**
 * Edge SSE proxy: forwards requests (including X-Provider-Key) to the FastAPI
 * backend and streams the response body back without buffering.
 *
 * Why this exists:
 *   - The browser EventSource API can't set custom headers (no X-Provider-Key).
 *     We use fetch + ReadableStream, but in some deployments (Vercel Node
 *     runtime) the response is buffered before reaching the client. The Edge
 *     runtime + an explicit no-buffering header pair fixes that.
 *   - Same-origin requests simplify CORS for the demo deployment.
 */

import { NextRequest } from "next/server";

export const runtime = "edge";
export const dynamic = "force-dynamic";

const BACKEND = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function proxy(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  const targetPath = "/" + path.join("/");
  const url = new URL(targetPath + req.nextUrl.search, BACKEND);

  // Forward headers but drop hop-by-hop ones.
  const headers = new Headers(req.headers);
  headers.delete("host");
  headers.delete("connection");

  const init: RequestInit = {
    method: req.method,
    headers,
    body: req.method === "GET" || req.method === "HEAD" ? undefined : req.body,
    // @ts-expect-error duplex is required for streaming bodies in Edge
    duplex: "half",
  };

  const upstream = await fetch(url.toString(), init);

  const respHeaders = new Headers(upstream.headers);
  respHeaders.set("Cache-Control", "no-store");
  respHeaders.set("X-Accel-Buffering", "no");

  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: respHeaders,
  });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
