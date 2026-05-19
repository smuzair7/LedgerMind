/** @type {import('next').NextConfig} */
const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  experimental: {
    typedRoutes: false,
  },
  async rewrites() {
    // Non-proxy routes pass through; /api/proxy/* is handled by our edge route
    // (because it needs to stream SSE and forward X-Provider-Key safely).
    return [];
  },
  env: {
    NEXT_PUBLIC_API_BASE: API_BASE,
  },
};

export default nextConfig;
