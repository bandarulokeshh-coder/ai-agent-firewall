/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  // NOTE: /api/dashboard, /api/pending, /api/tool-call/* are Next.js route
  // handlers (app/api/...) that proxy to the backend with caching disabled.
  // Do NOT add a blanket /api/:path* rewrite here — it would shadow those
  // routes and bypass them.
};

module.exports = nextConfig;