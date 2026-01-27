"use client";

import React, { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
    Phone, Send, CheckCircle2, XCircle, Clock, Link2,
    Building2, Loader2, AlertCircle, ExternalLink,
    DollarSign, Percent, MessageSquare, Play
} from "lucide-react";
import { loadPipelineSettings } from "@/utils/pipelineSettings";

const API_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "";

// Types
interface Negotiation {
    id: string;
    project_id: string;
    supplier_name: string;
    supplier_email: string;
    supplier_phone?: string;
    supplier_website?: string;
    supplier_region?: string;
    machine_name: string;
    machine_type?: string;
    quantity: number;
    initial_price_estimate?: number;
    final_price?: number;
    currency: string;
    discount_achieved?: number;
    total_value?: number;
    status: "pending" | "link_sent" | "in_progress" | "completed" | "accepted" | "rejected" | "expired";
    negotiation_rounds?: number;
    link_token?: string;
    link_sent_at?: string;
    link_expires_at?: string;
    voice_call_completed_at?: string;
    voice_call_transcript?: Array<{ role: string; text: string }>;
    rounds_history?: Array<{ round: number; ai_offer: number; supplier_price?: number }>;
    buyer_company: string;
    buyer_email?: string;
    buyer_contact_name?: string;
    emails_sent?: Array<{ type: string; sent_at: string; recipient: string }>;
    created_at: string;
    updated_at: string;
}

