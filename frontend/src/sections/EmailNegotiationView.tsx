"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
    Mail, Send, Sparkles, RefreshCw, Check, X, Clock,
    ChevronRight, AlertCircle, CheckCircle2, XCircle,
    MessageSquare, User, Building2, Loader2, Play, Pause, Phone
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:5000";

// Types
interface EmailRecord {
    message_id: string;
    direction: "outbound" | "inbound";
    subject: string;
    body: string;
    timestamp: string;
    parsed_offer?: {
        price?: number;
        currency?: string;
        incoterm?: string;
        lead_time_days?: number;
        warranty_months?: number;
        payment_terms?: string;
    };
}

interface NegotiationThread {
    thread_id: string;
    supplier_name: string;
    supplier_email: string;
    machine_name: string;
    machine_type: string;
    quantity_needed: number;
    initial_price_estimate: string;
    status: "pending" | "negotiating" | "accepted" | "rejected" | "closed" | "initial_sent";
    emails: EmailRecord[];
    created_at: string;
    updated_at: string;
    rounds_completed: number;
    current_offer?: any;
    best_offer?: any;
}

interface Supplier {
    supplier_name: string;
    email_address: string;
    price_estimate: string;
    price_type: string;
    region: string;
    website?: string;
    phone_number?: string;
}

interface MachineEnriched {
    machine_input: {
        nom_machine: string;
        type: string;
        quantite_necessaire: number;
    };
    suppliers: Supplier[];
}

