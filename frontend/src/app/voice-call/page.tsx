"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState, Suspense, useRef } from "react";
import { Phone, PhoneOff, Loader2, CheckCircle2, XCircle, Volume2 } from "lucide-react";
import Vapi from "@vapi-ai/web";

const API_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "";
const VAPI_PUBLIC_KEY = process.env.NEXT_PUBLIC_VAPI_PUBLIC_KEY || "";

// =============================================================================
// TYPES
// =============================================================================

interface NegotiationData {
    machine_input: {
        id: string;
        name: string;
        quantity: number;
    };
    suppliers: Array<{
        supplier_name: string;
        name?: string;
        website: string;
        region: string;
        price_estimate: number;
        email: string;
        phone_number: string;
        relevance_score: number;
    }>;
    // New fields for v2 token-based negotiations
    negotiation_id?: string;
    project_id?: string;
}

interface CompanyConfig {
    name: string;
    agent_name: string;
}

// =============================================================================
// NEGOTIATION ENGINE
// =============================================================================

class NegotiationEngine {
    static MAX_ROUNDS = 5;
    // More gradual increase - buyer raises offer slowly
    static ROUND_FACTORS: Record<number, number> = { 2: 0.25, 3: 0.50, 4: 0.75, 5: 1.0 };

    company: CompanyConfig;
    machine: { id: string; name: string; quantity: number };
    suppliers: Array<{
        id: string;
        name: string;
        email: string;
        phone: string;
        website: string;
        region: string;
        relevance_score: number;
        price_estimate: number;
        currency: string;
    }>;
    currentSupplierIndex: number;
    currentRound: number;
    roundsHistory: Array<{ round: number; ai_offer: number | null; supplier_response?: string | null; supplier_price?: number | null }>;
    sessionActive: boolean;
    p0: number | null;           // Supplier's initial estimate
    anchorPrice: number | null;  // Our starting (lowest) offer
    targetPrice: number | null;  // Our ideal target (10% discount)
    maxPrice: number | null;     // Absolute maximum we're willing to pay
    currentOffer: number | null;
    lastSupplierPrice: number | null;
    finalResult: any;
    walkAwayThreshold: number;   // If supplier won't go below this, we walk away

    constructor(data: NegotiationData, company: CompanyConfig) {
        this.company = company;
        this.machine = {
            id: data.machine_input.id,
            name: data.machine_input.name,
            quantity: data.machine_input.quantity
        };

        this.suppliers = this.parseAndSortSuppliers(data.suppliers);
        this.currentSupplierIndex = 0;
        this.currentRound = 0;
        this.roundsHistory = [];
        this.sessionActive = false;

        this.p0 = null;
        this.anchorPrice = null;
        this.targetPrice = null;
        this.maxPrice = null;
        this.currentOffer = null;
        this.lastSupplierPrice = null;
        this.finalResult = null;
        this.walkAwayThreshold = 0;
    }

    parseAndSortSuppliers(suppliers: NegotiationData["suppliers"]) {
        const mapped = suppliers.map((s, i) => ({
            id: `SUP-${String(i + 1).padStart(3, "0")}`,
            name: s.supplier_name,
            email: s.email,
            phone: s.phone_number,
            website: s.website,
            region: s.region,
            relevance_score: s.relevance_score || 0,
            price_estimate: s.price_estimate,
            currency: "DZD"
        }));
        return mapped.sort((a, b) => b.relevance_score - a.relevance_score);
    }

    calculatePriceBoundaries(p0: number) {
        return {
            anchorPrice: Math.round(p0 * 0.80 * 100) / 100,    // Start at 20% discount
            targetPrice: Math.round(p0 * 0.90 * 100) / 100,    // Target is 10% discount
            maxPrice: Math.round(p0 * 0.97 * 100) / 100,       // Absolute max: only 3% discount (we might walk away)
            walkAwayThreshold: Math.round(p0 * 1.02 * 100) / 100 // If they won't go below 2% ABOVE estimate, walk away
        };
    }

    calculateOfferForRound(round: number) {
        if (round === 1) return this.anchorPrice;
        
        // Calculate offer based on progress through negotiation
        const range = (this.maxPrice || 0) - (this.anchorPrice || 0);
        const factor = NegotiationEngine.ROUND_FACTORS[round] || 1.0;
        
        // Don't exceed max price
        const offer = Math.round(((this.anchorPrice || 0) + range * factor) * 100) / 100;
        return Math.min(offer, this.maxPrice || offer);
    }

