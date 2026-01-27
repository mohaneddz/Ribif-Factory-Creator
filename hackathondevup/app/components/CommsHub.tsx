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
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 flex items-center gap-4">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center ${status !== 'IDLE' ? 'bg-red-900/50 text-red-500 animate-pulse' : 'bg-slate-800 text-slate-600'}`}>
                <Mic size={20} />
            </div>
            <div>
                <div className="text-[10px] text-slate-500 font-bold uppercase">AI Voice Agent</div>
                <div className="text-xs text-white font-mono">{status}</div>
            </div>
        </div>
    );
}