// Status badge component
const StatusBadge = ({ status }: { status: string }) => {
    const config: Record<string, { bg: string; text: string; icon: React.ReactNode }> = {
        pending: { bg: "bg-amber-50 dark:bg-amber-500/10 border-amber-200 dark:border-amber-500/20", text: "text-amber-700 dark:text-amber-400", icon: <Clock size={12} /> },
        negotiating: { bg: "bg-blue-50 dark:bg-blue-500/10 border-blue-200 dark:border-blue-500/20", text: "text-blue-700 dark:text-blue-400", icon: <MessageSquare size={12} /> },
        accepted: { bg: "bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/20", text: "text-emerald-700 dark:text-emerald-400", icon: <CheckCircle2 size={12} /> },
        rejected: { bg: "bg-red-50 dark:bg-red-500/10 border-red-200 dark:border-red-500/20", text: "text-red-700 dark:text-red-400", icon: <XCircle size={12} /> },
        closed: { bg: "bg-slate-50 dark:bg-slate-500/10 border-slate-200 dark:border-slate-500/20", text: "text-slate-700 dark:text-slate-400", icon: <X size={12} /> },
    };
    const c = config[status] || config.pending;
    return (
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border ${c.bg} ${c.text}`}>
            {c.icon}
            {status}
        </span>
    );
};

// Email thread card
const ThreadCard = ({
    thread,
    isSelected,
    onClick
}: {
    thread: NegotiationThread;
    isSelected: boolean;
    onClick: () => void;
}) => {
    const lastEmail = thread.emails[thread.emails.length - 1];
    const timeAgo = lastEmail ? new Date(lastEmail.timestamp).toLocaleString() : "No emails";

    return (
        <motion.div
            onClick={onClick}
            className={`p-4 border-b border-slate-100 dark:border-white/5 cursor-pointer transition-all ${isSelected
                ? "bg-indigo-50/50 dark:bg-indigo-500/10 border-l-4 border-l-indigo-500 dark:border-l-indigo-400"
                : "hover:bg-slate-50 dark:hover:bg-white/5"
                }`}
            whileHover={{ x: 2 }}
        >
            <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                        <Building2 size={14} className="text-slate-400 dark:text-slate-500" />
                        <span className="font-bold text-slate-800 dark:text-white text-sm truncate">{thread.supplier_name}</span>
                    </div>
                    <p className="text-xs text-slate-600 dark:text-slate-300 font-medium truncate">{thread.machine_name}</p>
                    <p className="text-[11px] text-slate-400 dark:text-slate-500 mt-1 truncate">
                        {lastEmail?.subject || "Awaiting first email..."}
                    </p>
                </div>
                <div className="flex flex-col items-end gap-2">
                    <StatusBadge status={thread.status} />
                    <span className="text-[10px] text-slate-400 dark:text-slate-500">{timeAgo}</span>
                </div>
            </div>
            {thread.current_offer?.price && (
                <div className="mt-2 pt-2 border-t border-slate-100 dark:border-white/5">
                    <span className="text-xs font-bold text-emerald-600 dark:text-emerald-400">
                        Current: {thread.current_offer.price} {thread.current_offer.currency}
                    </span>
                </div>
            )}
        </motion.div>
    );
};

// Email viewer
const EmailViewer = ({ thread, onAction, onCallSupplier }: {
    thread: NegotiationThread;
    onAction: (action: "negotiate" | "accept" | "reject") => void;
    onCallSupplier: (threadId: string) => void;
}) => {
    const [actionLoading, setActionLoading] = useState<string | null>(null);

    const handleAction = async (action: "negotiate" | "accept" | "reject") => {
        setActionLoading(action);
        await onAction(action);
        setActionLoading(null);
    };

    // Only allow calls for pending/negotiating/initial_sent threads (not accepted or rejected)
    const canCall = thread.status === "negotiating" || thread.status === "pending" || thread.status === "initial_sent";

    return (
        <div className="h-full flex flex-col bg-white dark:bg-[#13141c]">
            {/* Header */}
            <div className="p-5 border-b border-slate-100 dark:border-white/10 bg-gradient-to-r from-slate-50 to-white dark:from-white/5 dark:to-transparent">
                <div className="flex items-center justify-between">
                    <div>
                        <h3 className="text-lg font-bold text-slate-800 dark:text-white">{thread.supplier_name}</h3>
                        <p className="text-sm text-slate-500 dark:text-slate-400">{thread.supplier_email}</p>
                    </div>
                    <div className="flex items-center gap-3">
                        {canCall && (
                            <button
                                onClick={() => onCallSupplier(thread.thread_id)}
                                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-full text-xs font-bold flex items-center gap-2 transition-colors shadow-lg shadow-emerald-200 dark:shadow-none"
                                title="Open voice call in new tab"
                            >
                                <Phone size={14} />
                                Call Supplier
                            </button>
                        )}
                        <StatusBadge status={thread.status} />
                    </div>
                </div>
                <div className="mt-3 flex flex-wrap gap-4 text-xs">
                    <span className="text-slate-600 dark:text-slate-400">
                        <strong className="text-slate-800 dark:text-slate-200">Machine:</strong> {thread.machine_name}
                    </span>
                    <span className="text-slate-600 dark:text-slate-400">
                        <strong className="text-slate-800 dark:text-slate-200">Qty:</strong> {thread.quantity_needed}
                    </span>
                    <span className="text-slate-600 dark:text-slate-400">
                        <strong className="text-slate-800 dark:text-slate-200">Initial:</strong> {thread.initial_price_estimate}
                    </span>
                    <span className="text-slate-600 dark:text-slate-400">
                        <strong className="text-slate-800 dark:text-slate-200">Rounds:</strong> {thread.rounds_completed}
                    </span>
                </div>
            </div>

            {/* Email thread */}
            <div className="flex-1 overflow-y-auto p-5 space-y-4 bg-slate-50/30 dark:bg-[#0b0c10]/30 scrollbar-thin scrollbar-thumb-slate-200 dark:scrollbar-thumb-slate-700">
                <AnimatePresence>
                    {thread.emails.map((email, idx) => (
                        <motion.div
                            key={email.message_id || idx}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className={`flex ${email.direction === "outbound" ? "justify-end" : "justify-start"}`}
                        >
                            <div
                                className={`max-w-[80%] rounded-2xl p-4 shadow-sm ${email.direction === "outbound"
                                    ? "bg-indigo-600 dark:bg-indigo-600 text-white rounded-br-sm"
                                    : "bg-white dark:bg-[#1a1c25] border border-slate-200 dark:border-white/10 rounded-bl-sm"
                                    }`}
                            >
                                <div className="flex items-center gap-2 mb-2">
                                    {email.direction === "outbound" ? (
                                        <User size={14} className="text-indigo-200" />
                                    ) : (
                                        <Building2 size={14} className="text-slate-400 dark:text-slate-500" />
                                    )}
                                    <span className={`text-[10px] font-bold ${email.direction === "outbound" ? "text-indigo-200" : "text-slate-400 dark:text-slate-500"
                                        }`}>
                                        {email.direction === "outbound" ? "You" : thread.supplier_name}
                                    </span>
                                    <span className={`text-[10px] ${email.direction === "outbound" ? "text-indigo-300" : "text-slate-400 dark:text-slate-500"
                                        }`}>
                                        {new Date(email.timestamp).toLocaleString()}
                                    </span>
                                </div>
                                <p className={`text-xs font-semibold mb-2 ${email.direction === "outbound" ? "text-white" : "text-slate-700 dark:text-white"
                                    }`}>
                                    {email.subject}
                                </p>
                                <p className={`text-sm whitespace-pre-wrap ${email.direction === "outbound" ? "text-indigo-100" : "text-slate-600 dark:text-slate-300"
                                    }`}>
                                    {email.body}
                                </p>
                                {email.parsed_offer && (
                                    <div className={`mt-3 pt-3 border-t ${email.direction === "outbound" ? "border-indigo-500" : "border-slate-200 dark:border-white/10"
                                        }`}>
                                        <p className={`text-[10px] font-bold mb-1 ${email.direction === "outbound" ? "text-indigo-200" : "text-slate-500 dark:text-slate-400"
                                            }`}>
                                            PARSED OFFER
                                        </p>
                                        <div className="flex flex-wrap gap-2">
                                            {email.parsed_offer.price && (
                                                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${email.direction === "outbound" ? "bg-indigo-500 text-white" : "bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400"
                                                    }`}>
                                                    {email.parsed_offer.price} {email.parsed_offer.currency}
                                                </span>
                                            )}
                                            {email.parsed_offer.incoterm && (
                                                <span className={`px-2 py-0.5 rounded text-[10px] ${email.direction === "outbound" ? "bg-indigo-500 text-white" : "bg-slate-100 dark:bg-white/10 text-slate-600 dark:text-slate-300"
                                                    }`}>
                                                    {email.parsed_offer.incoterm}
                                                </span>
                                            )}
                                            {email.parsed_offer.lead_time_days && (
                                                <span className={`px-2 py-0.5 rounded text-[10px] ${email.direction === "outbound" ? "bg-indigo-500 text-white" : "bg-slate-100 dark:bg-white/10 text-slate-600 dark:text-slate-300"
                                                    }`}>
                                                    {email.parsed_offer.lead_time_days} days
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </motion.div>
                    ))}
                </AnimatePresence>

                {thread.emails.length === 0 && (
                    <div className="h-full flex items-center justify-center">
                        <div className="text-center">
                            <Mail size={48} className="mx-auto text-slate-300 dark:text-slate-600 mb-3" />
                            <p className="text-slate-500 dark:text-slate-400 text-sm">No emails yet</p>
                            <p className="text-slate-400 dark:text-slate-500 text-xs">First RFQ email will be sent automatically</p>
                        </div>
                    </div>
                )}
            </div>

            {/* Actions */}
            {thread.status === "negotiating" && (
                <div className="p-4 border-t border-slate-200 dark:border-white/10 bg-white dark:bg-[#13141c]">
                    <div className="flex items-center gap-3">
                        <button
                            onClick={() => handleAction("negotiate")}
                            disabled={actionLoading !== null}
                            className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2.5 rounded-xl text-xs font-bold flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
                        >
                            {actionLoading === "negotiate" ? (
                                <Loader2 size={14} className="animate-spin" />
                            ) : (
                                <Sparkles size={14} />
                            )}
                            Counter-offer AI
                        </button>
                        <button
                            onClick={() => handleAction("accept")}
                            disabled={actionLoading !== null}
                            className="px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold flex items-center gap-2 transition-colors disabled:opacity-50"
                        >
                            {actionLoading === "accept" ? (
                                <Loader2 size={14} className="animate-spin" />
                            ) : (
                                <Check size={14} />
                            )}
                            Accept
                        </button>
                        <button
                            onClick={() => handleAction("reject")}
                            disabled={actionLoading !== null}
                            className="px-4 py-2.5 bg-red-600 hover:bg-red-700 text-white rounded-xl text-xs font-bold flex items-center gap-2 transition-colors disabled:opacity-50"
                        >
                            {actionLoading === "reject" ? (
                                <Loader2 size={14} className="animate-spin" />
                            ) : (
                                <X size={14} />
                            )}
                            Reject
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

// Main component
export const EmailNegotiationView = ({
    module4Data,
    loading: parentLoading
}: {
    module4Data: { machines_enriched: MachineEnriched[] } | null;
    loading: boolean;
}) => {
    const [threads, setThreads] = useState<NegotiationThread[]>([]);
    const [selectedThreadId, setSelectedThreadId] = useState<string | null>(null);
    const [isStarting, setIsStarting] = useState(false);
    const [isPolling, setIsPolling] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const pollingRef = useRef<NodeJS.Timeout | null>(null);
    const initializationDone = useRef(false);  // Tracks if we've done initial setup

    const selectedThread = threads.find(t => t.thread_id === selectedThreadId);

    // Fetch existing threads
    const fetchThreads = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/api/module5/negotiations/list`, { method: "POST" });
            if (res.ok) {
                const data = await res.json();
                setThreads(data.threads || []);
                if (data.threads?.length > 0 && !selectedThreadId) {
                    setSelectedThreadId(data.threads[0].thread_id);
                }
            }
        } catch (err) {
            console.error("Failed to fetch threads:", err);
        }
    }, [selectedThreadId]);

    // Start negotiations with all suppliers from module4
    const startNegotiations = useCallback(async () => {
        if (!module4Data?.machines_enriched || isStarting) return;

        setIsStarting(true);
        setError(null);

        try {
            // Build suppliers list from module4 data
            // Email override is handled by backend via TEST_RECIPIENT_EMAIL env variable
            const suppliers = module4Data.machines_enriched.flatMap(machine =>
                machine.suppliers.map(supplier => ({
                    machine_name: machine.machine_input.nom_machine,
                    machine_type: machine.machine_input.type,
                    quantity_needed: machine.machine_input.quantite_necessaire,
                    supplier_name: supplier.supplier_name,
                    email_address: supplier.email_address || "", // Backend will override if TEST_RECIPIENT_EMAIL is set
                    price_estimate: supplier.price_estimate,
                    price_type: supplier.price_type,
                    region: supplier.region,
                    website: supplier.website || "",
                    phone_number: supplier.phone_number || ""
                }))
            );

            const res = await fetch(`${API_BASE}/api/module5/negotiations/start`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    suppliers,
                    send_emails: true,
                    buyer_email: "blib645@gmail.com",
                    buyer_company: "SARL ALLO MAISON"
                })
            });

            const data = await res.json();
            if (res.ok) {
                setThreads(data.threads || []);
                if (data.threads?.length > 0) {
                    setSelectedThreadId(data.threads[0].thread_id);
                }
            } else {
                setError(data.error || "Failed to start negotiations");
            }
        } catch (err) {
            setError("Network error starting negotiations");
            console.error(err);
        } finally {
            setIsStarting(false);
        }
    }, [module4Data, isStarting]);

    // Check for replies
    const checkReplies = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/api/module5/negotiations/check-replies`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({}) // Credentials from backend env
            });

            if (res.ok) {
                const data = await res.json();
                if (data.updated_threads?.length > 0) {
                    await fetchThreads();
                }
            }
        } catch (err) {
            console.error("Failed to check replies:", err);
        }
    }, [fetchThreads]);

    // Handle thread actions
    const handleThreadAction = useCallback(async (action: "negotiate" | "accept" | "reject") => {
        if (!selectedThreadId) return;

        const endpoint = action === "negotiate"
            ? `${API_BASE}/api/module5/negotiations/${selectedThreadId}/negotiate`
            : action === "accept"
                ? `${API_BASE}/api/module5/negotiations/${selectedThreadId}/accept`
                : `${API_BASE}/api/module5/negotiations/${selectedThreadId}/reject`;

        try {
            const body: any = {};
            if (action === "negotiate") {
                body.buyer_email = "blib645@gmail.com"; // Credentials from backend env
            }

            const res = await fetch(endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body)
            });

            if (res.ok) {
                await fetchThreads();
            }
        } catch (err) {
            console.error(`Failed to ${action}:`, err);
        }
    }, [selectedThreadId, fetchThreads]);

    // Handle call supplier - opens voice call in new tab
    const handleCallSupplier = useCallback((threadId: string) => {
        const voiceCallUrl = `/voice-call?session=${threadId}`;
        window.open(voiceCallUrl, '_blank', 'noopener,noreferrer');
    }, []);

    // Toggle polling
    const togglePolling = useCallback(() => {
        if (isPolling) {
            if (pollingRef.current) {
                clearInterval(pollingRef.current);
                pollingRef.current = null;
            }
            setIsPolling(false);
        } else {
            checkReplies();
            pollingRef.current = setInterval(checkReplies, 30000); // Check every 30 seconds
            setIsPolling(true);
        }
    }, [isPolling, checkReplies]);

    // Auto-start negotiations when module4Data is available (runs ONCE)
    useEffect(() => {
        if (initializationDone.current || !module4Data?.machines_enriched || parentLoading) {
            return;
        }
        
        initializationDone.current = true;
        
        // First fetch existing threads, then decide if we need to start negotiations
        const initialize = async () => {
            try {
                const res = await fetch(`${API_BASE}/api/module5/negotiations/list`, { method: "POST" });
                if (res.ok) {
                    const data = await res.json();
                    const existingThreads = data.threads || [];
                    setThreads(existingThreads);
                    
                    if (existingThreads.length > 0) {
                        // Threads exist, just select the first one
                        setSelectedThreadId(existingThreads[0].thread_id);
                    } else {
                        // No threads exist, start negotiations
                        startNegotiations();
                    }
                }
            } catch (err) {
                console.error("Failed to initialize:", err);
            }
        };
        
        initialize();
    }, [module4Data, parentLoading]); // Intentionally not including startNegotiations to avoid re-runs

    // Start polling when threads exist
    useEffect(() => {
        if (threads.length > 0 && !isPolling) {
            togglePolling();
        }

        return () => {
            if (pollingRef.current) {
                clearInterval(pollingRef.current);
            }
        };
    }, [threads.length]);

    // Loading state
    if (parentLoading || isStarting) {
        return (
            <div className="h-full flex items-center justify-center bg-slate-50 dark:bg-[#0b0c10] transition-colors">
                <div className="text-center">
                    <Loader2 size={48} className="mx-auto text-indigo-600 dark:text-indigo-400 animate-spin mb-4" />
                    <h3 className="text-lg font-bold text-slate-800 dark:text-white">
                        {isStarting ? "Starting Negotiations..." : "Loading supplier data..."}
                    </h3>
                    <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                        {isStarting ? "Sending initial RFQ emails to suppliers" : "Please wait while we prepare your data"}
                    </p>
                </div>
            </div>
        );
    }

    // No module4 data
    if (!module4Data?.machines_enriched) {
        return (
            <div className="h-full flex items-center justify-center bg-slate-50 dark:bg-[#0b0c10] transition-colors">
                <div className="text-center max-w-md">
                    <AlertCircle size={48} className="mx-auto text-amber-500 mb-4" />
                    <h3 className="text-lg font-bold text-slate-800 dark:text-white">No Supplier Data</h3>
                    <p className="text-sm text-slate-500 dark:text-slate-400 mt-2">
                        Complete the Sourcing module first to get supplier information for negotiations.
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="h-full p-6 flex flex-col gap-6 bg-slate-50 dark:bg-[#0b0c10] transition-colors">
            {/* Header */}
            <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                    <div className="text-[10px] font-bold uppercase tracking-[0.3em] text-indigo-500">
                        AI Email Negotiations
                    </div>
                    <h2 className="text-2xl font-black text-slate-800 dark:text-white mt-2">
                        Supplier Negotiations
                    </h2>
                    <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                        Automated RFQ and counter-offer negotiations with AI assistance
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    <button
                        onClick={togglePolling}
                        className={`px-4 py-2 rounded-full text-xs font-bold flex items-center gap-2 transition-colors ${isPolling
                            ? "bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/30"
                            : "bg-white dark:bg-white/10 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-white/10 hover:bg-slate-50 dark:hover:bg-white/20"
                            }`}
                    >
                        {isPolling ? <Pause size={14} /> : <Play size={14} />}
                        {isPolling ? "Polling Active" : "Start Polling"}
                    </button>
                    <button
                        onClick={checkReplies}
                        className="px-4 py-2 bg-white dark:bg-white/10 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-white/10 rounded-full text-xs font-bold flex items-center gap-2 hover:bg-slate-50 dark:hover:bg-white/20 transition-colors"
                    >
                        <RefreshCw size={14} />
                        Check Inbox
                    </button>
                </div>
            </div>

            {/* Error banner */}
            {error && (
                <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 rounded-xl p-4 flex items-center gap-3"
                >
                    <AlertCircle size={20} className="text-red-500" />
                    <span className="text-sm text-red-700 dark:text-red-400">{error}</span>
                    <button onClick={() => setError(null)} className="ml-auto text-red-400 hover:text-red-600">
                        <X size={16} />
                    </button>
                </motion.div>
            )}

            {/* Main content */}
            <div className="grid lg:grid-cols-[350px_1fr] gap-6 flex-1 min-h-0">
                {/* Thread list */}
                <div className="bg-white dark:bg-[#13141c] border border-slate-200 dark:border-white/10 rounded-3xl shadow-sm dark:shadow-none overflow-hidden flex flex-col transition-colors">
                    <div className="p-5 border-b border-slate-100 dark:border-white/10 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-2xl bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center border border-indigo-100 dark:border-indigo-500/20">
                                <Mail size={18} />
                            </div>
                            <div>
                                <div className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-widest">
                                    Negotiations
                                </div>
                                <div className="text-sm font-extrabold text-slate-800 dark:text-white">
                                    {threads.length} active threads
                                </div>
                            </div>
                        </div>
                        {isPolling && (
                            <div className="flex items-center gap-1.5">
                                <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
                                <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-medium">Live</span>
                            </div>
                        )}
                    </div>
                    <div className="flex-1 overflow-y-auto">
                        {threads.length === 0 ? (
                            <div className="h-full flex items-center justify-center p-6">
                                <div className="text-center">
                                    <Mail size={32} className="mx-auto text-slate-300 dark:text-slate-600 mb-2" />
                                    <p className="text-sm text-slate-500 dark:text-slate-400">No negotiations yet</p>
                                    <p className="text-xs text-slate-400 dark:text-slate-500">Starting automatically...</p>
                                </div>
                            </div>
                        ) : (
                            threads.map(thread => (
                                <ThreadCard
                                    key={thread.thread_id}
                                    thread={thread}
                                    isSelected={thread.thread_id === selectedThreadId}
                                    onClick={() => setSelectedThreadId(thread.thread_id)}
                                />
                            ))
                        )}
                    </div>
                </div>

                {/* Email viewer */}
                <div className="bg-white dark:bg-[#13141c] border border-slate-200 dark:border-white/10 rounded-3xl shadow-sm dark:shadow-none overflow-hidden transition-colors">
                    {selectedThread ? (
                        <EmailViewer thread={selectedThread} onAction={handleThreadAction} onCallSupplier={handleCallSupplier} />
                    ) : (
                        <div className="h-full flex items-center justify-center text-slate-300 dark:text-slate-600">
                            <div className="text-center">
                                <ChevronRight size={48} className="mx-auto mb-3" />
                                <p className="text-slate-500 dark:text-slate-400 text-sm">Select a thread to view</p>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Summary stats */}
            <div className="grid grid-cols-4 gap-4">
                {[
                    { label: "Total Threads", value: threads.length, color: "text-slate-700 dark:text-white" },
                    { label: "Negotiating", value: threads.filter(t => t.status === "negotiating").length, color: "text-blue-600 dark:text-blue-400" },
                    { label: "Accepted", value: threads.filter(t => t.status === "accepted").length, color: "text-emerald-600 dark:text-emerald-400" },
                    { label: "Pending", value: threads.filter(t => t.status === "pending").length, color: "text-amber-600 dark:text-amber-400" }
                ].map((stat, idx) => (
                    <div key={idx} className="bg-white dark:bg-[#13141c] border border-slate-200 dark:border-white/10 rounded-2xl p-4 text-center transition-colors">
                        <p className={`text-2xl font-black ${stat.color}`}>{stat.value}</p>
                        <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">{stat.label}</p>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default EmailNegotiationView;
