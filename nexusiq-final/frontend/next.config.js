/** @type {import('next').NextConfig} */
const nextConfig = {
  // NOTE: Do NOT use output: "standalone" on Vercel — it breaks routing.
  // Standalone is only needed for Docker/self-hosted deployments.
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  },
};

module.exports = nextConfig;
