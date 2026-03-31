import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  basePath: "/app",
  transpilePackages: ["@aioj/api", "@aioj/config", "@aioj/tokens", "@aioj/ui"]
};

export default nextConfig;
