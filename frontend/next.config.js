/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  images: {
    unoptimized: true,
  },
  
  // Configuration des métadonnées
  metadataBase: new URL(process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8012'),

  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8012"}/:path*`,
      },
    ];
  },

  serverExternalPackages: [],
};

module.exports = nextConfig;
