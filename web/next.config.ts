import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  env: { NEXT_PUBLIC_POLL: process.env.VERCEL ? "1" : "", NEXT_PUBLIC_API: process.env.NEXT_PUBLIC_API ?? (process.env.VERCEL ? "/server" : "http://localhost:8080") },
  /* config options here */
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