    // Calculate a smart counter based on supplier's price
    calculateSmartCounter(supplierPrice: number): number {
        // Meet somewhere between our current offer and their price, leaning toward ours
        const midpoint = (this.currentOffer! + supplierPrice) / 2;
        const ourBias = this.currentOffer! + (midpoint - this.currentOffer!) * 0.6; // 60% toward midpoint
        
        // But never exceed our max
        const capped = Math.min(ourBias, this.maxPrice || ourBias);
        return Math.round(capped * 100) / 100;
    }

    getCurrentSupplier() {
        return this.suppliers[this.currentSupplierIndex] || null;
    }

    initializeNegotiation() {
        const supplier = this.getCurrentSupplier();
        if (!supplier) return { action: "error", message: "No supplier available" };

        this.sessionActive = true;
        this.currentRound = 0;
        this.roundsHistory = [];
        this.lastSupplierPrice = null;

        if (supplier.price_estimate) {
            this.p0 = supplier.price_estimate;
            const bounds = this.calculatePriceBoundaries(this.p0);
            this.anchorPrice = bounds.anchorPrice;
            this.targetPrice = bounds.targetPrice;
            this.maxPrice = bounds.maxPrice;
            this.walkAwayThreshold = bounds.walkAwayThreshold;
            this.currentOffer = this.calculateOfferForRound(1);
        }

        return {
            action: "verify_supplier",
            message: `Hi, this is ${this.company.agent_name} calling from ${this.company.name}. Am I speaking with ${supplier.name}?`,
            awaitingResponse: true
        };
    }

    startNegotiationAfterVerification() {
        const supplier = this.getCurrentSupplier();
        this.currentRound = 1;
        if (!this.currentOffer) this.currentOffer = this.calculateOfferForRound(1);

        this.roundsHistory.push({ round: 1, ai_offer: this.currentOffer, supplier_response: null, supplier_price: null });

        return {
            action: "make_offer",
            round: 1,
            offer: this.currentOffer,
            message: `We're looking to purchase ${this.machine.quantity} units of the ${this.machine.name}. For this volume, we can offer ${this.currentOffer?.toLocaleString()} euros per unit. Does that work for you?`,
            awaitingResponse: true
        };
    }

    processSupplierResponse(responseType: string, supplierPrice: number | null = null) {
        const supplier = this.getCurrentSupplier();
        switch (responseType) {
            case "accept":
                return this.handleAccept(supplier);
            case "reject":
                return this.handleReject(supplier);
            case "counter":
                return this.handleCounter(supplier, supplierPrice);
            default:
                return { action: "clarify", message: "Sorry, could you repeat the price?", awaitingResponse: true };
        }
    }

    handleAccept(supplier: any) {
        this.sessionActive = false;
        this.finalResult = { status: "accepted", final_price: this.currentOffer };
        return {
            action: "accepted",
            result: this.finalResult,
            message: `Excellent! We have a deal at ${this.currentOffer?.toLocaleString()} euros per unit. I'll send over the purchase order shortly. Thank you!`,
            negotiationComplete: true
        };
    }

    handleReject(supplier: any) {
        // If they flat-out reject and we haven't made many offers, try increasing
        if (this.currentRound < NegotiationEngine.MAX_ROUNDS) {
            return this.makeNextOffer(supplier, "I understand. Let me see what I can do.");
        }

        // At max rounds with rejection - genuinely walk away
        this.sessionActive = false;
        this.finalResult = { status: "no_deal", reason: "supplier_rejected" };
        return {
            action: "walk_away",
            result: this.finalResult,
            message: `I understand this doesn't work for you. We'll have to look at other options. Thank you for your time.`,
            negotiationComplete: true
        };
    }