interface NegotiationsSummary {
    total_negotiations: number;
    pending_count: number;
    link_sent_count: number;
    in_progress_count: number;
    completed_count: number;
    rejected_count: number;
    total_accepted_value?: number;
    avg_discount?: number;
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
    const config: Record<string, { bg: string; text: string; icon: React.ReactNode; label: string }> = {
        pending: {
            bg: "bg-amber-50 dark:bg-amber-500/10 border-amber-200 dark:border-amber-500/20",
            text: "text-amber-700 dark:text-amber-400",
            icon: <Clock size={12} />,
            label: "Pending"
        },
        link_sent: {
            bg: "bg-blue-50 dark:bg-blue-500/10 border-blue-200 dark:border-blue-500/20",
            text: "text-blue-700 dark:text-blue-400",
            icon: <Link2 size={12} />,
            label: "Link Sent"
        },
        in_progress: {
            bg: "bg-purple-50 dark:bg-purple-500/10 border-purple-200 dark:border-purple-500/20",
            text: "text-purple-700 dark:text-purple-400",
            icon: <Phone size={12} />,
            label: "In Call"
        },
        completed: {
            bg: "bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/20",
            text: "text-emerald-700 dark:text-emerald-400",
            icon: <CheckCircle2 size={12} />,
            label: "Completed"
        },
        accepted: {
            bg: "bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/20",
            text: "text-emerald-700 dark:text-emerald-400",
            icon: <CheckCircle2 size={12} />,
            label: "Accepted"
        },
        rejected: {
            bg: "bg-red-50 dark:bg-red-500/10 border-red-200 dark:border-red-500/20",
            text: "text-red-700 dark:text-red-400",
            icon: <XCircle size={12} />,
            label: "Rejected"
        },
        expired: {
            bg: "bg-slate-50 dark:bg-slate-500/10 border-slate-200 dark:border-slate-500/20",
            text: "text-slate-700 dark:text-slate-400",
            icon: <Clock size={12} />,
            label: "Expired"
        },
    };
    const c = config[status] || config.pending;
    return (
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border ${c.bg} ${c.text}`}>
            {c.icon}
            {c.label}
        </span>
    );
};

// Negotiation card
const NegotiationCard = ({
    negotiation,
    isSelected,
    onClick
}: {
    negotiation: Negotiation;
    isSelected: boolean;
    onClick: () => void;
}) => {
    const timeAgo = negotiation.updated_at
        ? new Date(negotiation.updated_at).toLocaleString()
        : new Date(negotiation.created_at).toLocaleString();

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
                        <span className="font-bold text-slate-800 dark:text-white text-sm truncate">
                            {negotiation.supplier_name}
                        </span>
                    </div>
                    <p className="text-xs text-slate-600 dark:text-slate-300 font-medium truncate">
                        {negotiation.machine_name} × {negotiation.quantity}
                    </p>
                    <p className="text-[11px] text-slate-400 dark:text-slate-500 mt-1 truncate">
                        {negotiation.supplier_email || "No email"}
                    </p>
                </div>
                <div className="flex flex-col items-end gap-2">
                    <StatusBadge status={negotiation.status} />
                    <span className="text-[10px] text-slate-400 dark:text-slate-500">{timeAgo}</span>
                </div>
            </div>
            {negotiation.final_price && (
                <div className="mt-2 pt-2 border-t border-slate-100 dark:border-white/5 flex items-center justify-between">
                    <span className="text-xs font-bold text-emerald-600 dark:text-emerald-400">
                        Final: {negotiation.final_price.toLocaleString()} {negotiation.currency}
                    </span>
                    {negotiation.discount_achieved && (
                        <span className="text-xs text-emerald-600 dark:text-emerald-400">
                            -{negotiation.discount_achieved}%
                        </span>
                    )}
                </div>
            )}
            {!negotiation.final_price && negotiation.initial_price_estimate && (
                <div className="mt-2 pt-2 border-t border-slate-100 dark:border-white/5">
                    <span className="text-xs text-slate-500 dark:text-slate-400">
                        Est: {negotiation.initial_price_estimate.toLocaleString()} {negotiation.currency}
                    </span>
                </div>
            )}
        </motion.div>
    );
};

// Negotiation detail panel
const NegotiationDetail = ({
    negotiation,
    onSendLink,
    onOpenCall,
    linkSending
}: {
    negotiation: Negotiation;
    onSendLink: (id: string) => void;
    onOpenCall: (token: string) => void;
    linkSending: boolean;
}) => {
    const canSendLink = negotiation.status === "pending" && negotiation.supplier_email;
    const canResendLink = negotiation.status === "link_sent" && negotiation.supplier_email;
    const isCompleted = ["completed", "accepted", "rejected"].includes(negotiation.status);

    return (
        <div className="h-full flex flex-col bg-white dark:bg-[#13141c]">
            {/* Header */}
            <div className="p-5 border-b border-slate-100 dark:border-white/10 bg-gradient-to-r from-slate-50 to-white dark:from-white/5 dark:to-transparent">
                <div className="flex items-center justify-between">
                    <div>
                        <h3 className="text-lg font-bold text-slate-800 dark:text-white">
                            {negotiation.supplier_name}
                        </h3>
                        <p className="text-sm text-slate-500 dark:text-slate-400">
                            {negotiation.supplier_email || "No email address"}
                        </p>
                    </div>
                    <StatusBadge status={negotiation.status} />
                </div>
                <div className="mt-3 flex flex-wrap gap-4 text-xs">
                    <span className="text-slate-600 dark:text-slate-400">
                        <strong className="text-slate-800 dark:text-slate-200">Machine:</strong> {negotiation.machine_name}
                    </span>
                    <span className="text-slate-600 dark:text-slate-400">
                        <strong className="text-slate-800 dark:text-slate-200">Qty:</strong> {negotiation.quantity}
                    </span>
                    {negotiation.initial_price_estimate && (
                        <span className="text-slate-600 dark:text-slate-400">
                            <strong className="text-slate-800 dark:text-slate-200">Initial Est:</strong>{" "}
                            {negotiation.initial_price_estimate.toLocaleString()} {negotiation.currency}
                        </span>
                    )}
                    {negotiation.supplier_region && (
                        <span className="text-slate-600 dark:text-slate-400">
                            <strong className="text-slate-800 dark:text-slate-200">Region:</strong>{" "}
                            {negotiation.supplier_region}
                        </span>
                    )}
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-5 space-y-6">
                {/* Actions */}
                {!isCompleted && (
                    <div className="bg-slate-50 dark:bg-white/5 rounded-xl p-4">
                        <h4 className="text-sm font-bold text-slate-700 dark:text-slate-200 mb-3">Actions</h4>
                        <div className="flex flex-wrap gap-3">
                            {canSendLink && (
                                <button
                                    onClick={() => onSendLink(negotiation.id)}
                                    disabled={linkSending}
                                    className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white rounded-xl text-sm font-bold flex items-center gap-2 transition-colors shadow-lg shadow-indigo-200 dark:shadow-none"
                                >
                                    {linkSending ? (
                                        <Loader2 size={16} className="animate-spin" />
                                    ) : (
                                        <Send size={16} />
                                    )}
                                    Send Negotiation Link
                                </button>
                            )}
                            {canResendLink && (
                                <button
                                    onClick={() => onSendLink(negotiation.id)}
                                    disabled={linkSending}
                                    className="px-4 py-2.5 bg-slate-600 hover:bg-slate-700 disabled:bg-slate-400 text-white rounded-xl text-sm font-bold flex items-center gap-2 transition-colors"
                                >
                                    {linkSending ? (
                                        <Loader2 size={16} className="animate-spin" />
                                    ) : (
                                        <Send size={16} />
                                    )}
                                    Resend Link
                                </button>
                            )}
                            {negotiation.link_token && (
                                <button
                                    onClick={() => onOpenCall(negotiation.link_token!)}
                                    className="px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-sm font-bold flex items-center gap-2 transition-colors shadow-lg shadow-emerald-200 dark:shadow-none"
                                >
                                    <ExternalLink size={16} />
                                    Preview Call Page
                                </button>
                            )}
                        </div>
                        {negotiation.link_sent_at && (
                            <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
                                Link sent: {new Date(negotiation.link_sent_at).toLocaleString()}
                                {negotiation.link_expires_at && (
                                    <> · Expires: {new Date(negotiation.link_expires_at).toLocaleString()}</>
                                )}
                            </p>
                        )}
                    </div>
                )}

                {/* Results (for completed negotiations) */}
                {isCompleted && negotiation.final_price && (
                    <div className="bg-gradient-to-br from-emerald-50 to-green-50 dark:from-emerald-500/10 dark:to-green-500/10 rounded-xl p-5 border border-emerald-200 dark:border-emerald-500/20">
                        <h4 className="text-sm font-bold text-emerald-800 dark:text-emerald-300 mb-4 flex items-center gap-2">
                            <CheckCircle2 size={16} />
                            Negotiation Results
                        </h4>
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <p className="text-xs text-emerald-600 dark:text-emerald-400 mb-1">Final Price</p>
                                <p className="text-xl font-black text-emerald-900 dark:text-emerald-200">
                                    {negotiation.final_price.toLocaleString()} {negotiation.currency}
                                </p>
                            </div>
                            {negotiation.discount_achieved && (
                                <div>
                                    <p className="text-xs text-emerald-600 dark:text-emerald-400 mb-1">Discount</p>
                                    <p className="text-xl font-black text-emerald-900 dark:text-emerald-200">
                                        {negotiation.discount_achieved}%
                                    </p>
                                </div>
                            )}
                            {negotiation.total_value && (
                                <div>
                                    <p className="text-xs text-emerald-600 dark:text-emerald-400 mb-1">Total Value</p>
                                    <p className="text-lg font-bold text-emerald-900 dark:text-emerald-200">
                                        {negotiation.total_value.toLocaleString()} {negotiation.currency}
                                    </p>
                                </div>
                            )}
                            {negotiation.negotiation_rounds && (
                                <div>
                                    <p className="text-xs text-emerald-600 dark:text-emerald-400 mb-1">Rounds</p>
                                    <p className="text-lg font-bold text-emerald-900 dark:text-emerald-200">
                                        {negotiation.negotiation_rounds}
                                    </p>
                                </div>
                            )}
                        </div>
                        {negotiation.voice_call_completed_at && (
                            <p className="mt-4 text-xs text-emerald-600 dark:text-emerald-400">
                                Completed: {new Date(negotiation.voice_call_completed_at).toLocaleString()}
                            </p>
                        )}
                    </div>
                )}

                {/* Transcript */}
                {negotiation.voice_call_transcript && negotiation.voice_call_transcript.length > 0 && (
                    <div>
                        <h4 className="text-sm font-bold text-slate-700 dark:text-slate-200 mb-3 flex items-center gap-2">
                            <MessageSquare size={16} />
                            Call Transcript
                        </h4>
                        <div className="space-y-3 max-h-64 overflow-y-auto">
                            {negotiation.voice_call_transcript.map((entry, idx) => (
                                <div
                                    key={idx}
                                    className={`flex ${entry.role === "assistant" ? "justify-start" : "justify-end"}`}
                                >
                                    <div
                                        className={`max-w-[80%] rounded-2xl px-4 py-2 text-sm ${
                                            entry.role === "assistant"
                                                ? "bg-slate-100 dark:bg-white/10 text-slate-800 dark:text-slate-200"
                                                : "bg-indigo-500 text-white"
                                        }`}
                                    >
                                        {entry.text}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Rounds History */}
                {negotiation.rounds_history && negotiation.rounds_history.length > 0 && (
                    <div>
                        <h4 className="text-sm font-bold text-slate-700 dark:text-slate-200 mb-3">
                            Negotiation Rounds
                        </h4>
                        <div className="space-y-2">
                            {negotiation.rounds_history.map((round, idx) => (
                                <div
                                    key={idx}
                                    className="flex items-center justify-between p-3 bg-slate-50 dark:bg-white/5 rounded-lg text-sm"
                                >
                                    <span className="text-slate-600 dark:text-slate-400">Round {round.round}</span>
                                    <div className="flex gap-4">
                                        <span className="text-indigo-600 dark:text-indigo-400">
                                            Our offer: {round.ai_offer?.toLocaleString()} €
                                        </span>
                                        {round.supplier_price && (
                                            <span className="text-amber-600 dark:text-amber-400">
                                                Their price: {round.supplier_price?.toLocaleString()} €
                                            </span>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Emails sent */}
                {negotiation.emails_sent && negotiation.emails_sent.length > 0 && (
                    <div>
                        <h4 className="text-sm font-bold text-slate-700 dark:text-slate-200 mb-3">
                            Emails Sent
                        </h4>
                        <div className="space-y-2">
                            {negotiation.emails_sent.map((email, idx) => (
                                <div
                                    key={idx}
                                    className="flex items-center justify-between p-3 bg-slate-50 dark:bg-white/5 rounded-lg text-xs"
                                >
                                    <span className="text-slate-600 dark:text-slate-400 capitalize">
                                        {email.type.replace("_", " ")}
                                    </span>
                                    <span className="text-slate-500 dark:text-slate-500">
                                        {new Date(email.sent_at).toLocaleString()}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Contact info */}
                <div>
                    <h4 className="text-sm font-bold text-slate-700 dark:text-slate-200 mb-3">
                        Supplier Contact
                    </h4>
                    <div className="space-y-2 text-sm">
                        {negotiation.supplier_email && (
                            <p className="text-slate-600 dark:text-slate-400">
                                <strong>Email:</strong> {negotiation.supplier_email}
                            </p>
                        )}
                        {negotiation.supplier_phone && (
                            <p className="text-slate-600 dark:text-slate-400">
                                <strong>Phone:</strong> {negotiation.supplier_phone}
                            </p>
                        )}
                        {negotiation.supplier_website && (
                            <p className="text-slate-600 dark:text-slate-400">
                                <strong>Website:</strong>{" "}
                                <a
                                    href={negotiation.supplier_website}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-indigo-600 dark:text-indigo-400 hover:underline"
                                >
                                    {negotiation.supplier_website}
                                </a>
                            </p>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

// Summary stats
const SummaryStats = ({ summary }: { summary: NegotiationsSummary | null }) => {
    if (!summary) return null;

    return (
        <div className="grid grid-cols-5 gap-3 p-4 bg-gradient-to-r from-slate-50 to-white dark:from-white/5 dark:to-transparent border-b border-slate-100 dark:border-white/10">
            <div className="text-center">
                <p className="text-2xl font-black text-slate-800 dark:text-white">{summary.total_negotiations}</p>
                <p className="text-[10px] text-slate-500 dark:text-slate-400 uppercase tracking-wider">Total</p>
            </div>
            <div className="text-center">
                <p className="text-2xl font-black text-amber-600 dark:text-amber-400">{summary.pending_count}</p>
                <p className="text-[10px] text-slate-500 dark:text-slate-400 uppercase tracking-wider">Pending</p>
            </div>
            <div className="text-center">
                <p className="text-2xl font-black text-blue-600 dark:text-blue-400">{summary.link_sent_count}</p>
                <p className="text-[10px] text-slate-500 dark:text-slate-400 uppercase tracking-wider">Link Sent</p>
            </div>
            <div className="text-center">
                <p className="text-2xl font-black text-emerald-600 dark:text-emerald-400">{summary.completed_count}</p>
                <p className="text-[10px] text-slate-500 dark:text-slate-400 uppercase tracking-wider">Completed</p>
            </div>
            <div className="text-center">
                <p className="text-2xl font-black text-emerald-600 dark:text-emerald-400">
                    {summary.avg_discount ? `${summary.avg_discount.toFixed(1)}%` : "-"}
                </p>
                <p className="text-[10px] text-slate-500 dark:text-slate-400 uppercase tracking-wider">Avg Discount</p>
            </div>
        </div>
    );
};

// Main component
export const VoiceNegotiationView = ({
    projectId,
    module4Data: rawModule4Data,
    loading: externalLoading
}: {
    projectId: string;
    module4Data?: { machines_enriched?: MachineEnriched[] } | MachineEnriched[] | null;
    loading?: boolean;
}) => {
    // Normalize module4Data - handle both raw array and { machines_enriched: [] } format
    const module4Data: MachineEnriched[] | null = Array.isArray(rawModule4Data)
        ? rawModule4Data
        : rawModule4Data?.machines_enriched || null;
    const [negotiations, setNegotiations] = useState<Negotiation[]>([]);
    const [summary, setSummary] = useState<NegotiationsSummary | null>(null);
    const [selectedId, setSelectedId] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [linkSending, setLinkSending] = useState(false);
    const [sendingAllLinks, setSendingAllLinks] = useState(false);
    const [creating, setCreating] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);

    const selectedNegotiation = negotiations.find(n => n.id === selectedId);
    const pendingCount = negotiations.filter(n => n.status === "pending" && n.supplier_email).length;
    
    // Track if we've already auto-initiated the process
    const [autoInitiated, setAutoInitiated] = useState(false);
    const [autoCreationStatus, setAutoCreationStatus] = useState<string | null>(null);

    // Fetch negotiations
    const fetchNegotiations = useCallback(async () => {
        if (!projectId) return;

        try {
            const res = await fetch(`${API_BASE}/api/module5/v2/negotiations/project/${projectId}`);
            if (res.ok) {
                const data = await res.json();
                setNegotiations(data.negotiations || []);
                setSummary(data.summary || null);
                // Auto-select first if none selected
                if (!selectedId && data.negotiations?.length > 0) {
                    setSelectedId(data.negotiations[0].id);
                }
            }
        } catch (err) {
            console.error("Failed to fetch negotiations:", err);
        } finally {
            setLoading(false);
        }
    }, [projectId, selectedId]);

    useEffect(() => {
        fetchNegotiations();
        // Poll every 30 seconds
        const interval = setInterval(fetchNegotiations, 30000);
        return () => clearInterval(interval);
    }, [fetchNegotiations]);

    // Auto-dismiss success message after 5 seconds
    useEffect(() => {
        if (successMessage) {
            const timer = setTimeout(() => setSuccessMessage(null), 5000);
            return () => clearTimeout(timer);
        }
    }, [successMessage]);

    // AUTO-INITIATION: Create negotiations and send emails automatically when module4 data is available
    useEffect(() => {
        const autoInitiateNegotiations = async () => {
            // Only run once and when we have module4 data, projectId, and no existing negotiations
            if (autoInitiated || !module4Data || !projectId || module4Data.length === 0) return;
            if (externalLoading || loading) return;
            if (negotiations.length > 0) return; // Already have negotiations
            
            setAutoInitiated(true);
            setAutoCreationStatus("Creating negotiations...");
            setCreating(true);
            
            try {
                // Get test recipient email from settings
                const settings = loadPipelineSettings();
                const testRecipientEmail = settings.testRecipientEmail?.trim() || "";
                
                // Step 1: Create negotiations from module 4 data
                let createdCount = 0;
                for (const machine of module4Data) {
                    const suppliers = machine.suppliers || [];
                    if (suppliers.length === 0) continue;

                    const payload = {
                        project_id: projectId,
                        machine_name: machine.machine_input?.nom_machine || "Equipment",
                        machine_type: machine.machine_input?.type,
                        quantity: machine.machine_input?.quantite_necessaire || 1,
                        suppliers: suppliers,
                        buyer_company: "RIBIF Algeria",
                        test_recipient_email: testRecipientEmail, // Pass test email override
                    };

                    console.log("[Module5] Creating negotiations with payload:", payload);

                    const res = await fetch(`${API_BASE}/api/module5/v2/negotiations/bulk-create`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(payload),
                    });

                    if (res.ok) {
                        const data = await res.json();
                        createdCount += data.created_count || 0;
                        console.log("[Module5] Created negotiations:", data);
                    } else {
                        const errData = await res.json();
                        console.error("[Module5] Failed to create negotiations:", errData);
                    }
                }
                
                console.log("[Module5] Total created:", createdCount);
                
                if (createdCount > 0) {
                    // Step 2: Auto-send all negotiation links immediately
                    setAutoCreationStatus(`Sending emails to ${createdCount} suppliers...`);
                    
                    console.log("[Module5] Sending negotiation links for project:", projectId);
                    
                    const sendRes = await fetch(`${API_BASE}/api/module5/v2/negotiations/project/${projectId}/send-all-links`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ test_recipient_email: testRecipientEmail }), // Pass test email override
                    });
                    
                    const sendData = await sendRes.json();
                    console.log("[Module5] Send links response:", sendData);
                    
                    if (sendRes.ok && sendData.sent_count > 0) {
                        setSuccessMessage(`✅ Auto-sent ${sendData.sent_count} negotiation link${sendData.sent_count > 1 ? 's' : ''} to suppliers!`);
                    } else if (sendData.failed_count > 0) {
                        setError(`Some emails failed to send (${sendData.failed_count}): ${JSON.stringify(sendData.failed)}`);
                    } else if (sendData.sent_count === 0) {
                        setError(`No emails sent: ${sendData.message || 'Unknown reason'}`);
                    }
                }
                
                // Refresh to show updated statuses
                const refreshRes = await fetch(`${API_BASE}/api/module5/v2/negotiations/project/${projectId}`);
                if (refreshRes.ok) {
                    const refreshData = await refreshRes.json();
                    setNegotiations(refreshData.negotiations || []);
                    setSummary(refreshData.summary || null);
                    if (refreshData.negotiations?.length > 0) {
                        setSelectedId(refreshData.negotiations[0].id);
                    }
                }
                
            } catch (err: any) {
                console.error("[Module5] Auto-initiation failed:", err);
                setError(err.message || "Failed to auto-initiate negotiations");
            } finally {
                setCreating(false);
                setAutoCreationStatus(null);
                setLoading(false);
            }
        };
        
        autoInitiateNegotiations();
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [module4Data, projectId, autoInitiated, negotiations.length, externalLoading, loading]);

    // Create negotiations from module 4 data
    const createFromModule4 = async () => {
        if (!module4Data || !projectId) return;

        setCreating(true);
        setError(null);

        try {
            // Flatten suppliers from all machines
            for (const machine of module4Data) {
                const suppliers = machine.suppliers || [];
                if (suppliers.length === 0) continue;

                const payload = {
                    project_id: projectId,
                    machine_name: machine.machine_input?.nom_machine || "Equipment",
                    machine_type: machine.machine_input?.type,
                    quantity: machine.machine_input?.quantite_necessaire || 1,
                    suppliers: suppliers,
                    buyer_company: "RIBIF Algeria",
                };

                const res = await fetch(`${API_BASE}/api/module5/v2/negotiations/bulk-create`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                });

                if (!res.ok) {
                    const errData = await res.json();
                    throw new Error(errData.error || "Failed to create negotiations");
                }
            }

            await fetchNegotiations();
        } catch (err: any) {
            setError(err.message || "Failed to create negotiations");
        } finally {
            setCreating(false);
        }
    };

    // Send negotiation link
    const sendNegotiationLink = async (negotiationId: string) => {
        setLinkSending(true);
        setError(null);
        setSuccessMessage(null);

        try {
            // Get test recipient email from settings
            const settings = loadPipelineSettings();
            const testRecipientEmail = settings.testRecipientEmail?.trim() || "";
            
            const res = await fetch(`${API_BASE}/api/module5/v2/negotiations/${negotiationId}/send-link`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ test_recipient_email: testRecipientEmail }),
            });

            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.error || "Failed to send link");
            }

            setSuccessMessage("Negotiation link sent successfully!");
            await fetchNegotiations();
        } catch (err: any) {
            setError(err.message || "Failed to send negotiation link");
        } finally {
            setLinkSending(false);
        }
    };

    // Send all negotiation links
    const sendAllNegotiationLinks = async () => {
        if (!projectId || pendingCount === 0) return;
        
        setSendingAllLinks(true);
        setError(null);
        setSuccessMessage(null);

        try {
            // Get test recipient email from settings
            const settings = loadPipelineSettings();
            const testRecipientEmail = settings.testRecipientEmail?.trim() || "";
            
            const res = await fetch(`${API_BASE}/api/module5/v2/negotiations/project/${projectId}/send-all-links`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ test_recipient_email: testRecipientEmail }),
            });

            const data = await res.json();
            
            if (!res.ok) {
                throw new Error(data.error || "Failed to send links");
            }

            if (data.sent_count > 0) {
                setSuccessMessage(`Successfully sent ${data.sent_count} negotiation link${data.sent_count > 1 ? 's' : ''}!`);
            }
            if (data.failed_count > 0) {
                setError(`Failed to send ${data.failed_count} link${data.failed_count > 1 ? 's' : ''}`);
            }
            
            await fetchNegotiations();
        } catch (err: any) {
            setError(err.message || "Failed to send negotiation links");
        } finally {
            setSendingAllLinks(false);
        }
    };

    // Open call preview
    const openCallPreview = (token: string) => {
        window.open(`/voice-call?token=${token}`, "_blank");
    };

    if (externalLoading || loading || autoCreationStatus) {
        return (
            <div className="h-full flex items-center justify-center bg-white dark:bg-[#13141c]">
                <div className="text-center">
                    <Loader2 size={32} className="mx-auto text-indigo-500 animate-spin mb-3" />
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                        {autoCreationStatus || "Loading negotiations..."}
                    </p>
                    {autoCreationStatus && (
                        <p className="text-xs text-indigo-500 dark:text-indigo-400 mt-2">
                            Automatically setting up supplier negotiations...
                        </p>
                    )}
                </div>
            </div>
        );
    }

    // No negotiations yet - show create option
    if (negotiations.length === 0) {
        return (
            <div className="h-full flex items-center justify-center bg-white dark:bg-[#13141c] p-8">
                <div className="text-center max-w-md">
                    <div className="w-16 h-16 bg-indigo-100 dark:bg-indigo-500/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
                        <Phone size={32} className="text-indigo-600 dark:text-indigo-400" />
                    </div>
                    <h3 className="text-xl font-bold text-slate-800 dark:text-white mb-2">
                        Voice Negotiations
                    </h3>
                    <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
                        Create negotiation sessions for your suppliers. Each supplier will receive a unique link
                        to join a voice call with our AI negotiation agent.
                    </p>

                    {error && (
                        <div className="mb-4 p-3 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 rounded-lg">
                            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
                        </div>
                    )}

                    {module4Data && module4Data.length > 0 ? (
                        <button
                            onClick={createFromModule4}
                            disabled={creating}
                            className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white rounded-xl font-bold flex items-center gap-2 mx-auto transition-colors"
                        >
                            {creating ? (
                                <Loader2 size={18} className="animate-spin" />
                            ) : (
                                <Play size={18} />
                            )}
                            Create Negotiations from Sourcing Data
                        </button>
                    ) : (
                        <div className="p-4 bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20 rounded-xl">
                            <AlertCircle size={20} className="text-amber-600 dark:text-amber-400 mx-auto mb-2" />
                            <p className="text-sm text-amber-700 dark:text-amber-300">
                                No sourcing data available. Complete Module 4 (Sourcing) first to get supplier data.
                            </p>
                        </div>
                    )}
                </div>
            </div>
        );
    }

    return (
        <div className="h-full flex bg-white dark:bg-[#13141c]">
            {/* Sidebar */}
            <div className="w-80 border-r border-slate-100 dark:border-white/10 flex flex-col">
                {/* Summary */}
                <SummaryStats summary={summary} />

                {/* Header with Send All button */}
                <div className="p-4 border-b border-slate-100 dark:border-white/10">
                    <div className="flex items-center justify-between mb-3">
                        <h3 className="font-bold text-slate-800 dark:text-white">Negotiations</h3>
                        {module4Data && module4Data.length > 0 && (
                            <button
                                onClick={createFromModule4}
                                disabled={creating}
                                className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1"
                            >
                                {creating ? <Loader2 size={12} className="animate-spin" /> : "+"} Add More
                            </button>
                        )}
                    </div>
                    
                    {/* Send All Links Button */}
                    {pendingCount > 0 && (
                        <button
                            onClick={sendAllNegotiationLinks}
                            disabled={sendingAllLinks || linkSending}
                            className="w-full px-3 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white text-sm rounded-lg font-medium flex items-center justify-center gap-2 transition-colors"
                        >
                            {sendingAllLinks ? (
                                <Loader2 size={14} className="animate-spin" />
                            ) : (
                                <Send size={14} />
                            )}
                            Send Links to All ({pendingCount} pending)
                        </button>
                    )}
                </div>

                {/* Success banner */}
                {successMessage && (
                    <div className="p-3 bg-emerald-50 dark:bg-emerald-500/10 border-b border-emerald-200 dark:border-emerald-500/20 flex items-center gap-2">
                        <CheckCircle2 size={14} className="text-emerald-600 dark:text-emerald-400" />
                        <p className="text-xs text-emerald-600 dark:text-emerald-400">{successMessage}</p>
                    </div>
                )}

                {/* Error banner */}
                {error && (
                    <div className="p-3 bg-red-50 dark:bg-red-500/10 border-b border-red-200 dark:border-red-500/20">
                        <p className="text-xs text-red-600 dark:text-red-400">{error}</p>
                    </div>
                )}

                {/* List */}
                <div className="flex-1 overflow-y-auto">
                    {negotiations.map(neg => (
                        <NegotiationCard
                            key={neg.id}
                            negotiation={neg}
                            isSelected={neg.id === selectedId}
                            onClick={() => setSelectedId(neg.id)}
                        />
                    ))}
                </div>
            </div>

            {/* Detail panel */}
            <div className="flex-1">
                {selectedNegotiation ? (
                    <NegotiationDetail
                        negotiation={selectedNegotiation}
                        onSendLink={sendNegotiationLink}
                        onOpenCall={openCallPreview}
                        linkSending={linkSending}
                    />
                ) : (
                    <div className="h-full flex items-center justify-center">
                        <p className="text-sm text-slate-400 dark:text-slate-500">
                            Select a negotiation to view details
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default VoiceNegotiationView;
