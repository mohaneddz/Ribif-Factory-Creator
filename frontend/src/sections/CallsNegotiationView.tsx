import { Check, Phone, Sparkles } from "lucide-react";

import CommsHub from "@/components/CommsHub";

const CALL_LOG = [
    { speaker: "RIBIF AI", time: "00:12", text: "Hello, we would like to confirm an extra discount to secure the volume." },
    { speaker: "Supplier", time: "00:24", text: "We can consider -3% if the order is firm this quarter." },
    { speaker: "RIBIF AI", time: "00:42", text: "We can sign a quarterly commitment if lead time is reduced to 18 days." },
    { speaker: "Supplier", time: "01:03", text: "Agreed on 18 days and -4% on the first two lots." },
];

export const CallsNegotiationView = () => (
    <div className="h-full p-6 flex flex-col gap-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
                <div className="text-[10px] font-bold uppercase tracking-[0.3em] text-emerald-500">Phone Calls</div>
                <h2 className="text-2xl font-black text-slate-800 mt-2">Supplier voice negotiation</h2>
                <p className="text-sm text-slate-500 mt-1">AI voice agent for live calls and offer summaries.</p>
            </div>
            <button className="bg-slate-900 text-white px-5 py-2 rounded-full text-xs font-bold flex items-center gap-2 shadow-lg shadow-slate-200">
                <Sparkles size={14} /> Start a call
            </button>
        </div>

        <div className="grid lg:grid-cols-[1fr_1.2fr] gap-6 flex-1">
            <div className="bg-white border border-slate-200 rounded-4xl shadow-sm p-6 flex flex-col gap-5">
                <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center border border-emerald-100">
                        <Phone size={20} />
                    </div>
                    <div>
                        <div className="text-xs uppercase tracking-widest text-slate-400 font-bold">Live Call</div>
                        <div className="text-sm font-extrabold text-slate-800">Active session</div>
                    </div>
                </div>

                <CommsHub />

                <div className="rounded-2xl border border-slate-200 p-4 bg-slate-50">
                    <div className="text-xs uppercase tracking-widest text-slate-400 font-bold">AI summary</div>
                    <p className="text-sm text-slate-600 mt-2">
                        Final offer obtained: <span className="font-semibold text-slate-800">-4% discount</span> and
                        <span className="font-semibold text-slate-800"> 18-day lead time</span>.
                    </p>
                </div>

                <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-2xl border border-slate-200 p-4">
                        <div className="text-xs uppercase tracking-widest text-slate-400 font-bold">Score</div>
                        <div className="text-2xl font-black text-slate-900 mt-2">91/100</div>
                        <div className="text-xs text-slate-400">Supplier reliability</div>
                    </div>
                    <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
                        <div className="text-xs uppercase tracking-widest text-emerald-500 font-bold">Status</div>
                        <div className="flex items-center gap-2 mt-2 text-emerald-600 font-semibold">
                            <Check size={16} /> Verbal agreement
                        </div>
                        <div className="text-xs text-emerald-500/80">Transcript ready</div>
                    </div>
                </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-4xl shadow-xl shadow-slate-200/20 p-6 flex flex-col">
                <div className="flex items-center justify-between mb-4">
                    <div>
                        <div className="text-[10px] uppercase tracking-[0.3em] text-slate-400 font-bold">Transcript</div>
                        <h3 className="text-lg font-black text-white mt-2">Real-time negotiation</h3>
                    </div>
                    <div className="text-xs font-bold text-slate-400">Voice - EN</div>
                </div>
                <div className="flex-1 space-y-3 overflow-y-auto">
                    {CALL_LOG.map((entry, idx) => (
                        <div key={`${entry.time}-${idx}`} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                            <div className="flex items-center justify-between text-xs text-slate-400">
                                <span className="font-bold uppercase tracking-widest">{entry.speaker}</span>
                                <span>{entry.time}</span>
                            </div>
                            <p className="text-sm text-slate-100 mt-2">{entry.text}</p>
                        </div>
                    ))}
                </div>
                <div className="mt-4 rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-200">
                    Next action: generate a written recap and send via Email Center.
                </div>
            </div>
        </div>
    </div>
);