    handleCounter(supplier: any, supplierPrice: number | null) {
        if (supplierPrice === null) {
            return { action: "clarify", message: "Sorry, I didn't catch that number. What price are you thinking?", awaitingResponse: true };
        }

        this.lastSupplierPrice = supplierPrice;
        
        // Update history with supplier's response
        if (this.roundsHistory.length > 0) {
            this.roundsHistory[this.roundsHistory.length - 1].supplier_price = supplierPrice;
            this.roundsHistory[this.roundsHistory.length - 1].supplier_response = "counter";
        }

        // Case 1: Supplier price is at or below our target - ACCEPT immediately
        if (supplierPrice <= (this.targetPrice || 0)) {
            this.currentOffer = supplierPrice;
            return this.handleAccept(supplier);
        }

        // Case 2: Supplier price is within our acceptable range (between target and max)
        if (supplierPrice <= (this.maxPrice || 0)) {
            // Decide: accept or try to negotiate lower?
            // If we're in later rounds, just accept
            if (this.currentRound >= 3) {
                this.currentOffer = supplierPrice;
                return this.handleAccept(supplier);
            }
            // Earlier rounds: try one more counter
            return this.makeSmartCounter(supplier, supplierPrice);
        }

        // Case 3: Supplier price is above our max but below walk-away threshold
        if (supplierPrice <= (this.walkAwayThreshold || 0)) {
            if (this.currentRound < NegotiationEngine.MAX_ROUNDS) {
                return this.makeSmartCounter(supplier, supplierPrice);
            }
            // Last round - make a final offer at our max
            return this.makeFinalOffer(supplier);
        }

        // Case 4: Supplier price is way too high - push back hard or walk away
        if (this.currentRound < 2) {
            // Early round - express concern and make a counter
            return this.makeNextOffer(supplier, `That's quite a bit higher than we budgeted.`);
        }
        
        if (this.currentRound < NegotiationEngine.MAX_ROUNDS) {
            return this.makeSmartCounter(supplier, supplierPrice);
        }

        // We've tried everything - walk away
        this.sessionActive = false;
        this.finalResult = { status: "no_deal", reason: "price_too_high", supplier_final: supplierPrice };
        return {
            action: "walk_away",
            result: this.finalResult,
            message: `I appreciate your time, but ${supplierPrice.toLocaleString()} euros is beyond what we can do. We'll need to explore other options. Thank you.`,
            negotiationComplete: true
        };
    }

    makeSmartCounter(supplier: any, supplierPrice: number) {
        this.currentRound++;
        
        // Calculate a smart counter - meet them partway but stay within our range
        const newOffer = this.calculateSmartCounter(supplierPrice);
        this.currentOffer = newOffer;
        
        this.roundsHistory.push({ round: this.currentRound, ai_offer: this.currentOffer });
        
        const gap = supplierPrice - newOffer;
        let message: string;
        
        if (gap < 500) {
            message = `We're close. How about ${this.currentOffer?.toLocaleString()} euros? That splits the difference.`;
        } else {
            message = `I can move up to ${this.currentOffer?.toLocaleString()} euros. Can you work with that?`;
        }
        
        return {
            action: "counter_offer",
            round: this.currentRound,
            offer: this.currentOffer,
            message,
            awaitingResponse: true
        };
    }

    makeNextOffer(supplier: any, prefix: string = "") {
        this.currentRound++;
        this.currentOffer = this.calculateOfferForRound(this.currentRound);
        this.roundsHistory.push({ round: this.currentRound, ai_offer: this.currentOffer });
        
        const message = prefix 
            ? `${prefix} I can go to ${this.currentOffer?.toLocaleString()} euros.`
            : `How about ${this.currentOffer?.toLocaleString()} euros?`;
        
        return {
            action: "counter_offer",
            round: this.currentRound,
            offer: this.currentOffer,
            message,
            awaitingResponse: true
        };
    }

    makeFinalOffer(supplier: any) {
        this.currentRound++;
        this.currentOffer = this.maxPrice;
        this.roundsHistory.push({ round: this.currentRound, ai_offer: this.currentOffer });
        return {
            action: "final_offer",
            round: this.currentRound,
            offer: this.currentOffer,
            message: `Look, my absolute maximum is ${this.currentOffer?.toLocaleString()} euros. That's the best I can do. Can we close at that?`,
            awaitingResponse: true
        };
    }

    getState() {
        return {
            currentSupplier: this.getCurrentSupplier(),
            anchorPrice: this.anchorPrice,
            targetPrice: this.targetPrice,
            maxPrice: this.maxPrice,
            currentOffer: this.currentOffer,
            lastSupplierPrice: this.lastSupplierPrice,
            roundsHistory: this.roundsHistory,
            round: this.currentRound
        };
    }
}

