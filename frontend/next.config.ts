import type { NextConfig } from "next";

const nextConfig: NextConfig = {
    // Transpile R3F packages to fix Turbopack bundling issues
    transpilePackages: [
        "@react-three/fiber",
        "@react-three/drei",
        "three",
    ],
    // Increase timeouts for long-running API operations (e.g., enrichment)
    experimental: {
        proxyTimeout: 600000, // 10 minutes for enrichment operations
    },
    async rewrites() {
        return [
            {
                source: "/api/:path*",
                destination: "http://127.0.0.1:5000/api/:path*",
            },
        ];
    },
    devIndicators: false,
};

export default nextConfig;
