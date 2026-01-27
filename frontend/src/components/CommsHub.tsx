"use client";
import { useState, useEffect } from "react";
import { Mic, Phone } from "lucide-react";

export default function CommsHub() {
    const [status, setStatus] = useState("IDLE");

    useEffect(() => {
        const interval = setInterval(() => {
            setStatus("DIALING");
            setTimeout(() => setStatus("NEGOTIATING: BASF Germany ($2.4/kg)"), 2000);
            setTimeout(() => setStatus("IDLE"), 6000);
        }, 10000);
        return () => clearInterval(interval);
    }, []);

    return (

        <div className="bg-white border border-slate-200 dark:bg-[#13141c] dark:border-white/10 rounded-lg p-4 flex items-center gap-4 transition-colors">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center ${status !== 'IDLE' ? 'bg-red-50 dark:bg-red-900/50 text-red-600 dark:text-red-500 animate-pulse' : 'bg-slate-100 dark:bg-white/10 text-slate-500 dark:text-slate-400'}`}>
                <Mic size={20} />
            </div>
            <div>
                <div className="text-[10px] text-slate-500 dark:text-slate-400 font-bold uppercase">AI Voice Agent</div>
                <div className="text-xs text-slate-900 dark:text-slate-200 font-mono">{status}</div>
            </div>
        </div>
    )

}