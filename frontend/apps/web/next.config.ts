import type { NextConfig } from "next";

const APP_URL = process.env.APP_URL || "http://localhost:4001";
const ADMIN_URL = process.env.ADMIN_URL || "http://localhost:4002";

const nextConfig: NextConfig = {
  transpilePackages: ["@aioj/api", "@aioj/config", "@aioj/tokens", "@aioj/ui"],
  async rewrites() {
    return [
      {
        source: "/app",
        destination: `${APP_URL}/app`,
      },
      {
        source: "/app/:path*",
        destination: `${APP_URL}/app/:path*`,
      },
      {
        source: "/admin",
        destination: `${ADMIN_URL}/admin`,
      },
      {
        source: "/admin/:path*",
        destination: `${ADMIN_URL}/admin/:path*`,
      },
    ];
  },
};

export default nextConfig;
