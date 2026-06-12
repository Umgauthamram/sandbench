import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Produce a minimal, self-contained server bundle for the Docker image.
  // See frontend/Dockerfile.
  output: "standalone",
};

export default nextConfig;
