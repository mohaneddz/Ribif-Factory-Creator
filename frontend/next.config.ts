import type { NextConfig } from "next";

const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:5000";

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
    async rewrites() {
        // Only use rewrites in development when no explicit backend URL is set
        // In production (Vercel), frontend will call the backend directly via NEXT_PUBLIC_BACKEND_URL
        if (process.env.NODE_ENV === 'development' && !process.env.NEXT_PUBLIC_BACKEND_URL) {
            return [
                {
                    source: "/api/:path*",
                    destination: "http://127.0.0.1:5000/api/:path*",
                },
            ];
        }
        return [];
    },
    async headers() {
        return [
            {
                // Apply to all routes
                source: "/:path*",
                headers: [
                    { key: "Access-Control-Allow-Credentials", value: "true" },
                    { key: "Access-Control-Allow-Origin", value: "*" },
                    { key: "Access-Control-Allow-Methods", value: "GET,DELETE,PATCH,POST,PUT,OPTIONS" },
                    { key: "Access-Control-Allow-Headers", value: "X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version, X-User-Id, X-Project-Id, Authorization" },
                ],
            },
        ];
    },
    devIndicators: false,
};

export default nextConfig;