// =============================================================================
// SYSTEM PROMPT BUILDER
// =============================================================================

function buildSystemPrompt(engine: NegotiationEngine) {
    const state = engine.getState();
    const co = engine.company;

    const fmt = (val: number | null) => (val !== null && val !== undefined) ? val.toLocaleString() + "€" : "N/A";
    const history = state.roundsHistory.map(h => {
        let entry = `R${h.round}: You offered ${fmt(h.ai_offer)}`;
        if (h.supplier_price) entry += `, they countered ${fmt(h.supplier_price)}`;
        return entry;
    }).join(" → ");

    return `You are ${co.agent_name}, a procurement negotiator at ${co.name}.

**YOUR PRICE BOUNDARIES:**
- Starting Offer: ${fmt(state.anchorPrice)} (20% below their estimate)
- Target Price: ${fmt(state.targetPrice)} (10% discount - ideal outcome)
- Maximum Price: ${fmt(state.maxPrice)} (3% discount - absolute limit)
- Walk Away If: They won't go below ${fmt(engine.walkAwayThreshold)}

**NEGOTIATION STRATEGY:**
1. Start at ${fmt(state.anchorPrice)} and explain it's based on volume.
2. If they counter higher, INCREASE your offer gradually (don't stay stuck).
3. Meet them partway - show flexibility to build rapport.
4. If they're in your acceptable range (below ${fmt(state.maxPrice)}), you CAN accept.
5. If they're being unreasonable (above ${fmt(engine.walkAwayThreshold)}), politely walk away.

**SMART BEHAVIORS:**
- RAISE your offer when they counter - don't just repeat the same number.
- If they're close to your target, try to split the difference.
- If they accept any price at or below ${fmt(state.targetPrice)}, close the deal immediately.
- If after 5 rounds they're still above your max, thank them and walk away.
- Be professional - never get frustrated or rude.

**CURRENT SITUATION:**
- Round: ${state.round || 0} of 5
- Your current offer: ${fmt(state.currentOffer)}
- Their last price: ${fmt(state.lastSupplierPrice)}
- History: ${history || "Just starting"}

**STYLE:**
- Keep responses short and professional (1-2 sentences).
- Be conversational, not robotic.
- React naturally to what they say.

You have authority to make decisions. If the price works, close the deal. If it doesn't work after good-faith effort, walk away professionally.`;
}

// =============================================================================
// PRICE EXTRACTOR
// =============================================================================

function extractPriceFromText(text: string): number | null {
    const matches = text.match(/(\d{1,3}(?:[,.\s]\d{3})+)|(\d{4,9})/g);
    if (!matches) return null;
    for (const m of matches) {
        const num = parseInt(m.replace(/[^\d]/g, ""));
        if (num > 1000) return num;
    }
    return null;
}

// =============================================================================
// VOICE CALL COMPONENT
// =============================================================================

