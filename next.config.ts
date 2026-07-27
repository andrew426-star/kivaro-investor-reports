import type { NextConfig } from "next";

// Deliberately no cacheComponents — /api/insights is a plain route handler
// with its own server-side interval caching, not a Server-Component
// data-fetching flow.
const nextConfig: NextConfig = {};

export default nextConfig;
