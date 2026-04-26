import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Standalone output untuk Docker prod (size minimal)
  output: "standalone",

  reactStrictMode: true,

  // ESLint warning/cosmetic tidak boleh menggagalkan production build di VPS.
  // Tetap jalan via 'npm run lint' utk dev — hanya skip saat build.
  eslint: {
    ignoreDuringBuilds: true,
  },
  // TypeScript error TETAP fail build (indikator bug nyata, bukan kosmetik).
  typescript: {
    ignoreBuildErrors: false,
  },

  // Re-write /api/* ke backend untuk dev tanpa Caddy.
  // Saat di prod (Caddy ada), Caddy yang pegang routing /api/*.
  // Re-write ini hanya aktif kalau NEXT_PUBLIC_API_BASE_URL kosong (mode dev).
  async rewrites() {
    if (process.env.NEXT_PUBLIC_API_BASE_URL) return [];
    const internal = process.env.INTERNAL_API_BASE_URL || "http://backend:8000";
    return [
      { source: "/api/:path*", destination: `${internal}/api/:path*` },
      { source: "/django-admin/:path*", destination: `${internal}/django-admin/:path*` },
      { source: "/static/:path*", destination: `${internal}/static/:path*` },
      { source: "/media/:path*", destination: `${internal}/media/:path*` },
    ];
  },

  // Mute warning trace upload pixel di production
  poweredByHeader: false,
};

export default nextConfig;
