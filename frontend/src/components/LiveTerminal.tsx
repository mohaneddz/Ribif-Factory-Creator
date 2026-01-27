"use client";
import { useEffect, useState, useRef } from "react";
import { Terminal } from "lucide-react";

const LOGS_SOURCE = [
    "CONNECTING: Global_Supplier_Net [SECURE]",
    "SCRAPING: Alibaba API... Found 14 matches for 'Polyurethane'",
    "PARSING: Tech_Sheet_A1.pdf... 98% Confidence",
    "CALCULATING: TCO (Total Cost of Ownership)...",
    "OPTIMIZING: Logistics Route (China -> Algeria)",
    "GENERATING: IFC Model for Zone Z1...",
    "CHECKING: ATEX Compliance... [PASSED]",
];

export default function LiveTerminal() {
    const [logs, setLogs] = useState<string[]>([]);
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        let i = 0;
        const interval = setInterval(() => {
            const timestamp = new Date().toLocaleTimeString('en-US', { hour12: false });
            setLogs(prev => [...prev.slice(-10), `[${timestamp}] ${LOGS_SOURCE[i % LOGS_SOURCE.length]}`]);
            i++;
        }, 800);
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }, [logs]);

    return (
        <div className="bg-white border border-slate-200 dark:bg-black dark:border-slate-800 rounded-lg font-mono text-[10px] h-48 flex flex-col shadow-inner transition-colors">
            <div className="bg-slate-50 border-b border-slate-200 dark:bg-slate-900 dark:border-slate-800 px-3 py-1 flex items-center gap-2">
                <Terminal size={12} className="text-indigo-600 dark:text-[#66fcf1]" />
                <span className="text-slate-500 dark:text-slate-400">RIBIF_KERNEL.exe</span>
            </div>
            <div ref={scrollRef} className="p-3 overflow-hidden flex-1 text-slate-700 dark:text-[#66fcf1] space-y-1">
                {logs.map((log, i) => <div key={i}>{log}</div>)}
                <div className="animate-pulse text-indigo-600 dark:text-[#66fcf1]">_</div>
            </div>
        </div>
    );
}