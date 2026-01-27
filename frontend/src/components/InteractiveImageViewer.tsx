"use client";

import { useState, useRef } from "react";
import { motion, useMotionValue, useTransform } from "framer-motion";
import { ZoomIn, ZoomOut, Maximize, RefreshCw } from "lucide-react";

interface InteractiveImageViewerProps {
    src: string;
    alt: string;
    className?: string;
}

export default function InteractiveImageViewer({
    src,
    alt,
    className = "",
}: InteractiveImageViewerProps) {
    const [scale, setScale] = useState(1);
    const containerRef = useRef<HTMLDivElement>(null);

    // Handlers
    const handleZoomIn = () => setScale((s) => Math.min(s + 0.5, 5));
    const handleZoomOut = () => setScale((s) => Math.max(s - 0.5, 0.5));
    const handleReset = () => setScale(1);

    return (
        <div
            ref={containerRef}
            className={`relative w-full h-full overflow-hidden bg-slate-50/50 dark:bg-[#0b0c10]/50 flex items-center justify-center ${className}`}
        >
            {/* Controls */}
            <div className="absolute top-4 right-4 flex flex-col gap-2 z-20">
                <button
                    onClick={handleZoomIn}
                    className="p-2 bg-white dark:bg-slate-800 rounded-lg shadow-lg border border-slate-200 dark:border-white/10 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition-colors"
                    title="Zoom In"
                >
                    <ZoomIn size={18} />
                </button>
                <button
                    onClick={handleZoomOut}
                    className="p-2 bg-white dark:bg-slate-800 rounded-lg shadow-lg border border-slate-200 dark:border-white/10 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition-colors"
                    title="Zoom Out"
                >
                    <ZoomOut size={18} />
                </button>
                <button
                    onClick={handleReset}
                    className="p-2 bg-white dark:bg-slate-800 rounded-lg shadow-lg border border-slate-200 dark:border-white/10 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition-colors"
                    title="Reset View"
                >
                    <RefreshCw size={18} />
                </button>
            </div>

            {/* Image */}
            <motion.div
                drag
                dragConstraints={containerRef}
                dragElastic={0.1}
                animate={{ scale }}
                transition={{ type: "spring", stiffness: 300, damping: 30 }}
                className="cursor-move"
                style={{ touchAction: "none" }} // Prevent browser zoom gestures
            >
                <img
                    src={src}
                    alt={alt}
                    className="max-w-none max-h-none object-contain pointer-events-none dark:invert-[.1] transition-all duration-300"
                    style={{
                        // Logic to ensure it fits initially but can grow
                        maxWidth: scale === 1 ? "100%" : "none",
                        maxHeight: scale === 1 ? "100%" : "none",
                        height: scale === 1 ? "auto" : undefined,
                        width: scale === 1 ? "auto" : undefined,
                    }}
                    draggable={false}
                />
                {/* Force size when scaled up to avoid layout collapse */}
                <img
                    src={src}
                    className="invisible absolute top-0 left-0 -z-10"
                    alt="spacer"
                    style={{ width: "auto", height: "auto" }}
                />
            </motion.div>
        </div>
    );
}
