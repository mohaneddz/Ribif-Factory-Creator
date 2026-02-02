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
        serverActions: {
            bodySizeLimit: '50mb',
        },
    },
    // Allow larger request bodies for API routes and middleware (module9/catalog needs >10MB)
    serverExternalPackages: [],
    // Increase body size limit for all routes
    api: {
        bodyParser: {
            sizeLimit: '50mb',
        },
        responseLimit: false,
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