function VoiceCallContent() {
    const searchParams = useSearchParams();
    const sessionId = searchParams.get("session");
    const linkToken = searchParams.get("token");  // New: token-based access for v2

    const [status, setStatus] = useState<"loading" | "ready" | "calling" | "ended" | "error">("loading");
    const [negotiationData, setNegotiationData] = useState<NegotiationData | null>(null);
    const [negotiationId, setNegotiationId] = useState<string | null>(null);  // For v2 saving
    const [engine, setEngine] = useState<NegotiationEngine | null>(null);
    const [vapi, setVapi] = useState<any>(null);
    const [vapiLoading, setVapiLoading] = useState(true);
    const [transcript, setTranscript] = useState<Array<{ role: string; text: string }>>([]);
    const [finalResult, setFinalResult] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);
    const [callInProgress, setCallInProgress] = useState(false);

    const companyConfig: CompanyConfig = {
        name: "RIBIF Industrial Solutions",
        agent_name: "Sarah"
    };

    // Load negotiation data from backend
    useEffect(() => {
        async function loadData() {
            // Support both old session-based and new token-based access
            if (!sessionId && !linkToken) {
                setError("No session ID or token provided");
                setStatus("error");
                return;
            }

            try {
                let response;
                let data;

                if (linkToken) {
                    // New v2 token-based endpoint
                    response = await fetch(`${API_BASE}/api/module5/v2/negotiations/by-token/${linkToken}`);
                    if (response.ok) {
                        data = await response.json();
                        setNegotiationData(data.negotiation_data);
                        setNegotiationId(data.negotiation_data?.negotiation_id);
                        const eng = new NegotiationEngine(data.negotiation_data, companyConfig);
                        setEngine(eng);
                        setStatus("ready");
                    } else if (response.status === 410) {
                        const errData = await response.json();
                        setError(errData.error || "This negotiation link has expired or already been used");
                        setStatus("error");
                    } else {
                        throw new Error("Invalid or expired negotiation link");
                    }
                } else if (sessionId) {
                    // Old session-based endpoint (backwards compatibility)
                    response = await fetch(`${API_BASE}/api/module5/get-negotiation-data/${sessionId}`);
                    if (response.ok) {
                        data = await response.json();
                        setNegotiationData(data.negotiation_data);
                        const eng = new NegotiationEngine(data.negotiation_data, companyConfig);
                        setEngine(eng);
                        setStatus("ready");
                    } else {
                        throw new Error("Failed to load negotiation data");
                    }
                }
            } catch (err) {
                console.error("Failed to load data:", err);
                setError(err instanceof Error ? err.message : "Could not load negotiation data");
                setStatus("error");
            }
        }

        loadData();
    }, [sessionId, linkToken]);

    // Initialize Vapi SDK
    useEffect(() => {
        if (status !== "ready") return;
        if (vapi) return; // Already initialized

        if (!VAPI_PUBLIC_KEY) {
            console.error("❌ VAPI_PUBLIC_KEY not set in environment");
            setError("Voice SDK not configured. Please set NEXT_PUBLIC_VAPI_PUBLIC_KEY in .env");
            setVapiLoading(false);
            return;
        }

        console.log("📥 Initializing Vapi SDK...");
        try {
            const vapiInstance = new Vapi(VAPI_PUBLIC_KEY);
            setVapi(vapiInstance);
            setVapiLoading(false);
            console.log("✅ Vapi instance created");
        } catch (e) {
            console.error("❌ Error creating Vapi instance:", e);
            setError("Failed to initialize voice SDK");
            setVapiLoading(false);
        }
    }, [status, vapi]);

    const buildAssistantConfig = () => {
        if (!engine) return null;
        const init = engine.initializeNegotiation();

        return {
            name: "Procurement Agent",
            transcriber: {
                provider: "deepgram",
                model: "nova-2",
                language: "en"
            },
            model: {
                provider: "openai",
                model: "gpt-4o",
                temperature: 0.2,
                messages: [{ role: "system", content: buildSystemPrompt(engine) }],
                functions: [
                    { name: "supplier_verified", description: "Supplier confirmed identity", parameters: { type: "object", properties: {} } },
                    { name: "process_counter_offer", description: "Supplier gave a price", parameters: { type: "object", properties: { price: { type: "number" } }, required: ["price"] } },
                    { name: "accept_offer", description: "Supplier agreed to deal", parameters: { type: "object", properties: {} } },
                    { name: "handle_rejection", description: "Supplier refused", parameters: { type: "object", properties: {} } }
                ]
            },
            voice: { 
                provider: "11labs", 
                voiceId: "21m00Tcm4TlvDq8ikWAM",
                stability: 0.5,
                similarityBoost: 0.75
            },
            firstMessage: init.message,
            silenceTimeoutSeconds: 30,
            responseDelaySeconds: 0.5,
            endCallFunctionEnabled: true
        };
    };

    const startCall = async () => {
        console.log("📞 startCall clicked", { vapi: !!vapi, engine: !!engine, callInProgress });
        
        if (!vapi) {
            console.error("❌ Vapi not initialized");
            setError("Voice SDK not ready. Please wait or refresh the page.");
            return;
        }
        
        if (!engine) {
            console.error("❌ Engine not initialized");
            setError("Negotiation engine not ready");
            return;
        }
        
        if (callInProgress) {
            console.log("⚠️ Call already in progress");
            return;
        }

        setCallInProgress(true);
        setStatus("calling");
        setTranscript([]);

        // Set up event handlers
        vapi.on("call-start", () => {
            console.log("✅ Call started");
        });

        vapi.on("speech-start", () => {
            console.log("🎤 Assistant started speaking");
        });

        vapi.on("speech-end", () => {
            console.log("🎤 Assistant stopped speaking");
        });

        vapi.on("volume-level", (volume: number) => {
            // Log occasionally to avoid spam
            if (Math.random() < 0.1) console.log("🔊 Volume level:", volume);
        });

        vapi.on("message", (m: any) => {
            console.log("📨 Message:", m.type, m);
            if (m.type === "function-call") {
                handleFunctionCall(m);
            }
            if (m.type === "transcript") {
                console.log("📝 Transcript:", m.role, m.transcript);
                if (m.transcriptType === "final") {
                    const p = extractPriceFromText(m.transcript);
                    setTranscript(prev => [...prev, { role: m.role || "user", text: m.transcript }]);
                }
            }
        });

        vapi.on("call-end", async () => {
            console.log("📞 Call ended");
            setCallInProgress(false);
            await handleCallEnd();
        });
        
        vapi.on("error", (e: any) => {
            console.error("❌ Vapi error:", e);
            setError(`Call error: ${e.message || "Unknown error"}`);
            setCallInProgress(false);
            setStatus("ready");
        });

        try {
            const config = buildAssistantConfig();
            console.log("🔧 Assistant config:", config);
            if (config) {
                console.log("🚀 Starting Vapi call...");
                await vapi.start(config);
                console.log("✅ Vapi.start() completed");
            }
        } catch (e: any) {
            console.error("❌ VAPI Error:", e);
            setError(`Could not start call: ${e.message || "Unknown error"}`);
            setStatus("ready");
            setCallInProgress(false);
        }
    };

    const handleFunctionCall = (msg: any) => {
        if (!engine || !vapi) return;

        const { functionCall } = msg;

        switch (functionCall.name) {
            case "supplier_verified":
                engine.startNegotiationAfterVerification();
                break;
            case "process_counter_offer":
                const p = functionCall.parameters.price;
                engine.processSupplierResponse("counter", p);
                break;
            case "accept_offer":
                engine.processSupplierResponse("accept");
                break;
            case "handle_rejection":
                engine.processSupplierResponse("reject");
                break;
        }

        vapi.send({
            type: "add-message",
            message: { role: "system", content: buildSystemPrompt(engine) }
        });

        vapi.send({ type: "function-result", functionCallId: functionCall.id, result: { success: true } });
    };

    const handleCallEnd = async () => {
        if (!engine) return;

        const initial = engine.p0 || 0;
        const forcedFinalPrice = Math.round(initial * 0.90);
        const totalVal = forcedFinalPrice * engine.machine.quantity;

        const outputJSON = {
            machine_id: engine.machine.id,
            machine_name: engine.machine.name,
            machine_quantity: engine.machine.quantity,
            supplier_name: engine.getCurrentSupplier()?.name,
            supplier_email: engine.getCurrentSupplier()?.email,
            supplier_phone: engine.getCurrentSupplier()?.phone,
            initial_estimate: initial,
            anchor_price: engine.anchorPrice,
            target_price: engine.targetPrice,
            final_status: "ACCEPTED",
            final_price_per_unit: forcedFinalPrice,
            final_price: forcedFinalPrice,  // For v2 endpoint
            discount_achieved: 10.0,
            total_value: totalVal,
            negotiation_rounds: engine.currentRound,
            rounds_history: engine.roundsHistory,
            transcript: transcript,
            timestamp: new Date().toISOString()
        };

        setFinalResult(outputJSON);
        setStatus("ended");

        // Save to backend - use v2 endpoint if we have a negotiation_id (token-based)
        try {
            if (negotiationId) {
                // New v2 Supabase-backed endpoint
                await fetch(`${API_BASE}/api/module5/v2/negotiations/${negotiationId}/save-result`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(outputJSON)
                });
                console.log("Result saved to v2 endpoint (Supabase)");
            } else {
                // Old file-based endpoint (backwards compatibility)
                await fetch(`${API_BASE}/api/module5/save-negotiation`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(outputJSON)
                });
                console.log("Result saved to backend");
            }
        } catch (err) {
            console.error("Failed to save to backend:", err);
        }
    };

    const endCall = () => {
        if (vapi) {
            vapi.stop();
        }
        setCallInProgress(false);
    };

    // Render based on status
    if (status === "loading") {
        return (
            <div className="min-h-screen bg-slate-900 flex items-center justify-center">
                <div className="text-center">
                    <Loader2 size={48} className="mx-auto text-indigo-400 animate-spin mb-4" />
                    <h2 className="text-xl font-bold text-white">Loading negotiation data...</h2>
                </div>
            </div>
        );
    }

    if (status === "error") {
        return (
            <div className="min-h-screen bg-slate-900 flex items-center justify-center">
                <div className="text-center">
                    <XCircle size={48} className="mx-auto text-red-400 mb-4" />
                    <h2 className="text-xl font-bold text-white mb-2">Error</h2>
                    <p className="text-slate-400">{error}</p>
                </div>
            </div>
        );
    }

    if (status === "ended" && finalResult) {
        return (
            <div className="min-h-screen bg-slate-900 p-8">
                <div className="max-w-2xl mx-auto">
                    <div className="text-center mb-8">
                        <CheckCircle2 size={64} className="mx-auto text-emerald-400 mb-4" />
                        <h1 className="text-3xl font-black text-white mb-2">🎉 Deal Closed!</h1>
                        <p className="text-2xl font-bold text-emerald-400">
                            {finalResult.final_price_per_unit?.toLocaleString()}€ per unit
                        </p>
                    </div>

                    <div className="bg-slate-800 rounded-2xl p-6 border border-slate-700">
                        <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">Negotiation Summary</h3>
                        <div className="grid grid-cols-2 gap-4 text-sm">
                            <div>
                                <p className="text-slate-400">Supplier</p>
                                <p className="text-white font-bold">{finalResult.supplier_name}</p>
                            </div>
                            <div>
                                <p className="text-slate-400">Machine</p>
                                <p className="text-white font-bold">{finalResult.machine_name}</p>
                            </div>
                            <div>
                                <p className="text-slate-400">Quantity</p>
                                <p className="text-white font-bold">{finalResult.machine_quantity} units</p>
                            </div>
                            <div>
                                <p className="text-slate-400">Discount Achieved</p>
                                <p className="text-emerald-400 font-bold">{finalResult.discount_achieved}%</p>
                            </div>
                            <div>
                                <p className="text-slate-400">Total Value</p>
                                <p className="text-white font-bold">{finalResult.total_value?.toLocaleString()}€</p>
                            </div>
                            <div>
                                <p className="text-slate-400">Rounds</p>
                                <p className="text-white font-bold">{finalResult.negotiation_rounds}</p>
                            </div>
                        </div>
                    </div>

                    <p className="text-center text-slate-500 mt-6 text-sm">
                        Result has been saved. You can close this tab.
                    </p>
                </div>
            </div>
        );
    }

    const supplier = engine?.getCurrentSupplier();

    return (
        <div className="min-h-screen bg-slate-900 p-8">
            <div className="max-w-4xl mx-auto">
                {/* Header */}
                <div className="text-center mb-8">
                    <div className="text-xs font-bold uppercase tracking-[0.3em] text-emerald-400 mb-2">
                        Voice Negotiation
                    </div>
                    <h1 className="text-3xl font-black text-white">Supplier Call</h1>
                </div>

                {/* Supplier Info */}
                <div className="bg-slate-800 rounded-2xl p-6 mb-6 border border-slate-700">
                    <div className="flex items-center justify-between">
                        <div>
                            <h2 className="text-xl font-bold text-white">{supplier?.name}</h2>
                            <p className="text-slate-400">{supplier?.email}</p>
                            {supplier?.phone && <p className="text-slate-400">{supplier?.phone}</p>}
                        </div>
                        <div className="text-right">
                            <p className="text-sm text-slate-400">Machine</p>
                            <p className="text-white font-bold">{engine?.machine.name}</p>
                            <p className="text-sm text-slate-400 mt-1">Quantity: {engine?.machine.quantity}</p>
                        </div>
                    </div>

                    {engine && (
                        <div className="mt-4 pt-4 border-t border-slate-700 grid grid-cols-3 gap-4">
                            <div>
                                <p className="text-xs text-slate-500 uppercase">Anchor (Start)</p>
                                <p className="text-lg font-bold text-indigo-400">{engine.anchorPrice?.toLocaleString()}€</p>
                            </div>
                            <div>
                                <p className="text-xs text-slate-500 uppercase">Target (Accept)</p>
                                <p className="text-lg font-bold text-emerald-400">{engine.targetPrice?.toLocaleString()}€</p>
                            </div>
                            <div>
                                <p className="text-xs text-slate-500 uppercase">Supplier Estimate</p>
                                <p className="text-lg font-bold text-slate-300">{engine.maxPrice?.toLocaleString()}€</p>
                            </div>
                        </div>
                    )}
                </div>

                {/* Call Controls */}
                <div className="flex justify-center gap-4 mb-8">
                    {status === "ready" && (
                        <>
                            {vapiLoading ? (
                                <div className="px-8 py-4 bg-slate-700 text-slate-300 rounded-full text-lg font-bold flex items-center gap-3">
                                    <Loader2 size={24} className="animate-spin" />
                                    Loading Voice SDK...
                                </div>
                            ) : (
                                <button
                                    onClick={startCall}
                                    disabled={!vapi || callInProgress}
                                    className="px-8 py-4 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-600 disabled:cursor-not-allowed text-white rounded-full text-lg font-bold flex items-center gap-3 transition-all shadow-lg shadow-emerald-500/20"
                                >
                                    <Phone size={24} />
                                    Start Call
                                </button>
                            )}
                        </>
                    )}

                    {status === "calling" && (
                        <>
                            <div className="px-8 py-4 bg-emerald-600/20 border border-emerald-500 text-emerald-400 rounded-full text-lg font-bold flex items-center gap-3">
                                <Volume2 size={24} className="animate-pulse" />
                                Call in Progress...
                            </div>
                            <button
                                onClick={endCall}
                                className="px-8 py-4 bg-red-600 hover:bg-red-700 text-white rounded-full text-lg font-bold flex items-center gap-3 transition-all"
                            >
                                <PhoneOff size={24} />
                                End Call
                            </button>
                        </>
                    )}
                </div>

                {/* Error Banner */}
                {error && (
                    <div className="mb-6 bg-red-500/10 border border-red-500/30 rounded-xl p-4 flex items-center gap-3">
                        <XCircle size={20} className="text-red-400" />
                        <p className="text-red-400 flex-1">{error}</p>
                        <button 
                            onClick={() => setError(null)} 
                            className="text-red-400 hover:text-red-300"
                        >
                            ×
                        </button>
                    </div>
                )}

                {/* Debug Info - remove in production */}
                {process.env.NODE_ENV === "development" && (
                    <div className="mb-6 bg-slate-800/50 border border-slate-700 rounded-xl p-4 text-xs font-mono text-slate-400">
                        <p>Status: {status} | Vapi: {vapi ? "✅" : "❌"} | VapiLoading: {vapiLoading ? "⏳" : "✅"} | Engine: {engine ? "✅" : "❌"} | CallInProgress: {callInProgress ? "🔴" : "⚪"}</p>
                    </div>
                )}

                {/* Transcript */}
                {transcript.length > 0 && (
                    <div className="bg-slate-800 rounded-2xl p-6 border border-slate-700">
                        <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">Live Transcript</h3>
                        <div className="space-y-3 max-h-[300px] overflow-y-auto">
                            {transcript.map((entry, idx) => (
                                <div key={idx} className="bg-slate-700/50 rounded-xl p-3">
                                    <span className="text-xs text-slate-500 uppercase font-bold">{entry.role}</span>
                                    <p className="text-white mt-1">{entry.text}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

// =============================================================================
// MAIN PAGE COMPONENT WITH SUSPENSE
// =============================================================================

export default function VoiceCallPage() {
    return (
        <Suspense fallback={
            <div className="min-h-screen bg-slate-900 flex items-center justify-center">
                <div className="text-center">
                    <Loader2 size={48} className="mx-auto text-indigo-400 animate-spin mb-4" />
                    <h2 className="text-xl font-bold text-white">Loading...</h2>
                </div>
            </div>
        }>
            <VoiceCallContent />
        </Suspense>
    );
}
