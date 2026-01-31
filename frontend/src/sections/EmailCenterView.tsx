import { Calendar, Check, Mail, Send, Sparkles } from "lucide-react";

const EMAIL_THREADS = [
    {
        supplier: "Nordic Machines",
        subject: "Counter-offer - Injection press",
        preview: "Revised proposal with extended warranty and 6% discount.",
        status: "Pending",
        time: "2h ago",
    },
    {
        supplier: "Shenzhen Resins",
        subject: "Incoterms and lead time",
        preview: "CIF option validated, 21-day transit. Terms proposed.",
        status: "AI Draft",
        time: "5h ago",
    },
    {
        supplier: "EuroPress Group",
        subject: "Final response",
        preview: "Agreement on MOQ and on-site pre-inspection.",
        status: "Confirmed",
        time: "Yesterday",
    },
];

export const EmailCenterView = () => (
    <div className="h-full p-6 flex flex-col gap-6 bg-slate-50 dark:bg-[#0b0c10] transition-colors">
        <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
                <div className="text-[10px] font-bold uppercase tracking-[0.3em] text-indigo-500">Email Center</div>
                <h2 className="text-2xl font-black text-slate-800 dark:text-white mt-2">Negotiation and supplier offers</h2>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">AI inbox with drafts, counter-offers, and follow-up.</p>
            </div>
            <button className="bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2 rounded-full text-xs font-bold flex items-center gap-2 shadow-lg shadow-indigo-200 dark:shadow-indigo-500/20 transition-all">
                <Sparkles size={14} /> Generate AI email
            </button>
        </div>

        <div className="grid lg:grid-cols-[1fr_1.2fr] gap-6 flex-1">
            <div className="bg-white dark:bg-[#13141c] border border-slate-200 dark:border-white/10 rounded-4xl shadow-sm dark:shadow-none overflow-hidden flex flex-col transition-colors">
                <div className="p-5 border-b border-slate-100 dark:border-white/10 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-2xl bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center border border-indigo-100 dark:border-indigo-500/20">
                            <Mail size={18} />
                        </div>
                        <div>
                            <div className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-widest">Inbox</div>
                            <div className="text-sm font-extrabold text-slate-800 dark:text-white">Active threads</div>
                        </div>
                    </div>
                    <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500">{EMAIL_THREADS.length} conversations</span>
                </div>
                <div className="flex-1 overflow-y-auto p-5 space-y-3">
                    {EMAIL_THREADS.map((thread) => (
                        <div key={thread.subject} className="border border-slate-200 dark:border-white/10 rounded-2xl p-4 hover:border-indigo-200 dark:hover:border-indigo-500/50 hover:bg-slate-50 dark:hover:bg-white/5 transition">
                            <div className="flex items-center justify-between mb-2">
                                <div className="text-sm font-bold text-slate-800 dark:text-white">{thread.supplier}</div>
                                <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500 flex items-center gap-1">
                                    <Calendar size={12} /> {thread.time}
                                </span>
                            </div>
                            <div className="text-xs font-semibold text-slate-500 dark:text-slate-400">{thread.subject}</div>
                            <p className="text-xs text-slate-400 dark:text-slate-500 mt-2">{thread.preview}</p>
                            <div className="mt-3 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-100 dark:bg-white/10 text-[10px] font-bold text-slate-500 dark:text-slate-400">
                                {thread.status}
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            <div className="bg-slate-900 dark:bg-[#13141c] border border-slate-800 dark:border-white/10 rounded-4xl shadow-xl shadow-slate-200/20 dark:shadow-none flex flex-col overflow-hidden transition-colors">
                <div className="p-6 border-b border-white/10 flex items-center justify-between">
                    <div>
                        <div className="text-[10px] uppercase tracking-[0.3em] text-slate-400 dark:text-slate-500 font-bold">Email Draft</div>
                        <h3 className="text-lg font-black text-white mt-2">AI draft ready to send</h3>
                    </div>
                    <button className="bg-white text-slate-900 hover:bg-slate-200 px-4 py-2 rounded-full text-xs font-bold flex items-center gap-2 transition-colors">
                        <Send size={14} /> Send
                    </button>
                </div>
                <div className="flex-1 p-6 space-y-4 text-white/90">
                    <div className="bg-white/10 border border-white/10 rounded-2xl p-4">
                        <div className="text-xs uppercase tracking-widest text-slate-300 dark:text-slate-400 font-bold">Goal</div>
                        <p className="text-sm mt-2 text-slate-200 dark:text-slate-300">Secure an additional 4% discount and lead time under 20 days.</p>
                    </div>
                    <div className="bg-white/10 border border-white/10 rounded-2xl p-4 space-y-3">
                        <div className="text-xs uppercase tracking-widest text-slate-300 dark:text-slate-400 font-bold">Message</div>
                        <div className="text-sm leading-relaxed text-slate-200 dark:text-slate-300">
                            Hello, thanks for your proposal. After multi-supplier comparison, we can confirm an immediate
                            pre-order if an extra 4% discount is applied and the lead time is reduced to 18-20 days.
                            We can also consider a quarterly commitment to secure volume.
                        </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                        <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-2xl p-4">
                            <div className="text-xs uppercase tracking-widest text-emerald-200 dark:text-emerald-400 font-bold">Impact</div>
                            <div className="text-2xl font-black text-emerald-200 dark:text-emerald-400 mt-2">-EUR 84k</div>
                            <div className="text-xs text-emerald-200/70 dark:text-emerald-400/70 mt-1">Estimated savings</div>
                        </div>
                        <div className="bg-indigo-500/10 border border-indigo-500/30 rounded-2xl p-4">
                            <div className="text-xs uppercase tracking-widest text-indigo-200 dark:text-indigo-400 font-bold">Status</div>
                            <div className="flex items-center gap-2 mt-2 text-indigo-100 dark:text-indigo-300 text-sm font-semibold">
                                <Check size={16} /> AI approved
                            </div>
                            <div className="text-xs text-indigo-200/70 dark:text-indigo-400/70 mt-1">Ready to send</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
);
