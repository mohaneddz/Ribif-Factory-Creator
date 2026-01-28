"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Grid, Float } from "@react-three/drei";
import {
    FileText, Layers, Video, Globe, Check,
    Upload, Loader2, Download, RefreshCw, Sparkles, Building2,
    Info, Play, FileSearch, Eye, BrainCircuit, Calculator,
    Briefcase, X, FileSpreadsheet, Presentation, ChevronLeft, ChevronRight, BookOpen
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import clsx from "clsx";
import { useRouter } from "next/navigation";
import HTMLFlipBook from "react-pageflip";

// ==========================================
// 0. STYLES (Outfit Font)
// ==========================================

const fontStyle = `
  @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&display=swap');
  
  body, div, button, input, table, h1, h2, h3, p {
    font-family: 'Outfit', sans-serif;
  }

    @keyframes progress {
        0% { transform: translateX(-100%); }
        100% { transform: translateX(300%); }
    }
`;

// ==========================================
// 1. CONFIGURATION
// ==========================================

const API_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:5000";

const MODULES = [
    { id: 1, title: "Analyse Specs", icon: FileText, file: "Specs_V1.pdf", type: "specs", statusText: "Extraction des données..." },
    { id: 2, title: "Sourcing Global", icon: Globe, file: "Liste_Sourcing.xlsx", type: "sourcing", statusText: "Recherche fournisseurs..." },
    { id: 3, title: "Analyse TCO", icon: Calculator, file: "Rapport_TCO.json", type: "tco", statusText: "Calcul des coûts..." },
    { id: 4, title: "Business Plan", icon: Briefcase, file: "Business_Plan.xlsx", type: "businessplan", statusText: "Génération du plan..." },
    { id: 5, title: "Pitch Deck", icon: Presentation, file: "Pitch_Deck.pdf", type: "pitchdeck", statusText: "Génération du pitch deck..." },
    { id: 6, title: "Catalogue Technique", icon: BookOpen, file: "Catalogue_Produits.pdf", type: "catalogue", statusText: "Génération du catalogue..." }
];

const MODULE_LOADING_META: Record<string, { kicker: string; description: string; bullets: string[]; accent: string; glow: string }> = {
    specs: {
        kicker: "Lecture du cahier des charges",
        description: "Extraction intelligente des contraintes techniques, matières premières et volumes cibles.",
        bullets: ["OCR & segmentation", "Normalisation des unités", "Structuration des specs"],
        accent: "from-indigo-600 via-violet-600 to-fuchsia-600",
        glow: "bg-fuchsia-500",
    },
    plans: {
        kicker: "Planification industrielle",
        description: "Génération du layout usine, zones de production et flux logistiques.",
        bullets: ["Zonage intelligent", "Gabarits machines", "Flux & sécurité"],
        accent: "from-emerald-600 via-teal-600 to-cyan-600",
        glow: "bg-cyan-500",
    },
    video: {
        kicker: "Rendu immersif",
        description: "Création d'une visite virtuelle réaliste avec scènes 3D et animations.",
        bullets: ["Scènes 3D", "Caméras & parcours", "Export vidéo"],
        accent: "from-amber-500 via-orange-500 to-rose-500",
        glow: "bg-rose-500",
    },
    sourcing: {
        kicker: "Sourcing mondial",
        description: "Identification des fournisseurs et scoring multi-critères.",
        bullets: ["Recherche globale", "Matching besoins", "Classement qualité"],
        accent: "from-sky-600 via-blue-600 to-indigo-600",
        glow: "bg-blue-500",
    },
    tco: {
        kicker: "Analyse des coûts",
        description: "Calcul du TCO, amortissements et projections multi-années.",
        bullets: ["Coûts CAPEX", "OPEX & maintenance", "Projection 5 ans"],
        accent: "from-slate-700 via-slate-800 to-indigo-800",
        glow: "bg-indigo-400",
    },
    businessplan: {
        kicker: "Plan d'affaires",
        description: "Construction du modèle économique et des indicateurs financiers.",
        bullets: ["BMC & ROI", "Pricing", "Synthèse investisseurs"],
        accent: "from-emerald-600 via-green-600 to-lime-600",
        glow: "bg-lime-400",
    },
    catalogue: {
        kicker: "Catalogue technique",
        description: "Compilation des fiches produits et mise en page PDF premium.",
        bullets: ["Fiches produits", "Mise en page", "Export PDF"],
        accent: "from-indigo-700 via-blue-700 to-slate-900",
        glow: "bg-indigo-300",
    },
};

const MOCK_TCO_DATA = {
    "company_name": "SARL ALLO MAISON",
    "project_name": "ALLO MAISON – Complexe Industriel Polymère & Matériaux Avancés",
    "calculation_date": "2025-12-28",
    "total_tco": 14006740000.0,
    "average_annual_tco": 2801348000.0,
    "annual_tco": [
        { "year": 1, "total_tco": 2772928000.0 },
        { "year": 2, "total_tco": 2967032960.0 },
        { "year": 3, "total_tco": 3174725267.2 },
        { "year": 4, "total_tco": 3396956035.9 },
        { "year": 5, "total_tco": 3634742958.42 }
    ],
    "machine_tco": [
        {
            "machine_name": "Machine d'injection plastique",
            "quantity": 3,
            "total_tco": 243600000.0,
            "cost_breakdown": { "initial_pct": 40.42, "operations_pct": 32.79, "maintenance_pct": 21.25 }
        }
    ],
    "raw_materials_tco": [
        { "nom_materiau": "Polyuréthane (PU)", "total_tco": 526500000.0, "unit_price": 405000.0 },
        { "nom_materiau": "Polyurée (2K)", "total_tco": 394875000.0, "unit_price": 607500.0 },
        { "nom_materiau": "Résines époxy", "total_tco": 102060000.0, "unit_price": 405000.0 },
        { "nom_materiau": "UTG (verre flexible)", "total_tco": 530550000.0, "unit_price": 4050000.0 }
    ]
};

const TcoView = ({ data, loading }: { data: any, loading: boolean }) => {
    // Use real data if available, otherwise fall back to mock
    const tcoData = data || MOCK_TCO_DATA;
    const totalTco = tcoData.total_tco || 0;
    const avgAnnualTco = tcoData.average_annual_tco || 0;
    const annualTco = tcoData.annual_tco || tcoData?.data?.annual_tco || [];
    const machineTco = tcoData.machine_tco || [];
    const productTco = tcoData.product_tco || [];
    const rawMaterialsTco = tcoData.raw_materials_tco || [];
    const totalMachinesTco = tcoData.total_machines_tco || 0;
    const totalProductsTco = tcoData.total_products_tco || 0;
    const totalMaterialsTco = tcoData.total_raw_materials_tco || 0;
    const calcDate = tcoData.calculation_date || new Date().toISOString().split('T')[0];

    if (loading) {
        return (
            <div className="h-full flex items-center justify-center">
                <div className="text-center">
                    <Loader2 size={48} className="text-indigo-600 animate-spin mx-auto mb-4" />
                    <h3 className="text-xl font-bold text-slate-800">Calcul du TCO en cours...</h3>
                    <p className="text-slate-500">Analyse des coûts de machines et matériaux</p>
                </div>
            </div>
        );
    }

    return (
        <div className="h-full flex flex-col p-6 gap-6">
            {/* Top Cards: Total TCO & Annual Avg */}
            <div className="grid grid-cols-2 gap-6">
                <div className="bg-slate-900 rounded-[24px] p-8 text-white relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500 rounded-full blur-[60px] opacity-20" />
                    <div className="relative z-10">
                        <div className="text-slate-400 font-bold uppercase tracking-widest text-xs mb-2">TCO Total (5 ans)</div>
                        <div className="text-4xl font-black mb-2">
                            {(totalTco / 1000000000).toFixed(2)} Milliards
                            <span className="text-lg font-bold text-indigo-400 ml-2">DZD</span>
                        </div>
                        <div className="inline-flex items-center gap-2 px-3 py-1 bg-white/10 rounded-full text-xs font-medium">
                            <Sparkles size={12} className="text-indigo-300" />
                            <span>Calculé le {calcDate}</span>
                        </div>
                    </div>
                </div>

                <div className="bg-white border border-slate-200 rounded-[24px] p-8 relative overflow-hidden">
                    <div className="text-slate-400 font-bold uppercase tracking-widest text-xs mb-2">Moyenne Annuelle</div>
                    <div className="text-4xl font-black text-slate-800 mb-2">
                        {(avgAnnualTco / 1000000000).toFixed(2)} Mrd
                        <span className="text-lg font-bold text-slate-400 ml-2">DZD/an</span>
                    </div>
                    <div className="h-1.5 w-full bg-slate-100 rounded-full mt-4 overflow-hidden">
                        <div className="h-full bg-emerald-500 w-[60%]" />
                    </div>
                </div>
            </div>

            <div className="flex-1 grid grid-cols-3 gap-6 min-h-0">
                {/* Annual Evolution Chart (Simplified) */}
                <div className="col-span-2 bg-white border border-slate-200 rounded-[24px] p-6 flex flex-col">
                    <div className="flex justify-between items-center mb-6">
                        <h3 className="font-bold text-slate-800">Évolution Annuelle des Coûts</h3>
                        <div className="flex gap-2">
                            <span className="flex items-center gap-1.5 text-[10px] font-bold text-slate-500 bg-slate-50 px-2 py-1 rounded-md">
                                <div className="w-2 h-2 rounded-full bg-indigo-500" /> Machines
                            </span>
                            <span className="flex items-center gap-1.5 text-[10px] font-bold text-slate-500 bg-slate-50 px-2 py-1 rounded-md">
                                <div className="w-2 h-2 rounded-full bg-emerald-500" /> Produits
                            </span>
                            <span className="flex items-center gap-1.5 text-[10px] font-bold text-slate-500 bg-slate-50 px-2 py-1 rounded-md">
                                <div className="w-2 h-2 rounded-full bg-amber-500" /> Matières
                            </span>
                        </div>
                    </div>
                    <div className="flex-1 flex items-end justify-between px-4 gap-4 pb-2">
                        {annualTco.length > 0 ? annualTco.map((year: any, i: number) => {
                            const maxVal = Math.max(1, ...annualTco.map((y: any) => y.total_tco || 0));
                            const totalVal = year.total_tco || 0;
                            const heightPct = maxVal > 0 ? (totalVal / maxVal) * 100 : 0;
                            const machinesVal = year.machines_tco || 0;
                            const productsVal = year.products_tco || 0;
                            const materialsVal = year.raw_materials_tco || 0;
                            const totalParts = machinesVal + productsVal + materialsVal || 1;
                            const machinesPct = (machinesVal / totalParts) * 100;
                            const productsPct = (productsVal / totalParts) * 100;
                            const materialsPct = (materialsVal / totalParts) * 100;
                            return (
                                <div key={i} className="flex-1 flex flex-col items-center gap-2 group">
                                    <div className="text-[10px] font-bold text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity">
                                        {(totalVal / 1000000000).toFixed(1)} Mrd
                                    </div>
                                    <div className="w-full bg-slate-50 rounded-t-xl relative overflow-hidden" style={{ height: `${Math.max(heightPct, 12)}%` }}>
                                        <div className="absolute bottom-0 left-0 right-0" style={{ height: `${machinesPct}%`, backgroundColor: '#6366f1' }} />
                                        <div className="absolute left-0 right-0" style={{ bottom: `${machinesPct}%`, height: `${productsPct}%`, backgroundColor: '#10b981' }} />
                                        <div className="absolute left-0 right-0" style={{ bottom: `${machinesPct + productsPct}%`, height: `${materialsPct}%`, backgroundColor: '#f59e0b' }} />
                                    </div>
                                    <div className="text-xs font-bold text-slate-600">Année {year.year}</div>
                                </div>
                            );
                        }) : (
                            <div className="flex-1 flex items-center justify-center text-slate-400">Pas de données</div>
                        )}
                    </div>
                </div>

                {/* Cost Distribution */}
                <div className="bg-slate-50 border border-slate-200 rounded-[24px] p-6 overflow-y-auto">
                    <h3 className="font-bold text-slate-800 mb-4">Postes de Coûts</h3>

                    <div className="space-y-4">
                        <div className="bg-white p-4 rounded-xl border border-slate-100 shadow-sm">
                            <div className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Répartition Totale</div>
                            <div className="space-y-2 text-xs">
                                <div className="flex justify-between"><span className="text-slate-500">Machines</span><span className="font-bold text-slate-700">{(totalMachinesTco / 1000000000).toFixed(2)} Mrd</span></div>
                                <div className="flex justify-between"><span className="text-slate-500">Produits</span><span className="font-bold text-slate-700">{(totalProductsTco / 1000000000).toFixed(2)} Mrd</span></div>
                                <div className="flex justify-between"><span className="text-slate-500">Matières</span><span className="font-bold text-slate-700">{(totalMaterialsTco / 1000000000).toFixed(2)} Mrd</span></div>
                            </div>
                        </div>

                        {rawMaterialsTco.length > 0 && (
                            <div className="bg-white p-4 rounded-xl border border-slate-100 shadow-sm">
                                <div className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Matériaux (Top 3)</div>
                                <div className="space-y-3">
                                    {rawMaterialsTco.slice(0, 3).map((mat: any, i: number) => (
                                        <div key={i} className="flex justify-between items-center">
                                            <div className="text-xs font-bold text-slate-700 truncate max-w-[120px]">{mat.nom_materiau}</div>
                                            <div className="text-xs font-medium text-slate-500">{((mat.total_tco || 0) / 1000000).toFixed(0)}M</div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {productTco.length > 0 && (
                            <div className="bg-white p-4 rounded-xl border border-slate-100 shadow-sm">
                                <div className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Produits (Top 3)</div>
                                <div className="space-y-3">
                                    {productTco.slice(0, 3).map((prod: any, i: number) => (
                                        <div key={i} className="flex justify-between items-center">
                                            <div className="text-xs font-bold text-slate-700 truncate max-w-[120px]">{prod.nom_produit}</div>
                                            <div className="text-xs font-medium text-slate-500">{((prod.total_tco || 0) / 1000000).toFixed(0)}M</div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {machineTco.length > 0 && (
                            <div className="bg-white p-4 rounded-xl border border-slate-100 shadow-sm">
                                <div className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Machines ({machineTco.length})</div>
                                <div className="space-y-3">
                                    {machineTco.map((mac: any, i: number) => (
                                        <div key={i} className="space-y-2">
                                            <div className="text-xs font-bold text-slate-700 truncate">{mac.machine_name}</div>
                                            {mac.cost_breakdown && (
                                                <>
                                                    <div className="flex h-2 w-full rounded-full overflow-hidden gap-0.5">
                                                        <div className="bg-indigo-500" style={{ width: `${mac.cost_breakdown.initial_pct || 0}%` }} title="Initial" />
                                                        <div className="bg-emerald-500" style={{ width: `${mac.cost_breakdown.operations_pct || 0}%` }} title="Ops" />
                                                        <div className="bg-amber-500" style={{ width: `${mac.cost_breakdown.maintenance_pct || 0}%` }} title="Maint" />
                                                    </div>
                                                    <div className="flex justify-between text-[9px] text-slate-400 font-medium">
                                                        <span>Init: {mac.cost_breakdown.initial_pct?.toFixed(0) || 0}%</span>
                                                        <span>Ops: {mac.cost_breakdown.operations_pct?.toFixed(0) || 0}%</span>
                                                    </div>
                                                </>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

// ==========================================
// BUSINESS PLAN SECTION TABS
// ==========================================
const BUSINESS_PLAN_TABS = [
    { id: 'bmc', label: 'Business Model Canvas', shortLabel: 'BMC' },
    { id: 'capex', label: 'CapEx', shortLabel: 'CapEx' },
    { id: 'opex', label: 'OpEx', shortLabel: 'OpEx' },
    { id: 'pricing', label: 'Pricing', shortLabel: 'Pricing' },
    { id: 'roi', label: 'Analyse ROI', shortLabel: 'ROI' },
];

// Mock data for Business Plan sections
const MOCK_BUSINESS_PLAN_DATA = {
    bmc: {
        partners: "Fabricants d'équipements industriels, Fournisseurs matières premières, Instituts de certification",
        activities: "Production polymères, R&D, Contrôle qualité, Logistique",
        resources: "Usine moderne, Personnel qualifié, Brevets, Équipements spécialisés",
        value_propositions: "Produits haute performance, Qualité certifiée, Délais courts, Prix compétitifs",
        relationships: "Support technique dédié, SAV réactif, Formation clients",
        channels: "Vente directe B2B, Distributeurs régionaux, E-commerce industriel",
        segments: "Industrie automobile, Construction, Électronique, Aéronautique",
        cost_structure: "Matières premières 45%, Personnel 25%, Énergie 15%, Maintenance 10%, Autres 5%",
        revenue_streams: "Vente produits 85%, Services techniques 10%, Licences 5%"
    },
    capex: {
        equipment: { total: 2500000000, items: ["Ligne d'extrusion", "Presses injection", "Équipements qualité"] },
        infrastructure: { total: 800000000, items: ["Bâtiment industriel", "Installations électriques", "Traitement eaux"] },
        vehicles: { total: 150000000, items: ["Camions livraison", "Chariots élévateurs"] },
        licenses: { total: 50000000, items: ["Certifications ISO", "Licences logicielles"] },
        working_capital: 300000000,
        total_capex: 3800000000
    },
    opex: {
        raw_materials: { annual_cost: 1200000000, growth_rate: 0.05 },
        energy: { annual_cost: 180000000, growth_rate: 0.03 },
        personnel: { annual_cost: 450000000, growth_rate: 0.04 },
        maintenance: { annual_cost: 120000000, growth_rate: 0.02 },
        rent: { annual_cost: 60000000, growth_rate: 0.02 },
        insurance: { annual_cost: 40000000, growth_rate: 0.03 },
        marketing: { annual_cost: 80000000, growth_rate: 0.05 },
        administrative: { annual_cost: 70000000, growth_rate: 0.03 },
        total_annual_opex: 2200000000
    },
    pricing: {
        products: [
            { name: "Polyuréthane Premium", unit_price_dzd: 85000, annual_volume: 50000, annual_revenue: 4250000000 },
            { name: "Résine Époxy Industrielle", unit_price_dzd: 120000, annual_volume: 25000, annual_revenue: 3000000000 },
            { name: "Composite Renforcé", unit_price_dzd: 200000, annual_volume: 15000, annual_revenue: 3000000000 },
        ],
        total_annual_revenue_year1: 10250000000,
        revenue_projections_5y: [10250000000, 11275000000, 12402500000, 13642750000, 15007025000],
        pricing_strategy: "Stratégie de valeur premium avec différenciation qualité"
    },
    roi: {
        npv: 8500000000,
        irr: 0.28,
        payback: 3.2,
        discount_rate: 0.08,
        total_investment: 3800000000
    }
};

const MOCK_PITCH_DECK = {
    filename: "PitchDeck_RIBIF_Project.pptx",
    slides_count: 10,
    size_mb: 2.4,
    created_at: "2025-12-28"
};

const MOCK_EXTRACTED_DATA = {
    ribif_metadata: {
        source_file: "RIBIF_Demo.pdf",
        processed_at: "2026-01-27",
        pages: 42,
    },
    stage_1_informations_generales: {
        informations_generales: {
            nom_projet: "ALLO MAISON – Complexe Industriel Polymère",
            nom_entreprise: "SARL ALLO MAISON",
            raison_sociale: "SARL",
            secteur_activite: "Matériaux avancés",
            type_projet: "Greenfield",
            objectifs_strategiques: ["Substitution des importations", "Capacité locale", "Qualité ISO"],
            description_projet: "Création d'une unité de production de polymères et composites haute performance.",
            localisation: { zone: "Zone Industrielle Rouiba", pays: "Algérie" },
            taille_projet: { echelle: "Grande" },
            classification_danger: { niveau_danger: "moyen", type_dangers: ["Chimique", "Thermique"] },
        }
    },
    stage_2_matieres_premieres: {
        matieres_premieres: [
            { nom_materiau: "Polyuréthane (PU)", categorie: "Chimique", type: "Résine", quantite_estimee: { valeur: 120, unite: "t", periode: "mois" } },
            { nom_materiau: "Résines époxy", categorie: "Chimique", type: "Résine", quantite_estimee: { valeur: 80, unite: "t", periode: "mois" } },
            { nom_materiau: "Fibres de verre", categorie: "Composite", type: "Renfort", quantite_estimee: { valeur: 60, unite: "t", periode: "mois" } },
        ]
    },
    stage_3_produits_fabriques: {
        produits_fabriques: [
            {
                nom_produit: "Panneaux composites",
                categorie: "finished",
                description: "Panneaux légers haute résistance pour l'industrie automobile.",
                specifications_techniques: { normes: ["ISO 9001", "ASTM D256"] },
                volume_production: { capacite: 12000, unite: "m²", periode: "mois" }
            },
            {
                nom_produit: "Revêtements industriels",
                categorie: "finished",
                description: "Revêtements anti-corrosion pour équipements industriels.",
                specifications_techniques: { normes: ["ISO 12944"] },
                volume_production: { capacite: 8000, unite: "m²", periode: "mois" }
            }
        ]
    },
    stage_4_machines_equipements: {
        machines_production: [
            {
                nom_machine: "Extrudeuse double vis",
                type: "Extrusion",
                fabricant_recommande: "PolyTech Solutions",
                quantite_necessaire: 2,
                specifications: { capacite: "500 kg/h", puissance: { value: 250, unit: "kW" } },
                performance: { rendement: { value: 0.92 }, cadence: { value: 500, unit: "kg/h" } }
            },
            {
                nom_machine: "Presse d'injection",
                type: "Injection",
                fabricant_recommande: "Nordic Machines",
                quantite_necessaire: 3,
                specifications: { capacite: "450 cycles/h", puissance: { value: 180, unit: "kW" } },
                performance: { rendement: { value: 0.9 }, cadence: { value: 450, unit: "cycles/h" } }
            }
        ]
    },
    stage_5_processus_production: {
        processus_production: [
            {
                numero_etape: 1,
                nom_etape: "Préparation",
                type_operation: "Mixage",
                description: "Dosage et mélange des matières premières.",
                machines_utilisees: ["Mélangeur haute précision"],
                parametres_process: { temperature: "60°C", pression: "1.2 bar", temps_cycle: "15 min" }
            },
            {
                numero_etape: 2,
                nom_etape: "Mise en forme",
                type_operation: "Extrusion",
                description: "Extrusion et injection des composites.",
                machines_utilisees: ["Extrudeuse double vis", "Presse d'injection"],
                parametres_process: { temperature: "180°C", pression: "2.5 bar", temps_cycle: "8 min" }
            },
            {
                numero_etape: 3,
                nom_etape: "Finition",
                type_operation: "Contrôle",
                description: "Découpe, contrôle qualité et emballage.",
                machines_utilisees: ["Scanner qualité", "Station d'emballage"],
                parametres_process: { temperature: "25°C", pression: "1 bar", temps_cycle: "12 min" }
            }
        ],
        kpi_production: {
            oee_cible: "85%",
            trs_cible: "82%",
            taux_rebut_acceptable: "3%",
            temps_changement_serie: "35 min"
        }
    },
    stage_6_informations_complementaires: {
        aspects_reglementaires: {
            autorisations_requises: ["Autorisation environnementale", "Permis d'exploitation"],
            certifications: ["ISO 14001", "ISO 9001", "REACH"]
        },
        analyse_risques: {
            risques_techniques: ["Variabilité matière", "Sécurité opérateurs"],
            strategies_mitigation: ["Capteurs sécurité", "Contrôle qualité"]
        },
        opportunites: {
            innovation: "Formulation à faible VOC",
            marche: "Demande locale en hausse",
            partenariats: "Fournisseurs régionaux",
            subventions: "Programme national d'industrialisation"
        },
        recommandations: ["Automatiser le packaging", "Mettre en place la récupération chaleur"]
    },
    enriched_machines: [
        {
            nom_machine: "Extrudeuse double vis",
            type: "Extrusion",
            fabricant_recommande: "PolyTech Solutions",
            quantite_necessaire: 2,
            specifications: { capacite: "500 kg/h", puissance: "250 kW" },
            performance: { rendement: "92%", cadence: "500 kg/h" },
            image_url: "https://images.unsplash.com/photo-1518770660439-4636190af475?q=80&w=1200&auto=format&fit=crop",
            image_status: "success"
        }
    ],
    scraping_summary: { successful_scrapes: 1, total_machines: 2 }
};

const MOCK_MODULE4_DATA = {
    machines_enriched: [
        {
            machine_input: {
                nom_machine: "Extrudeuse double vis",
                type: "Extrusion",
                fabricant_recommande: "PolyTech Solutions",
                quantite_necessaire: 2,
                best_image_url: "https://images.unsplash.com/photo-1489515217757-5fd1be406fef?q=80&w=1200&auto=format&fit=crop"
            },
            suppliers: [
                {
                    supplier_name: "Nordic Machines",
                    website: "https://example.com",
                    region: "Europe",
                    price_estimate: "€120k",
                    price_type: "FOB",
                    phone_number: "+33 1 23 45 67 89",
                    email_address: "sales@example.com",
                    customs_algeria_info: "Certificat d'origine requis",
                    relevance_score: 0.9
                },
                {
                    supplier_name: "Shenzhen Resins",
                    website: "https://example.com",
                    region: "Asie",
                    price_estimate: "$105k",
                    price_type: "EXW",
                    phone_number: "+86 21 5555 3333",
                    email_address: "export@example.com",
                    customs_algeria_info: "HS code 8477",
                    relevance_score: 0.75
                }
            ]
        },
        {
            machine_input: {
                nom_machine: "Presse d'injection",
                type: "Injection",
                fabricant_recommande: "Nordic Machines",
                quantite_necessaire: 3,
                best_image_url: ""
            },
            suppliers: [
                {
                    supplier_name: "EuroPress Group",
                    website: "https://example.com",
                    region: "Europe",
                    price_estimate: "€95k",
                    price_type: "CIF",
                    phone_number: "+49 30 1234 5678",
                    email_address: "contact@example.com",
                    customs_algeria_info: "Inspection préalable conseillée",
                    relevance_score: 0.83
                }
            ]
        }
    ]
};

const MOCK_BUSINESS_PLAN_RESPONSE = {
    filename: "Business_Plan_RIBIF.pdf",
    download_url: "/pdf_dash.pdf"
};

const MOCK_PITCH_DECK_RESPONSE = {
    ...MOCK_PITCH_DECK,
    pdf_filename: "PitchDeck_RIBIF_Project.pdf",
    pdf_download_url: "/pdf_dash.pdf",
    data: { slides: Array.from({ length: 10 }, (_, i) => ({ page: i + 1 })) }
};

const BusinessPlanView = ({ businessPlanData, pitchDeckData, loading }: { businessPlanData: any, pitchDeckData: any, loading: boolean }) => {
    const [activeTab, setActiveTab] = useState<string | null>(null);
    const [showOverlay, setShowOverlay] = useState(false);
    const [currentPage, setCurrentPage] = useState(1);
    const totalPages = pitchDeckData?.data?.slides?.length || 10; // Use real slide count if available

    // Get pitch deck file info
    const fallbackPdfUrl = "";
    const pitchDeckPdfUrl = pitchDeckData?.pdf_download_url || fallbackPdfUrl;
    const pitchDeckFilename = pitchDeckData?.pdf_filename || pitchDeckData?.filename || 'pitch_deck.pdf';
    const businessPlanFilename = businessPlanData?.filename || 'business_plan.pdf';
    const businessPlanDownloadUrl = businessPlanData?.download_url || fallbackPdfUrl;

    const handleTabClick = (tabId: string) => {
        setActiveTab(tabId);
        setShowOverlay(true);
    };

    const closeOverlay = () => {
        setShowOverlay(false);
        setActiveTab(null);
    };

    const renderOverlayContent = () => {
        if (!activeTab) return null;
        const data = businessPlanData?.data || {};
        const bmc = data.bmc_content || {};
        const capex = data.capex_data || {};
        const opex = data.opex_data || {};
        const pricing = data.pricing_data || {};
        const roi = data.financial_data || {};

        switch (activeTab) {
            case 'bmc':
                return (
                    <div className="space-y-6">
                        <h3 className="text-lg font-bold text-slate-800 mb-4">Business Model Canvas</h3>
                        <div className="grid grid-cols-3 gap-4">
                            <div className="bg-indigo-50 p-4 rounded-xl border border-indigo-100">
                                <div className="text-xs font-bold text-indigo-600 uppercase tracking-widest mb-2">Partenaires Clés</div>
                                <p className="text-sm text-slate-600">{Array.isArray(bmc.partners) ? bmc.partners.join(" • ") : bmc.partners}</p>
                            </div>
                            <div className="bg-purple-50 p-4 rounded-xl border border-purple-100">
                                <div className="text-xs font-bold text-purple-600 uppercase tracking-widest mb-2">Activités Clés</div>
                                <p className="text-sm text-slate-600">{Array.isArray(bmc.activities) ? bmc.activities.join(" • ") : bmc.activities}</p>
                            </div>
                            <div className="bg-emerald-50 p-4 rounded-xl border border-emerald-100">
                                <div className="text-xs font-bold text-emerald-600 uppercase tracking-widest mb-2">Propositions de Valeur</div>
                                <p className="text-sm text-slate-600">{Array.isArray(bmc.value_propositions) ? bmc.value_propositions.join(" • ") : bmc.value_propositions}</p>
                            </div>
                            <div className="bg-sky-50 p-4 rounded-xl border border-sky-100">
                                <div className="text-xs font-bold text-sky-600 uppercase tracking-widest mb-2">Ressources Clés</div>
                                <p className="text-sm text-slate-600">{Array.isArray(bmc.resources) ? bmc.resources.join(" • ") : bmc.resources}</p>
                            </div>
                            <div className="bg-amber-50 p-4 rounded-xl border border-amber-100">
                                <div className="text-xs font-bold text-amber-600 uppercase tracking-widest mb-2">Relations Clients</div>
                                <p className="text-sm text-slate-600">{Array.isArray(bmc.relationships) ? bmc.relationships.join(" • ") : bmc.relationships}</p>
                            </div>
                            <div className="bg-rose-50 p-4 rounded-xl border border-rose-100">
                                <div className="text-xs font-bold text-rose-600 uppercase tracking-widest mb-2">Segments Clients</div>
                                <p className="text-sm text-slate-600">{Array.isArray(bmc.segments) ? bmc.segments.join(" • ") : bmc.segments}</p>
                            </div>
                        </div>
                        <div className="grid grid-cols-2 gap-4 mt-4">
                            <div className="bg-slate-800 p-4 rounded-xl text-white">
                                <div className="text-xs font-bold text-slate-300 uppercase tracking-widest mb-2">Structure de Coûts</div>
                                <p className="text-sm">{Array.isArray(bmc.cost_structure) ? bmc.cost_structure.join(" • ") : bmc.cost_structure}</p>
                            </div>
                            <div className="bg-emerald-600 p-4 rounded-xl text-white">
                                <div className="text-xs font-bold text-emerald-200 uppercase tracking-widest mb-2">Flux de Revenus</div>
                                <p className="text-sm">{Array.isArray(bmc.revenue_streams) ? bmc.revenue_streams.join(" • ") : bmc.revenue_streams}</p>
                            </div>
                        </div>
                    </div>
                );
            case 'capex':
                return (
                    <div className="space-y-4">
                        <h3 className="text-lg font-bold text-slate-800 mb-4">Capital Expenditures (CapEx)</h3>
                        <div className="space-y-3">
                            {[
                                { label: 'Équipements', value: capex?.equipment?.total },
                                { label: 'Infrastructure', value: capex?.infrastructure?.total },
                                { label: 'Véhicules', value: capex?.vehicles?.total },
                                { label: 'Licences', value: capex?.licenses?.total },
                                { label: 'Fonds de roulement', value: capex?.working_capital },
                            ].map((item, i) => (
                                <div key={i} className="flex justify-between items-center p-4 bg-slate-50 rounded-xl">
                                    <span className="font-medium text-slate-700">{item.label}</span>
                                    <span className="font-bold text-slate-900">{(item.value / 1000000).toFixed(0)} M DZD</span>
                                </div>
                            ))}
                            <div className="flex justify-between items-center p-4 bg-indigo-600 text-white rounded-xl">
                                <span className="font-bold">TOTAL CAPEX</span>
                                <span className="font-black text-xl">{((capex?.total_capex || 0) / 1000000000).toFixed(2)} Mrd DZD</span>
                            </div>
                        </div>
                    </div>
                );
            case 'opex':
                return (
                    <div className="space-y-4">
                        <h3 className="text-lg font-bold text-slate-800 mb-4">Operating Expenses (OpEx) - Annuel</h3>
                        <div className="space-y-3">
                            {[
                                { label: 'Matières Premières', value: opex?.raw_materials?.annual_cost },
                                { label: 'Énergie', value: opex?.energy?.annual_cost },
                                { label: 'Personnel', value: opex?.personnel?.annual_cost },
                                { label: 'Maintenance', value: opex?.maintenance?.annual_cost },
                                { label: 'Loyer', value: opex?.rent?.annual_cost },
                                { label: 'Assurance', value: opex?.insurance?.annual_cost },
                                { label: 'Marketing', value: opex?.marketing?.annual_cost },
                                { label: 'Administratif', value: opex?.administrative?.annual_cost },
                            ].map((item, i) => (
                                <div key={i} className="flex justify-between items-center p-3 bg-slate-50 rounded-xl">
                                    <span className="font-medium text-slate-700">{item.label}</span>
                                    <span className="font-bold text-slate-900">{(item.value / 1000000).toFixed(0)} M DZD</span>
                                </div>
                            ))}
                            <div className="flex justify-between items-center p-4 bg-slate-800 text-white rounded-xl">
                                <span className="font-bold">TOTAL OPEX ANNUEL</span>
                                <span className="font-black text-xl">{((opex?.total_annual_opex || 0) / 1000000000).toFixed(2)} Mrd DZD</span>
                            </div>
                        </div>
                    </div>
                );
            case 'pricing':
                return (
                    <div className="space-y-4">
                        <h3 className="text-lg font-bold text-slate-800 mb-4">Stratégie de Tarification</h3>
                        <table className="w-full">
                            <thead>
                                <tr className="border-b border-slate-200">
                                    <th className="text-left py-3 text-xs font-bold text-slate-400 uppercase">Produit</th>
                                    <th className="text-right py-3 text-xs font-bold text-slate-400 uppercase">Prix Unitaire</th>
                                    <th className="text-right py-3 text-xs font-bold text-slate-400 uppercase">Volume/An</th>
                                    <th className="text-right py-3 text-xs font-bold text-slate-400 uppercase">CA Annuel</th>
                                </tr>
                            </thead>
                            <tbody>
                                {(pricing.products || []).map((p: any, i: number) => (
                                    <tr key={i} className="border-b border-slate-100">
                                        <td className="py-3 font-medium text-slate-700">{p.name}</td>
                                        <td className="py-3 text-right text-slate-600">{p.unit_price_dzd.toLocaleString()} DZD</td>
                                        <td className="py-3 text-right text-slate-600">{p.annual_volume.toLocaleString()}</td>
                                        <td className="py-3 text-right font-bold text-slate-900">{(p.annual_revenue / 1000000000).toFixed(2)} Mrd</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                        <div className="mt-4 p-4 bg-emerald-600 text-white rounded-xl flex justify-between items-center">
                            <span className="font-bold">TOTAL ANNÉE 1</span>
                            <span className="font-black text-xl">{((pricing.total_annual_revenue_year1 || 0) / 1000000000).toFixed(2)} Mrd DZD</span>
                        </div>
                        <div className="mt-4 p-4 bg-slate-50 rounded-xl">
                            <div className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Stratégie</div>
                            <p className="text-sm text-slate-700">{pricing.pricing_strategy}</p>
                        </div>
                    </div>
                );
            case 'roi':
                return (
                    <div className="space-y-4">
                        <h3 className="text-lg font-bold text-slate-800 mb-4">Analyse ROI</h3>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="bg-emerald-50 p-6 rounded-xl border border-emerald-100">
                                <div className="text-xs font-bold text-emerald-600 uppercase tracking-widest mb-2">VAN (NPV)</div>
                                <div className="text-3xl font-black text-emerald-700">{((roi.npv || 0) / 1000000000).toFixed(2)} Mrd</div>
                                <div className="text-sm text-emerald-600 mt-1">DZD</div>
                            </div>
                            <div className="bg-indigo-50 p-6 rounded-xl border border-indigo-100">
                                <div className="text-xs font-bold text-indigo-600 uppercase tracking-widest mb-2">TRI (IRR)</div>
                                <div className="text-3xl font-black text-indigo-700">{((roi.irr || 0) * 100).toFixed(1)}%</div>
                            </div>
                            <div className="bg-amber-50 p-6 rounded-xl border border-amber-100">
                                <div className="text-xs font-bold text-amber-600 uppercase tracking-widest mb-2">Période de Récupération</div>
                                <div className="text-3xl font-black text-amber-700">{(roi.payback || 0).toFixed(1)} ans</div>
                            </div>
                            <div className="bg-slate-100 p-6 rounded-xl border border-slate-200">
                                <div className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Investissement Total</div>
                                <div className="text-3xl font-black text-slate-700">{((roi.total_investment || 0) / 1000000000).toFixed(2)} Mrd</div>
                                <div className="text-sm text-slate-500 mt-1">DZD</div>
                            </div>
                        </div>
                    </div>
                );
            default:
                return null;
        }
    };

    // Loading state
    if (loading) {
        return (
            <div className="h-full flex items-center justify-center">
                <div className="text-center">
                    <Loader2 size={48} className="text-indigo-600 animate-spin mx-auto mb-4" />
                    <h3 className="text-xl font-bold text-slate-800">Génération du Business Plan...</h3>
                    <p className="text-slate-500">Préparation du pitch deck et analyse financière</p>
                </div>
            </div>
        );
    }

    // Waiting state (no data yet)
    if (!businessPlanData && !pitchDeckData) {
        return (
            <div className="h-full flex items-center justify-center">
                <div className="text-center">
                    <FileSpreadsheet size={48} className="text-slate-300 mx-auto mb-4" />
                    <h3 className="text-xl font-bold text-slate-600">En attente du Business Plan...</h3>
                    <p className="text-slate-400">Le calcul TCO doit d'abord se terminer</p>
                </div>
            </div>
        );
    }

    return (
        <div className="h-full flex flex-col p-6 gap-6">
            {/* TOP SECTION: 5 Tabs + Download Buttons */}
            <div className="bg-white rounded-[24px] border border-slate-200 p-6 shadow-sm">
                <div className="flex justify-between items-center mb-4">
                    <div className="text-xs font-bold text-slate-400 uppercase tracking-widest">Sections du Business Plan</div>
                    <div className="flex gap-2">
                        {businessPlanDownloadUrl && (
                            <a
                                href={businessPlanDownloadUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2 rounded-lg text-xs font-bold flex items-center gap-2 transition-all"
                            >
                                <Download size={14} />
                                Business Plan XLSX
                            </a>
                        )}
                        {pitchDeckPdfUrl && (
                            <a
                                href={pitchDeckPdfUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-xs font-bold flex items-center gap-2 transition-all"
                            >
                                <Download size={14} />
                                Pitch Deck PDF
                            </a>
                        )}
                    </div>
                </div>
                <div className="flex gap-2">
                    {BUSINESS_PLAN_TABS.map((tab, index) => (
                        <button
                            key={tab.id}
                            onClick={() => handleTabClick(tab.id)}
                            className={clsx(
                                "flex-1 py-4 px-4 rounded-xl text-sm font-bold transition-all border-2 cursor-pointer",
                                "hover:bg-indigo-50 hover:border-indigo-300 hover:text-indigo-700",
                                "bg-white border-slate-200 text-slate-700",
                                index === 0 && "border-l-4 border-l-emerald-500"
                            )}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>
                <p className="mt-4 text-xs text-slate-400 text-center">Cliquez sur une section pour voir les détails</p>
            </div>

            {/* BOTTOM SECTION: Pitch Deck Preview */}
            <div className="flex-1 bg-slate-900 rounded-[24px] relative overflow-hidden">
                {/* Status Badge */}
                <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20">
                    <div className="bg-emerald-500/90 text-white px-4 py-2 rounded-full text-xs font-bold flex items-center gap-2">
                        <Check size={14} />
                        {pitchDeckData ? 'Pitch Deck Généré' : 'Business Plan Généré'}
                    </div>
                </div>

                {/* Navigation Arrows */}
                <div className="absolute top-1/2 -translate-y-1/2 left-0 right-0 z-20 flex items-center justify-between px-4">
                    <button
                        onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                        disabled={currentPage <= 1}
                        className={clsx(
                            "w-10 h-10 rounded-full flex items-center justify-center transition-all",
                            currentPage <= 1
                                ? "bg-white/10 text-slate-500 cursor-not-allowed"
                                : "bg-white/20 text-white hover:bg-white/30 cursor-pointer"
                        )}
                    >
                        <ChevronLeft size={20} />
                    </button>
                    <button
                        onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                        disabled={currentPage >= totalPages}
                        className={clsx(
                            "w-10 h-10 rounded-full flex items-center justify-center transition-all",
                            currentPage >= totalPages
                                ? "bg-white/10 text-slate-500 cursor-not-allowed"
                                : "bg-white/20 text-white hover:bg-white/30 cursor-pointer"
                        )}
                    >
                        <ChevronRight size={20} />
                    </button>
                </div>

                {/* Page Counter */}
                <div className="absolute bottom-4 left-6 z-20">
                    <span className="text-white text-sm font-medium bg-black/40 px-3 py-1.5 rounded-lg">
                        {currentPage} / {totalPages}
                    </span>
                </div>

                {/* Download Button */}
                <div className="absolute bottom-4 right-6 z-20">
                    {pitchDeckPdfUrl ? (
                        <a
                            href={pitchDeckPdfUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-xs font-bold flex items-center gap-2 transition-all"
                        >
                            <Download size={14} />
                            Télécharger PDF
                        </a>
                    ) : (
                        <button className="bg-slate-600 text-slate-300 px-4 py-2 rounded-lg text-xs font-bold flex items-center gap-2 cursor-not-allowed">
                            <Loader2 size={14} className="animate-spin" />
                            Génération...
                        </button>
                    )}
                </div>

                {/* PDF Preview or Placeholder */}
                <div className="w-full h-full flex items-center justify-center">
                    {pitchDeckPdfUrl ? (
                        <iframe
                            src={`${pitchDeckPdfUrl}#page=${currentPage}&toolbar=0&navpanes=0&scrollbar=0&view=FitH`}
                            className="w-full h-full border-0"
                            title="Pitch Deck Preview"
                        />
                    ) : (
                        <div className="text-center text-white/60">
                            <FileSpreadsheet size={64} className="mx-auto mb-4" />
                            <p className="text-lg font-bold">Pitch Deck en cours de génération...</p>
                            <p className="text-sm">Le PDF sera affiché une fois prêt</p>
                        </div>
                    )}
                </div>
            </div>

            {/* OVERLAY MODAL */}
            <AnimatePresence>
                {showOverlay && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-8"
                        onClick={closeOverlay}
                    >
                        <motion.div
                            initial={{ scale: 0.95, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.95, opacity: 0 }}
                            className="bg-white rounded-[24px] p-8 max-w-4xl w-full max-h-[80vh] overflow-y-auto shadow-2xl"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <div className="flex justify-between items-center mb-6">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 bg-indigo-100 rounded-xl flex items-center justify-center text-indigo-600">
                                        <FileSpreadsheet size={20} />
                                    </div>
                                    <span className="font-bold text-slate-800">{BUSINESS_PLAN_TABS.find(t => t.id === activeTab)?.label}</span>
                                </div>
                                <button
                                    onClick={closeOverlay}
                                    className="w-10 h-10 bg-slate-100 rounded-full flex items-center justify-center text-slate-400 hover:text-slate-600 hover:bg-slate-200 transition-colors"
                                >
                                    <X size={20} />
                                </button>
                            </div>
                            {renderOverlayContent()}
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};



// ==========================================
// 2. SUB-COMPONENTS (CONNECTED TO REAL DATA)
// ==========================================

const SpecsView = ({ data }: any) => {
    // MAP REAL DATA FROM BACKEND
    const info = data?.stage_1_informations_generales?.informations_generales || {};
    const rawMaterials = data?.stage_2_matieres_premieres?.matieres_premieres || [];
    const products = data?.stage_3_produits_fabriques?.produits_fabriques || [];
    const machines = data?.stage_4_machines_equipements?.machines_production || [];
    const process = data?.stage_5_processus_production?.processus_production || [];
    const kpis = data?.stage_5_processus_production?.kpi_production || {};
    const reglementary = data?.stage_6_informations_complementaires?.aspects_reglementaires || {};
    const risks = data?.stage_6_informations_complementaires?.analyse_risques || {};
    const opportunities = data?.stage_6_informations_complementaires?.opportunites || {};
    const recommendations = data?.stage_6_informations_complementaires?.recommandations || [];
    const metadata = data?.ribif_metadata || {};

    // Enrichment data (from web scraping)
    const enrichedMachines = data?.enriched_machines || [];
    const scrapingSummary = data?.scraping_summary || null;

    // Fallbacks if data is missing or loading
    const projectName = info.nom_projet || "Analyse en cours...";
    const companyName = info.nom_entreprise || "N/A";
    const industry = info.secteur_activite || "Industrie";
    const type = info.type_projet || "Standard";
    const objectives = info.objectifs_strategiques || info.objectifs || ["Optimisation", "Modernisation"];
    const description = info.description_projet || "";
    const location = info.localisation || {};
    const dangerClass = info.classification_danger || {};

    return (
        <div className="h-full flex flex-col overflow-hidden">
            {/* Fixed Header */}
            <div className="p-8 pb-4 border-b border-slate-100 bg-white shrink-0">
                <div className="flex items-center gap-6">
                    <div className="w-16 h-16 bg-indigo-50 rounded-2xl flex items-center justify-center text-indigo-600 border border-indigo-100">
                        <Sparkles size={28} />
                    </div>
                    <div>
                        <h3 className="text-3xl font-extrabold text-slate-800">Données Projet</h3>
                        <p className="text-base font-medium text-slate-500">Extraction automatique du cahier des charges</p>
                    </div>
                </div>
            </div>

            {/* Scrollable Content */}
            <div className="flex-1 overflow-y-auto p-8 pt-6 space-y-6">
                {/* Project Info Cards */}
                <div className="grid grid-cols-2 gap-6">
                    <div className="bg-white p-8 rounded-[24px] border border-slate-200 shadow-sm relative overflow-hidden group hover:border-indigo-300 transition-all">
                        <div className="absolute top-0 right-0 w-24 h-24 bg-slate-50 rounded-bl-[100px] -mr-4 -mt-4 transition-colors group-hover:bg-indigo-50" />
                        <div className="relative z-10">
                            <div className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Nom du Projet</div>
                            <div className="text-2xl font-bold text-slate-800">{projectName}</div>
                            <div className="text-sm font-medium text-slate-500 mt-1">{companyName} ({info.raison_sociale || "N/A"})</div>
                        </div>
                    </div>

                    <div className="bg-white p-8 rounded-[24px] border border-slate-200 shadow-sm relative overflow-hidden group hover:border-indigo-300 transition-all">
                        <div className="absolute top-0 right-0 w-24 h-24 bg-slate-50 rounded-bl-[100px] -mr-4 -mt-4 transition-colors group-hover:bg-indigo-50" />
                        <div className="relative z-10">
                            <div className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Industrie</div>
                            <div className="text-2xl font-bold text-slate-800">{industry}</div>
                            <div className="inline-block mt-2 px-3 py-1 rounded-full bg-indigo-50 text-indigo-700 text-xs font-bold uppercase">{type}</div>
                        </div>
                    </div>
                </div>

                {/* Description */}
                {description && (
                    <div className="bg-white p-6 rounded-[24px] border border-slate-200 shadow-sm">
                        <div className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">Description du Projet</div>
                        <p className="text-sm font-medium text-slate-600 leading-relaxed">{description}</p>
                    </div>
                )}

                {/* Objectives de Production - Main Section */}
                <div className="bg-indigo-600 p-8 rounded-[24px] text-white relative overflow-hidden">
                    <div className="absolute -right-10 -bottom-10 opacity-10">
                        <Building2 size={200} />
                    </div>
                    <div className="relative z-10">
                        <div className="text-indigo-200 font-bold uppercase tracking-widest text-xs mb-4">Objectifs Stratégiques</div>
                        <div className="flex gap-3 flex-wrap">
                            {objectives.map((tag: string, i: number) => (
                                <span key={i} className="px-4 py-2 bg-white/10 backdrop-blur-sm rounded-xl border border-white/20 text-sm font-bold">{tag}</span>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Location & Danger Classification */}
                <div className="grid grid-cols-2 gap-6">
                    <div className="bg-white p-6 rounded-[24px] border border-slate-200 shadow-sm">
                        <div className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">Localisation</div>
                        <div className="space-y-2">
                            <div className="flex justify-between"><span className="text-sm text-slate-500">Zone</span><span className="text-sm font-bold text-slate-800">{location.zone || "N/A"}</span></div>
                            <div className="flex justify-between"><span className="text-sm text-slate-500">Pays</span><span className="text-sm font-bold text-slate-800">{location.pays || "N/A"}</span></div>
                            <div className="flex justify-between"><span className="text-sm text-slate-500">Échelle</span><span className="text-sm font-bold text-slate-800">{info.taille_projet?.echelle || "N/A"}</span></div>
                        </div>
                    </div>
                    <div className="bg-white p-6 rounded-[24px] border border-slate-200 shadow-sm">
                        <div className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">Classification Danger</div>
                        <div className="mb-3">
                            <span className={clsx("px-3 py-1.5 rounded-full text-xs font-bold uppercase",
                                dangerClass.niveau_danger === "moyen" ? "bg-amber-50 text-amber-600 border border-amber-100" :
                                    dangerClass.niveau_danger === "élevé" ? "bg-red-50 text-red-600 border border-red-100" :
                                        "bg-emerald-50 text-emerald-600 border border-emerald-100"
                            )}>{dangerClass.niveau_danger || "N/A"}</span>
                        </div>
                        <div className="flex flex-wrap gap-2">
                            {(dangerClass.type_dangers || []).map((d: string, i: number) => (
                                <span key={i} className="px-2 py-1 bg-slate-100 text-slate-600 rounded-lg text-xs font-medium">{d}</span>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Raw Materials Section */}
                {rawMaterials.length > 0 && (
                    <div className="bg-white p-6 rounded-[24px] border border-slate-200 shadow-sm">
                        <div className="flex justify-between items-center mb-4">
                            <div className="text-xs font-bold text-slate-400 uppercase tracking-widest">Matières Premières</div>
                            <span className="px-3 py-1 bg-indigo-50 text-indigo-600 rounded-full text-xs font-bold">{rawMaterials.length} matériaux</span>
                        </div>
                        <div className="max-h-64 overflow-y-auto space-y-3 pr-2">
                            {rawMaterials.map((mat: any, i: number) => (
                                <div key={i} className="p-4 bg-slate-50 rounded-xl border border-slate-100 hover:border-indigo-200 transition-all">
                                    <div className="flex justify-between items-start mb-2">
                                        <div className="font-bold text-slate-800">{mat.nom_materiau}</div>
                                        <span className="px-2 py-0.5 bg-white text-slate-500 rounded text-xs font-medium">{mat.categorie}</span>
                                    </div>
                                    <div className="text-xs text-slate-500 mb-2">{mat.type}</div>
                                    <div className="flex gap-4 text-xs">
                                        <span className="text-slate-600"><strong>Quantité:</strong> {mat.quantite_estimee?.valeur} {mat.quantite_estimee?.unite}/{mat.quantite_estimee?.periode}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Products Section */}
                {products.length > 0 && (
                    <div className="bg-white p-6 rounded-[24px] border border-slate-200 shadow-sm">
                        <div className="flex justify-between items-center mb-4">
                            <div className="text-xs font-bold text-slate-400 uppercase tracking-widest">Produits Fabriqués</div>
                            <span className="px-3 py-1 bg-emerald-50 text-emerald-600 rounded-full text-xs font-bold">{products.length} produits</span>
                        </div>
                        <div className="max-h-80 overflow-y-auto space-y-3 pr-2">
                            {products.map((prod: any, i: number) => (
                                <div key={i} className="p-4 bg-slate-50 rounded-xl border border-slate-100 hover:border-emerald-200 transition-all">
                                    <div className="flex justify-between items-start mb-2">
                                        <div className="font-bold text-slate-800">{prod.nom_produit}</div>
                                        <span className={clsx("px-2 py-0.5 rounded text-xs font-medium",
                                            prod.categorie === "finished" ? "bg-emerald-50 text-emerald-600" : "bg-amber-50 text-amber-600"
                                        )}>{prod.categorie}</span>
                                    </div>
                                    <p className="text-xs text-slate-500 mb-2">{prod.description}</p>
                                    <div className="flex flex-wrap gap-2 mb-2">
                                        {(prod.specifications_techniques?.normes || []).map((n: string, j: number) => (
                                            <span key={j} className="px-2 py-0.5 bg-indigo-50 text-indigo-600 rounded text-xs font-medium">{n}</span>
                                        ))}
                                    </div>
                                    <div className="text-xs text-slate-600">
                                        <strong>Capacité:</strong> {prod.volume_production?.capacite} {prod.volume_production?.unite}/{prod.volume_production?.periode}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Machines with AI Generated Images */}
                {enrichedMachines.length > 0 && (
                    <div className="bg-white p-6 rounded-[24px] border border-slate-200 shadow-sm">
                        <div className="flex justify-between items-center mb-6">
                            <div className="flex items-center gap-3">
                                <div className="text-xs font-bold text-slate-400 uppercase tracking-widest">Machines Industrielles</div>
                                <span className="px-2 py-0.5 bg-purple-50 text-purple-600 rounded text-[10px] font-bold">🤖 AI Generated</span>
                            </div>
                            {scrapingSummary && (
                                <span className={clsx(
                                    "px-3 py-1 rounded-full text-xs font-bold",
                                    scrapingSummary.successful_scrapes === scrapingSummary.total_machines
                                        ? "bg-emerald-50 text-emerald-600"
                                        : scrapingSummary.successful_scrapes > 0
                                            ? "bg-amber-50 text-amber-600"
                                            : "bg-red-50 text-red-600"
                                )}>
                                    {scrapingSummary.successful_scrapes}/{scrapingSummary.total_machines} images
                                </span>
                            )}
                        </div>

                        {/* Machine Cards Grid with Images */}
                        <div className="grid grid-cols-2 gap-4 max-h-[500px] overflow-y-auto pr-2">
                            {enrichedMachines.map((machine: any, i: number) => {
                                const hasImage = Boolean(machine.image_url);
                                const hasError = machine.enrichment_error || machine.image_status === 'error';

                                return (
                                    <div key={i} className="bg-slate-50 rounded-xl border border-slate-100 overflow-hidden hover:border-purple-200 hover:shadow-md transition-all">
                                        {/* Machine Image */}
                                        <div className="h-40 bg-gradient-to-br from-slate-100 to-slate-200 relative overflow-hidden">
                                            {hasImage ? (
                                                <img
                                                    src={machine.image_url}
                                                    alt={machine.nom_machine}
                                                    className="w-full h-full object-cover"
                                                />
                                            ) : (
                                                <div className="w-full h-full flex flex-col items-center justify-center text-slate-400">
                                                    <div className="w-12 h-12 bg-slate-200 rounded-xl flex items-center justify-center mb-2">
                                                        {hasError ? (
                                                            <span className="text-red-400">❌</span>
                                                        ) : (
                                                            <span className="text-slate-300">🔧</span>
                                                        )}
                                                    </div>
                                                    <span className="text-xs font-medium">
                                                        {hasError ? 'Image non disponible' : 'Génération en attente'}
                                                    </span>
                                                </div>
                                            )}
                                            {/* Image Status Badge */}
                                            <div className="absolute top-2 right-2">
                                                <span className={clsx(
                                                    "px-2 py-0.5 rounded-full text-[10px] font-bold backdrop-blur-sm",
                                                    hasImage ? "bg-emerald-500/90 text-white" :
                                                        hasError ? "bg-red-500/90 text-white" :
                                                            "bg-slate-500/90 text-white"
                                                )}>
                                                    {hasImage ? '✓ AI' : hasError ? '✗' : '⏳'}
                                                </span>
                                            </div>
                                        </div>

                                        {/* Machine Details */}
                                        <div className="p-4">
                                            <div className="font-bold text-slate-800 mb-1 line-clamp-1">{machine.nom_machine}</div>
                                            <div className="text-xs text-slate-500 mb-2 line-clamp-1">{machine.type}</div>

                                            <div className="flex items-center gap-2 mb-3">
                                                <span className="px-2 py-0.5 bg-purple-50 text-purple-600 rounded text-xs font-medium">
                                                    x{typeof machine.quantite_necessaire === 'object' ? machine.quantite_necessaire?.value : machine.quantite_necessaire || 1}
                                                </span>
                                                {machine.fabricant_recommande && (
                                                    <span className="px-2 py-0.5 bg-indigo-50 text-indigo-600 rounded text-xs font-medium truncate max-w-[120px]">
                                                        {typeof machine.fabricant_recommande === 'object' ? machine.fabricant_recommande?.value : machine.fabricant_recommande}
                                                    </span>
                                                )}
                                            </div>

                                            {/* Specifications */}
                                            {machine.specifications && (
                                                <div className="grid grid-cols-2 gap-1 text-[11px]">
                                                    {machine.specifications?.capacite && (
                                                        <div className="text-slate-600">
                                                            <span className="text-slate-400">Cap:</span> {typeof machine.specifications.capacite === 'object' ? machine.specifications.capacite.value : machine.specifications.capacite}
                                                        </div>
                                                    )}
                                                    {machine.specifications?.puissance && (
                                                        <div className="text-slate-600">
                                                            <span className="text-slate-400">Puis:</span> {typeof machine.specifications.puissance === 'object' ? machine.specifications.puissance.value : machine.specifications.puissance}
                                                        </div>
                                                    )}
                                                    {machine.performance?.rendement && (
                                                        <div className="text-slate-600">
                                                            <span className="text-slate-400">Rend:</span> {typeof machine.performance.rendement === 'object' ? `${(machine.performance.rendement.value * 100).toFixed(0)}%` : machine.performance.rendement}
                                                        </div>
                                                    )}
                                                    {machine.performance?.cadence && (
                                                        <div className="text-slate-600">
                                                            <span className="text-slate-400">Cad:</span> {typeof machine.performance.cadence === 'object' ? machine.performance.cadence.value : machine.performance.cadence}
                                                        </div>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}


                {/* Production Process Section */}
                {process.length > 0 && (
                    <div className="bg-white p-6 rounded-[24px] border border-slate-200 shadow-sm">
                        <div className="flex justify-between items-center mb-4">
                            <div className="text-xs font-bold text-slate-400 uppercase tracking-widest">Processus de Production</div>
                            <span className="px-3 py-1 bg-sky-50 text-sky-600 rounded-full text-xs font-bold">{process.length} étapes</span>
                        </div>
                        <div className="max-h-80 overflow-y-auto space-y-3 pr-2">
                            {process.map((step: any, i: number) => (
                                <div key={i} className="p-4 bg-slate-50 rounded-xl border border-slate-100 hover:border-sky-200 transition-all">
                                    <div className="flex items-center gap-3 mb-2">
                                        <span className="w-8 h-8 bg-sky-600 text-white rounded-full flex items-center justify-center text-xs font-bold">{step.numero_etape}</span>
                                        <div className="font-bold text-slate-800">{step.nom_etape}</div>
                                        <span className="px-2 py-0.5 bg-sky-50 text-sky-600 rounded text-xs font-medium">{step.type_operation}</span>
                                    </div>
                                    <p className="text-xs text-slate-500 mb-2">{step.description}</p>
                                    <div className="flex flex-wrap gap-1 mb-2">
                                        {(step.machines_utilisees || []).map((m: string, j: number) => (
                                            <span key={j} className="px-2 py-0.5 bg-white border border-slate-200 text-slate-600 rounded text-xs">{m}</span>
                                        ))}
                                    </div>
                                    <div className="grid grid-cols-3 gap-2 text-xs text-slate-600">
                                        <span><strong>Temp:</strong> {step.parametres_process?.temperature}</span>
                                        <span><strong>Pression:</strong> {step.parametres_process?.pression}</span>
                                        <span><strong>Cycle:</strong> {step.parametres_process?.temps_cycle}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* KPIs Section */}
                {Object.keys(kpis).length > 0 && (
                    <div className="bg-gradient-to-r from-indigo-600 to-purple-600 p-6 rounded-[24px] text-white">
                        <div className="text-white/70 font-bold uppercase tracking-widest text-xs mb-4">KPIs de Production</div>
                        <div className="grid grid-cols-4 gap-4">
                            <div className="bg-white/10 backdrop-blur-sm p-4 rounded-xl border border-white/20">
                                <div className="text-white/60 text-xs font-medium mb-1">OEE Cible</div>
                                <div className="text-2xl font-black">{kpis.oee_cible}</div>
                            </div>
                            <div className="bg-white/10 backdrop-blur-sm p-4 rounded-xl border border-white/20">
                                <div className="text-white/60 text-xs font-medium mb-1">TRS Cible</div>
                                <div className="text-2xl font-black">{kpis.trs_cible}</div>
                            </div>
                            <div className="bg-white/10 backdrop-blur-sm p-4 rounded-xl border border-white/20">
                                <div className="text-white/60 text-xs font-medium mb-1">Taux Rebut</div>
                                <div className="text-2xl font-black">{kpis.taux_rebut_acceptable}</div>
                            </div>
                            <div className="bg-white/10 backdrop-blur-sm p-4 rounded-xl border border-white/20">
                                <div className="text-white/60 text-xs font-medium mb-1">Changement Série</div>
                                <div className="text-2xl font-black">{kpis.temps_changement_serie}</div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Regulatory & Risks Section */}
                <div className="grid grid-cols-2 gap-6">
                    {/* Regulatory */}
                    {Object.keys(reglementary).length > 0 && (
                        <div className="bg-white p-6 rounded-[24px] border border-slate-200 shadow-sm">
                            <div className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4">Aspects Réglementaires</div>
                            <div className="space-y-4 max-h-64 overflow-y-auto pr-2">
                                {(reglementary.autorisations_requises || []).length > 0 && (
                                    <div>
                                        <div className="text-xs font-bold text-slate-600 mb-2">Autorisations Requises</div>
                                        <div className="space-y-1">
                                            {reglementary.autorisations_requises.slice(0, 5).map((a: string, i: number) => (
                                                <div key={i} className="text-xs text-slate-500 flex items-start gap-2">
                                                    <span className="w-1.5 h-1.5 bg-amber-400 rounded-full mt-1.5 shrink-0"></span>
                                                    {a}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                                {(reglementary.certifications || []).length > 0 && (
                                    <div>
                                        <div className="text-xs font-bold text-slate-600 mb-2">Certifications</div>
                                        <div className="flex flex-wrap gap-2">
                                            {reglementary.certifications.map((c: string, i: number) => (
                                                <span key={i} className="px-2 py-1 bg-emerald-50 text-emerald-600 rounded-lg text-xs font-medium">{c}</span>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Risks */}
                    {Object.keys(risks).length > 0 && (
                        <div className="bg-white p-6 rounded-[24px] border border-slate-200 shadow-sm">
                            <div className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4">Analyse des Risques</div>
                            <div className="space-y-4 max-h-64 overflow-y-auto pr-2">
                                {(risks.risques_techniques || []).length > 0 && (
                                    <div>
                                        <div className="text-xs font-bold text-red-600 mb-2">Risques Techniques</div>
                                        <div className="space-y-1">
                                            {risks.risques_techniques.slice(0, 3).map((r: string, i: number) => (
                                                <div key={i} className="text-xs text-slate-500 flex items-start gap-2">
                                                    <span className="w-1.5 h-1.5 bg-red-400 rounded-full mt-1.5 shrink-0"></span>
                                                    {r}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                                {(risks.strategies_mitigation || []).length > 0 && (
                                    <div>
                                        <div className="text-xs font-bold text-emerald-600 mb-2">Stratégies de Mitigation</div>
                                        <div className="space-y-1">
                                            {risks.strategies_mitigation.slice(0, 3).map((s: string, i: number) => (
                                                <div key={i} className="text-xs text-slate-500 flex items-start gap-2">
                                                    <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full mt-1.5 shrink-0"></span>
                                                    {s}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>

                {/* Opportunities */}
                {Object.keys(opportunities).length > 0 && (
                    <div className="bg-gradient-to-r from-emerald-500 to-teal-500 p-6 rounded-[24px] text-white">
                        <div className="text-white/70 font-bold uppercase tracking-widest text-xs mb-4">Opportunités</div>
                        <div className="grid grid-cols-4 gap-4">
                            <div className="bg-white/10 backdrop-blur-sm p-4 rounded-xl border border-white/20">
                                <div className="text-white/60 text-xs font-medium mb-1">Innovation</div>
                                <div className="text-sm font-bold">{opportunities.innovation || "N/A"}</div>
                            </div>
                            <div className="bg-white/10 backdrop-blur-sm p-4 rounded-xl border border-white/20">
                                <div className="text-white/60 text-xs font-medium mb-1">Marché</div>
                                <div className="text-sm font-bold">{opportunities.marche || "N/A"}</div>
                            </div>
                            <div className="bg-white/10 backdrop-blur-sm p-4 rounded-xl border border-white/20">
                                <div className="text-white/60 text-xs font-medium mb-1">Partenariats</div>
                                <div className="text-sm font-bold">{opportunities.partenariats || "N/A"}</div>
                            </div>
                            <div className="bg-white/10 backdrop-blur-sm p-4 rounded-xl border border-white/20">
                                <div className="text-white/60 text-xs font-medium mb-1">Subventions</div>
                                <div className="text-sm font-bold">{opportunities.subventions || "N/A"}</div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Recommendations */}
                {recommendations.length > 0 && (
                    <div className="bg-white p-6 rounded-[24px] border border-slate-200 shadow-sm">
                        <div className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4">Recommandations</div>
                        <div className="space-y-2">
                            {recommendations.map((rec: string, i: number) => (
                                <div key={i} className="flex items-start gap-3 p-3 bg-slate-50 rounded-xl">
                                    <span className="w-6 h-6 bg-indigo-600 text-white rounded-full flex items-center justify-center text-xs font-bold shrink-0">{i + 1}</span>
                                    <span className="text-sm text-slate-600">{rec}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

const PlansView = () => (
    <div className="h-full flex flex-col gap-4 p-4">
        {/* Top Section - 2D Plan */}
        <div className="h-1/2 relative bg-white rounded-[32px] overflow-hidden border border-slate-200">
            <div className="absolute top-6 left-6 bg-indigo-600 text-white px-4 py-2 rounded-full text-xs font-bold z-10 shadow-lg shadow-indigo-200">
                VUE 2D (PLAN D'IMPLANTATION)
            </div>
            <div className="absolute top-6 right-6 flex gap-2 z-10">
                <button className="bg-white/90 backdrop-blur text-slate-600 px-3 py-1.5 rounded-lg text-[10px] font-bold border border-slate-200 hover:border-indigo-300 transition-colors">
                    Étage RDC
                </button>
                <button className="bg-slate-100 text-slate-400 px-3 py-1.5 rounded-lg text-[10px] font-bold border border-slate-200 hover:border-indigo-300 transition-colors">
                    Étage 1
                </button>
            </div>
            <div className="h-full w-full flex items-center justify-center bg-slate-50">
                {/* 2D Floor Plan Grid SVG */}
                <svg viewBox="0 0 400 300" className="w-full h-full max-w-3xl p-10">
                    {/* Background Grid */}
                    <defs>
                        <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
                            <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#e2e8f0" strokeWidth="0.5" />
                        </pattern>
                    </defs>
                    <rect width="400" height="300" fill="url(#grid)" />

                    {/* Main Factory Building */}
                    <rect x="40" y="40" width="200" height="150" fill="#e0e7ff" stroke="#4f46e5" strokeWidth="2" rx="4" />
                    <text x="140" y="120" textAnchor="middle" className="text-[10px] font-bold fill-indigo-700">ZONE PRODUCTION</text>

                    {/* Warehouse */}
                    <rect x="260" y="40" width="100" height="80" fill="#dcfce7" stroke="#22c55e" strokeWidth="2" rx="4" />
                    <text x="310" y="85" textAnchor="middle" className="text-[8px] font-bold fill-emerald-700">STOCKAGE</text>

                    {/* Office Area */}
                    <rect x="260" y="130" width="100" height="60" fill="#fef3c7" stroke="#f59e0b" strokeWidth="2" rx="4" />
                    <text x="310" y="165" textAnchor="middle" className="text-[8px] font-bold fill-amber-700">BUREAUX</text>

                    {/* Machines Representation */}
                    <rect x="60" y="60" width="30" height="40" fill="#818cf8" stroke="#4f46e5" strokeWidth="1" rx="2" />
                    <rect x="100" y="60" width="30" height="40" fill="#818cf8" stroke="#4f46e5" strokeWidth="1" rx="2" />
                    <rect x="140" y="60" width="30" height="40" fill="#818cf8" stroke="#4f46e5" strokeWidth="1" rx="2" />
                    <rect x="180" y="60" width="30" height="40" fill="#818cf8" stroke="#4f46e5" strokeWidth="1" rx="2" />

                    <rect x="60" y="130" width="30" height="40" fill="#818cf8" stroke="#4f46e5" strokeWidth="1" rx="2" />
                    <rect x="100" y="130" width="30" height="40" fill="#818cf8" stroke="#4f46e5" strokeWidth="1" rx="2" />
                    <rect x="140" y="130" width="30" height="40" fill="#818cf8" stroke="#4f46e5" strokeWidth="1" rx="2" />
                    <rect x="180" y="130" width="30" height="40" fill="#818cf8" stroke="#4f46e5" strokeWidth="1" rx="2" />

                    {/* Flow Arrows */}
                    <path d="M 95 80 L 95 80" stroke="#4f46e5" strokeWidth="1" markerEnd="url(#arrow)" />

                    {/* Legend */}
                    <rect x="40" y="220" width="12" height="12" fill="#818cf8" stroke="#4f46e5" strokeWidth="1" rx="2" />
                    <text x="58" y="230" className="text-[8px] fill-slate-600">Machines</text>

                    <rect x="120" y="220" width="12" height="12" fill="#e0e7ff" stroke="#4f46e5" strokeWidth="1" rx="2" />
                    <text x="138" y="230" className="text-[8px] fill-slate-600">Production</text>

                    <rect x="200" y="220" width="12" height="12" fill="#dcfce7" stroke="#22c55e" strokeWidth="1" rx="2" />
                    <text x="218" y="230" className="text-[8px] fill-slate-600">Stockage</text>

                    <rect x="280" y="220" width="12" height="12" fill="#fef3c7" stroke="#f59e0b" strokeWidth="1" rx="2" />
                    <text x="298" y="230" className="text-[8px] fill-slate-600">Bureaux</text>
                </svg>
            </div>
            {/* Scale indicator */}
            <div className="absolute bottom-6 right-6 flex items-center gap-2 bg-white/90 backdrop-blur px-3 py-1.5 rounded-lg border border-slate-200 text-[10px] text-slate-500 font-medium">
                <div className="w-12 h-0.5 bg-slate-400"></div>
                <span>10m</span>
            </div>
        </div>

        {/* Bottom Section - 3D Plan */}
        <div className="h-1/2 relative bg-slate-100 rounded-[32px] overflow-hidden border border-slate-200">
            <div className="absolute top-6 left-6 bg-white/90 backdrop-blur text-slate-800 px-4 py-2 rounded-full text-xs font-bold z-10 border border-slate-200 shadow-sm">
                VUE 3D ISOMÉTRIQUE (IFC)
            </div>
            <div className="absolute top-6 right-6 flex gap-2 z-10">
                <button className="bg-white/90 backdrop-blur text-slate-600 px-3 py-1.5 rounded-lg text-[10px] font-bold border border-slate-200 hover:border-indigo-300 transition-colors">
                    Rotation
                </button>
                <button className="bg-white/90 backdrop-blur text-slate-600 px-3 py-1.5 rounded-lg text-[10px] font-bold border border-slate-200 hover:border-indigo-300 transition-colors">
                    Reset
                </button>
            </div>
            <Canvas camera={{ position: [6, 6, 6] }}>
                <ambientLight intensity={0.6} />
                <pointLight position={[10, 10, 10]} />
                <Grid args={[20, 20]} cellColor="#cbd5e1" sectionColor="#94a3b8" />
                <Float speed={2} rotationIntensity={0.5}>
                    <mesh>
                        <boxGeometry args={[3, 1.5, 3]} />
                        <meshStandardMaterial color="#4f46e5" roughness={0.2} metalness={0.1} />
                    </mesh>
                </Float>
                <OrbitControls autoRotate enableZoom={false} />
            </Canvas>
        </div>
    </div>
);

const VideoView = ({ progress }: { progress: number }) => (
    <div className="h-full p-4 flex flex-col gap-4">
        {/* Top Section - Exterior View */}
        <div className="h-1/2 bg-white rounded-[32px] relative overflow-hidden flex items-center justify-center group cursor-pointer border border-slate-200 hover:border-indigo-300 transition-all">
            <div className="absolute top-6 left-6 bg-slate-100 text-slate-700 px-4 py-2 rounded-full text-xs font-bold z-10 border border-slate-200">
                VUE EXTÉRIEURE
            </div>
            <div className="absolute top-6 right-6 flex gap-2 z-10">
                <button className="bg-white text-slate-600 px-3 py-1.5 rounded-lg text-[10px] font-bold border border-slate-200 hover:border-indigo-300 transition-colors">
                    Façade Nord
                </button>
                <button className="bg-slate-50 text-slate-400 px-3 py-1.5 rounded-lg text-[10px] font-bold border border-slate-200 hover:border-indigo-300 transition-colors">
                    Façade Sud
                </button>
            </div>
            {/* Placeholder Content */}
            <div className="flex flex-col items-center gap-4">
                <div className="w-20 h-20 bg-indigo-50 rounded-2xl flex items-center justify-center text-indigo-600 border border-indigo-100 group-hover:bg-indigo-600 group-hover:text-white transition-all">
                    {progress < 100 ? <Loader2 className="animate-spin" size={32} /> : <Play className="ml-1" size={32} />}
                </div>
                <div className="text-center">
                    <div className="text-sm font-bold text-slate-700">Simulation Extérieure 3D</div>
                    <div className="text-xs text-slate-400">Rendu architectural du bâtiment</div>
                </div>
            </div>
        </div>

        {/* Bottom Section - Interior View */}
        <div className="h-1/2 bg-slate-50 rounded-[32px] relative overflow-hidden flex items-center justify-center group cursor-pointer border border-slate-200 hover:border-indigo-300 transition-all">
            <div className="absolute top-6 left-6 bg-white text-slate-700 px-4 py-2 rounded-full text-xs font-bold z-10 border border-slate-200">
                VUE INTÉRIEURE
            </div>
            <div className="absolute top-6 right-6 flex gap-2 z-10">
                <button className="bg-white text-slate-600 px-3 py-1.5 rounded-lg text-[10px] font-bold border border-slate-200 hover:border-indigo-300 transition-colors">
                    Zone Production
                </button>
                <button className="bg-slate-100 text-slate-400 px-3 py-1.5 rounded-lg text-[10px] font-bold border border-slate-200 hover:border-indigo-300 transition-colors">
                    Stockage
                </button>
            </div>
            {/* Placeholder Content */}
            <div className="flex flex-col items-center gap-4">
                <div className="w-20 h-20 bg-white rounded-2xl flex items-center justify-center text-slate-400 border border-slate-200 group-hover:bg-indigo-600 group-hover:text-white group-hover:border-indigo-600 transition-all">
                    {progress < 100 ? <Loader2 className="animate-spin" size={32} /> : <Play className="ml-1" size={32} />}
                </div>
                <div className="text-center">
                    <div className="text-sm font-bold text-slate-700">Visite Virtuelle Usine</div>
                    <div className="text-xs text-slate-400">Parcours interactif des installations</div>
                </div>
            </div>
        </div>
    </div>
);


const SourcingView = ({ progress, data, module4Data, loading }: { progress: number, data: any, module4Data: any, loading: boolean }) => {
    const [selectedMachine, setSelectedMachine] = useState<number>(0);

    // Get enriched machines from module 4
    const enrichedMachines = module4Data?.machines_enriched || [];
    const currentMachine = enrichedMachines[selectedMachine];
    const suppliers = currentMachine?.suppliers || [];

    if (loading) {
        return (
            <div className="p-8 h-full flex items-center justify-center">
                <div className="text-center">
                    <Loader2 size={48} className="text-indigo-600 animate-spin mx-auto mb-4" />
                    <h3 className="text-xl font-bold text-slate-800">Enrichissement des Machines...</h3>
                    <p className="text-slate-500">Module 4 en cours d'exécution</p>
                </div>
            </div>
        );
    }

    if (enrichedMachines.length === 0) {
        return (
            <div className="p-8 h-full flex items-center justify-center">
                <div className="text-center">
                    <Globe size={48} className="text-slate-300 mx-auto mb-4" />
                    <h3 className="text-xl font-bold text-slate-600">En attente des données de sourcing...</h3>
                    <p className="text-slate-400">Le module 4 enrichira les machines avec les fournisseurs</p>
                </div>
            </div>
        );
    }

    return (
        <div className="p-6 h-full flex gap-6">
            {/* Left: Machine List */}
            <div className="w-80 bg-white rounded-[24px] border border-slate-200 p-4 flex flex-col shadow-sm">
                <div className="mb-4">
                    <h3 className="text-sm font-extrabold text-slate-400 uppercase tracking-widest">Machines</h3>
                    <span className="text-xs text-slate-500">{enrichedMachines.length} équipements</span>
                </div>
                <div className="flex-1 overflow-y-auto space-y-2">
                    {enrichedMachines.map((item: any, i: number) => (
                        <div
                            key={i}
                            onClick={() => setSelectedMachine(i)}
                            className={clsx(
                                "p-4 rounded-xl cursor-pointer transition-all border",
                                selectedMachine === i
                                    ? "bg-indigo-50 border-indigo-300 ring-2 ring-indigo-100"
                                    : "bg-slate-50 border-slate-100 hover:border-indigo-200"
                            )}
                        >
                            <div className="font-bold text-sm text-slate-800 truncate">
                                {item.machine_input?.nom_machine || `Machine ${i + 1}`}
                            </div>
                            <div className="text-xs text-slate-500 mt-1 truncate">
                                {item.machine_input?.fabricant_recommande || 'N/A'}
                            </div>
                            <div className="flex gap-2 mt-2">
                                <span className="px-2 py-0.5 bg-emerald-50 text-emerald-600 rounded text-[10px] font-bold">
                                    {item.suppliers?.length || 0} fournisseurs
                                </span>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Right: Supplier Details */}
            <div className="flex-1 bg-white rounded-[24px] border border-slate-200 p-6 overflow-hidden flex flex-col shadow-sm">
                {currentMachine && (
                    <>
                        {/* Machine Header */}
                        <div className="flex items-start gap-4 mb-6 pb-6 border-b border-slate-100">
                            <div className="w-20 h-20 bg-slate-100 rounded-xl flex items-center justify-center overflow-hidden">
                                {currentMachine.machine_input?.best_image_url && !currentMachine.machine_input.best_image_url.startsWith('generated://') ? (
                                    <img src={currentMachine.machine_input.best_image_url} alt="" className="w-full h-full object-cover" />
                                ) : (
                                    <Layers size={32} className="text-slate-400" />
                                )}
                            </div>
                            <div className="flex-1">
                                <h2 className="text-xl font-extrabold text-slate-800">{currentMachine.machine_input?.nom_machine}</h2>
                                <p className="text-sm text-slate-500">{currentMachine.machine_input?.type}</p>
                                <div className="flex gap-2 mt-2">
                                    <span className="px-2 py-1 bg-indigo-50 text-indigo-600 rounded-lg text-xs font-bold">
                                        Qté: {currentMachine.machine_input?.quantite_necessaire || 1}
                                    </span>
                                    <span className="px-2 py-1 bg-slate-100 text-slate-600 rounded-lg text-xs font-bold">
                                        {currentMachine.machine_input?.fabricant_recommande}
                                    </span>
                                </div>
                            </div>
                        </div>

                        {/* Suppliers List */}
                        <div className="flex-1 overflow-y-auto">
                            <h3 className="text-xs font-extrabold text-slate-400 uppercase tracking-widest mb-4">Fournisseurs ({suppliers.length})</h3>
                            <div className="space-y-4">
                                {suppliers.map((supplier: any, i: number) => (
                                    <motion.div
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ delay: i * 0.1 }}
                                        key={i}
                                        className="p-5 bg-slate-50 rounded-xl border border-slate-100 hover:border-indigo-200 transition-all"
                                    >
                                        <div className="flex justify-between items-start mb-3">
                                            <div>
                                                <div className="font-bold text-base text-slate-800">{supplier.supplier_name}</div>
                                                <div className="text-xs text-slate-500">{supplier.region}</div>
                                            </div>
                                            <span className={clsx(
                                                "px-2 py-1 rounded-full text-[10px] font-bold",
                                                (supplier.relevance_score || 0) > 0.8
                                                    ? "bg-emerald-50 text-emerald-600"
                                                    : "bg-amber-50 text-amber-600"
                                            )}>
                                                Score: {Math.round((supplier.relevance_score || 0) * 100)}%
                                            </span>
                                        </div>

                                        <div className="grid grid-cols-2 gap-4 mb-3">
                                            <div>
                                                <div className="text-[10px] font-bold text-slate-400 uppercase">Prix Estimé</div>
                                                <div className="text-sm font-bold text-indigo-600">{supplier.price_estimate || 'Sur demande'}</div>
                                            </div>
                                            <div>
                                                <div className="text-[10px] font-bold text-slate-400 uppercase">Type de Prix</div>
                                                <div className="text-sm text-slate-600">{supplier.price_type || 'N/A'}</div>
                                            </div>
                                        </div>

                                        <div className="flex gap-3 text-xs">
                                            {supplier.website && (
                                                <a href={supplier.website} target="_blank" rel="noopener noreferrer" className="text-indigo-600 hover:underline font-medium">🌐 Site web</a>
                                            )}
                                            {supplier.email_address && (
                                                <a href={`mailto:${supplier.email_address}`} className="text-indigo-600 hover:underline font-medium">✉️ Email</a>
                                            )}
                                            {supplier.phone_number && (
                                                <span className="text-slate-500">📞 {supplier.phone_number}</span>
                                            )}
                                        </div>

                                        {supplier.customs_algeria_info && (
                                            <div className="mt-3 p-3 bg-amber-50 rounded-lg border border-amber-100">
                                                <div className="text-[10px] font-bold text-amber-600 uppercase mb-1">Info Douanes Algérie</div>
                                                <div className="text-xs text-amber-700">{supplier.customs_algeria_info}</div>
                                            </div>
                                        )}
                                    </motion.div>
                                ))}
                            </div>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
};


// Page component for the flipbook
const Page = React.forwardRef<HTMLDivElement, { pageNum: number; pdfDoc: any; scale: number }>(
    ({ pageNum, pdfDoc, scale }, ref) => {
        const canvasRef = useRef<HTMLCanvasElement>(null);
        const renderTaskRef = useRef<any>(null);
        const [rendered, setRendered] = useState(false);
        const renderQueueRef = useRef<Promise<void>>(Promise.resolve());
        const isUnmountedRef = useRef<boolean>(false);

        useEffect(() => {
            if (!pdfDoc || !canvasRef.current) return;

            isUnmountedRef.current = false;
            setRendered(false);

            const renderPage = async () => {
                try {
                    // If a render is in progress, cancel and await it before starting a new one
                    if (renderTaskRef.current) {
                        try {
                            renderTaskRef.current.cancel();
                            await renderTaskRef.current.promise;
                        } catch (e) {
                            // Ignore cancel errors
                        }
                        renderTaskRef.current = null;
                    }

                    if (isUnmountedRef.current) return;

                    const page = await pdfDoc.getPage(pageNum);
                    if (isUnmountedRef.current) return;

                    const viewport = page.getViewport({ scale });
                    const canvas = canvasRef.current;
                    if (!canvas) return;

                    const context = canvas.getContext('2d');
                    if (!context) return;

                    canvas.height = viewport.height;
                    canvas.width = viewport.width;
                    context.clearRect(0, 0, canvas.width, canvas.height);

                    const renderTask = page.render({
                        canvasContext: context,
                        viewport: viewport
                    });
                    renderTaskRef.current = renderTask;

                    await renderTask.promise;
                    if (!isUnmountedRef.current) {
                        setRendered(true);
                    }
                } catch (err: any) {
                    if (err?.name !== 'RenderingCancelledException') {
                        console.error('Error rendering page:', err);
                    }
                }
            };

            renderQueueRef.current = renderQueueRef.current
                .then(renderPage)
                .catch(() => {
                    // Swallow queue errors to keep chain alive
                });

            // Cleanup: cancel render task on unmount
            return () => {
                isUnmountedRef.current = true;
                if (renderTaskRef.current) {
                    try {
                        renderTaskRef.current.cancel();
                    } catch (e) {
                        // Ignore cancel errors
                    }
                    renderTaskRef.current = null;
                }
            };
        }, [pdfDoc, pageNum, scale]);

        return (
            <div ref={ref} className="bg-white shadow-lg" style={{ width: '100%', height: '100%' }}>
                <canvas
                    key={`canvas-${pageNum}`}
                    ref={canvasRef}
                    className="w-full h-full object-contain"
                    style={{ display: rendered ? 'block' : 'none' }}
                />
                {!rendered && (
                    <div className="w-full h-full flex items-center justify-center bg-slate-50">
                        <Loader2 className="animate-spin text-indigo-500" size={24} />
                    </div>
                )}
            </div>
        );
    }
);
Page.displayName = 'Page';

const CatalogueTechniqueView = () => {
    const bookRef = useRef<any>(null);
    const [pdfDoc, setPdfDoc] = useState<any>(null);
    const [numPages, setNumPages] = useState(0);
    const [currentPage, setCurrentPage] = useState(0);
    const [isLoading, setIsLoading] = useState(true);
    const [pdfJsLoaded, setPdfJsLoaded] = useState(false);

    // Load PDF.js from CDN
    useEffect(() => {
        if (typeof window !== 'undefined' && !(window as any).pdfjsLib) {
            const script = document.createElement('script');
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
            script.onload = () => {
                const pdfjsLib = (window as any).pdfjsLib;
                pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
                setPdfJsLoaded(true);
            };
            document.head.appendChild(script);
        } else if ((window as any).pdfjsLib) {
            setPdfJsLoaded(true);
        }
    }, []);

    // Load PDF document
    useEffect(() => {
        if (!pdfJsLoaded) return;

        const loadPdf = async () => {
            try {
                const pdfjsLib = (window as any).pdfjsLib;
                const loadingTask = pdfjsLib.getDocument('/catalog_output.pdf');
                const doc = await loadingTask.promise;
                setPdfDoc(doc);
                setNumPages(doc.numPages);
                setIsLoading(false);
            } catch (err) {
                console.error('Error loading PDF:', err);
                setIsLoading(false);
            }
        };

        loadPdf();
    }, [pdfJsLoaded]);

    const handlePageFlip = useCallback((e: any) => {
        setCurrentPage(e.data);
    }, []);

    const goToPrevPage = () => {
        if (bookRef.current) {
            bookRef.current.pageFlip().flipPrev();
        }
    };

    const goToNextPage = () => {
        if (bookRef.current) {
            bookRef.current.pageFlip().flipNext();
        }
    };

    const handleDownload = () => {
        const link = document.createElement('a');
        link.href = '/catalog_output.pdf';
        link.download = 'Catalogue_Technique.pdf';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    if (isLoading) {
        return (
            <div className="h-full flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-900">
                <div className="text-center">
                    <Loader2 className="animate-spin text-indigo-400 mx-auto mb-4\" size={48} />
                    <p className="text-white font-bold">Chargement du catalogue...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="h-full min-h-0 flex flex-col bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-900 relative overflow-hidden">
            {/* Background decoration */}
            <div className="absolute inset-0 opacity-10">
                <div className="absolute top-0 left-0 w-96 h-96 bg-indigo-500 rounded-full blur-[150px]" />
                <div className="absolute bottom-0 right-0 w-96 h-96 bg-purple-500 rounded-full blur-[150px]" />
            </div>

            {/* Header with Download Button */}
            <div className="relative z-10 p-6 flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-indigo-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-indigo-500/30">
                        <BookOpen size={24} />
                    </div>
                    <div>
                        <h2 className="text-xl font-bold text-white">Catalogue Technique</h2>
                        <p className="text-sm text-indigo-300">{numPages} pages</p>
                    </div>
                </div>
                <button
                    onClick={handleDownload}
                    className="bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-3 rounded-xl text-sm font-bold flex items-center gap-2 transition-all shadow-lg shadow-indigo-500/30 hover:shadow-indigo-500/50"
                >
                    <Download size={18} />
                    Télécharger PDF
                </button>
            </div>

            {/* Flipbook Container */}
            <div className="flex-1 min-h-0 relative z-10 flex items-center justify-center px-8 py-4">
                {/* Left Arrow */}
                <button
                    onClick={goToPrevPage}
                    disabled={currentPage <= 0}
                    className={clsx(
                        "absolute left-6 z-20 w-14 h-14 rounded-full flex items-center justify-center transition-all shadow-lg",
                        currentPage <= 0
                            ? "bg-white/10 text-slate-500 cursor-not-allowed"
                            : "bg-white/20 backdrop-blur-sm text-white hover:bg-white/30 cursor-pointer hover:scale-110"
                    )}
                >
                    <ChevronLeft size={28} />
                </button>

                {/* Book */}
                {pdfDoc && numPages > 0 && (
                    <div className="w-full h-full max-w-[720px] max-h-[640px] flex items-center justify-center">
                        <HTMLFlipBook
                            ref={bookRef}
                            width={360}
                            height={520}
                            size="stretch"
                            minWidth={280}
                            maxWidth={520}
                            minHeight={360}
                            maxHeight={640}
                            showCover={true}
                            mobileScrollSupport={true}
                            onFlip={handlePageFlip}
                            className="shadow-2xl"
                            style={{}}
                            startPage={0}
                            drawShadow={true}
                            flippingTime={600}
                            usePortrait={false}
                            startZIndex={0}
                            autoSize={true}
                            maxShadowOpacity={0.5}
                            showPageCorners={true}
                            disableFlipByClick={false}
                            swipeDistance={30}
                            clickEventForward={true}
                            useMouseEvents={true}
                        >
                            {Array.from({ length: numPages }, (_, i) => (
                                <Page key={i} pageNum={i + 1} pdfDoc={pdfDoc} scale={1.4} />
                            ))}
                        </HTMLFlipBook>
                    </div>
                )}

                {/* Right Arrow */}
                <button
                    onClick={goToNextPage}
                    disabled={currentPage >= numPages - 1}
                    className={clsx(
                        "absolute right-6 z-20 w-14 h-14 rounded-full flex items-center justify-center transition-all shadow-lg",
                        currentPage >= numPages - 1
                            ? "bg-white/10 text-slate-500 cursor-not-allowed"
                            : "bg-white/20 backdrop-blur-sm text-white hover:bg-white/30 cursor-pointer hover:scale-110"
                    )}
                >
                    <ChevronRight size={28} />
                </button>
            </div>

            {/* Page Counter */}
            <div className="relative z-10 p-6 flex justify-center shrink-0">
                <div className="bg-white/10 backdrop-blur-sm px-6 py-3 rounded-full flex items-center gap-4">
                    <span className="text-indigo-300 text-sm font-medium">Page</span>
                    <span className="text-white font-bold text-lg">{currentPage + 1}</span>
                    <span className="text-indigo-400">/</span>
                    <span className="text-indigo-300 font-bold text-lg">{numPages}</span>
                </div>
            </div>
        </div>
    );
};

const ReportPreview = ({ module }: { module: any }) => (
    <div className="h-full flex items-center justify-center p-12 bg-slate-50/50">
        <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="w-full max-w-lg aspect-[1/1.41] bg-white border border-slate-200 rounded-[24px] p-10 relative flex flex-col shadow-xl shadow-slate-200/50">
            <div className="absolute top-8 right-8 text-[9px] font-bold text-slate-300 uppercase tracking-widest">Ref: #RB-2025-X</div>
            <div className="flex items-center gap-5 mb-10 border-b border-slate-100 pb-8">
                <div className="w-12 h-12 bg-indigo-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-indigo-200">
                    <FileSearch size={24} />
                </div>
                <div>
                    <h1 className="text-xl font-black text-slate-900 uppercase tracking-tight">{module.title}</h1>
                    <p className="text-xs text-slate-400 font-bold mt-0.5">{module.file}</p>
                </div>
            </div>
            <div className="space-y-6 flex-1 opacity-50">
                <div className="h-3 bg-slate-100 rounded-full w-3/4" />
                <div className="h-3 bg-slate-100 rounded-full w-1/2" />
                <div className="py-6 space-y-4">
                    <div className="h-24 bg-slate-50 rounded-2xl border border-slate-100" />
                    <div className="h-24 bg-slate-50 rounded-2xl border border-slate-100" />
                </div>
            </div>
            <div className="mt-auto pt-8 border-t border-slate-50 text-center">
                <button className="w-full bg-slate-900 text-white py-3 rounded-xl text-xs font-bold flex items-center justify-center gap-2 hover:bg-indigo-600 transition-colors">
                    <Download size={14} /> TÉLÉCHARGER LE PDF
                </button>
            </div>
        </motion.div>
    </div>
);

const ModuleLoadingView = ({ module, progress }: { module: any; progress: number }) => {
    const meta = MODULE_LOADING_META[module.type] || {
        kicker: "Traitement en cours",
        description: "Préparation des livrables, veuillez patienter.",
        bullets: ["Analyse", "Génération", "Vérification"],
        accent: "from-indigo-600 via-violet-600 to-fuchsia-600",
        glow: "bg-fuchsia-500",
    };
    const Icon = module.icon;
    const safeProgress = Math.min(100, Math.max(0, progress));

    return (
        <div className="h-full w-full flex items-center justify-center p-10 bg-slate-50">
            <div className="w-full max-w-3xl bg-white border border-slate-200 rounded-[32px] overflow-hidden shadow-xl shadow-slate-200/50">
                <div className={clsx("p-10 text-white relative overflow-hidden bg-gradient-to-br", meta.accent)}>
                    <div className={clsx("absolute -top-20 -right-20 w-48 h-48 rounded-full blur-[80px] opacity-40", meta.glow)} />
                    <div className="relative z-10 flex items-start gap-5">
                        <div className="w-14 h-14 bg-white/15 rounded-2xl flex items-center justify-center border border-white/20">
                            <Icon size={28} />
                        </div>
                        <div>
                            <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/70 mb-2">{meta.kicker}</div>
                            <h3 className="text-2xl font-black tracking-tight">{module.title}</h3>
                            <p className="text-white/90 mt-2 max-w-xl">{meta.description}</p>
                        </div>
                    </div>
                </div>
                <div className="p-8">
                    <div className="flex items-center gap-3 mb-6">
                        <Loader2 className="animate-spin text-indigo-600" size={20} />
                        <span className="text-sm font-bold text-slate-700">{module.statusText}</span>
                    </div>
                    <div className="h-2 bg-slate-100 rounded-full overflow-hidden mb-6">
                        <div className="h-full bg-indigo-600 animate-[progress_1.2s_ease-in-out_infinite]" style={{ width: "35%" }} />
                    </div>
                    <div className="grid grid-cols-3 gap-3">
                        {meta.bullets.map((item) => (
                            <div key={item} className="bg-slate-50 border border-slate-100 rounded-xl px-4 py-3 text-xs font-bold text-slate-600 text-center">
                                {item}
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};

// ==========================================
// 3. MAIN WORKFLOW PAGE
// ==========================================

export default function FactoryCopilot() {
    const router = useRouter();
    const [status, setStatus] = useState<'idle' | 'uploading' | 'processing' | 'finished'>('idle');
    const [currentModule, setCurrentModule] = useState(0);
    const [selectedModule, setSelectedModule] = useState(0);
    const [subStep, setSubStep] = useState(0);
    const [artifacts, setArtifacts] = useState<number[]>([]);

    // THIS HOLDS THE REAL BACKEND DATA
    const [extractedData, setExtractedData] = useState<any>(null);
    const [module4Data, setModule4Data] = useState<any>(null);
    const [module4Loading, setModule4Loading] = useState(false);
    const [tcoData, setTcoData] = useState<any>(null);
    const [tcoLoading, setTcoLoading] = useState(false);
    const [businessPlanData, setBusinessPlanData] = useState<any>(null);
    const [pitchDeckData, setPitchDeckData] = useState<any>(null);
    const [businessPlanLoading, setBusinessPlanLoading] = useState(false);

    // Animate loading progress while a module is running
    useEffect(() => {
        if (status === 'processing' && !artifacts.includes(currentModule)) {
            const timer = setTimeout(() => {
                setSubStep(s => (s + 1) % 5);
            }, 800);
            return () => clearTimeout(timer);
        }
    }, [status, currentModule, subStep, artifacts]);

    // ----------------------------------------------------
    // REAL FILE UPLOAD HANDLER
    // ----------------------------------------------------
    const handleStart = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files || e.target.files.length === 0) return;

        const file = e.target.files[0];
        setStatus('processing');
        setArtifacts([]);
        setCurrentModule(0);
        setSelectedModule(0);
        setSubStep(0);
        setExtractedData(null);
        setModule4Data(null);
        setTcoData(null);
        setBusinessPlanData(null);
        setPitchDeckData(null);

        try {
            const formData = new FormData();
            formData.append('file', file);

            const module1Res = await fetch(`${API_BASE}/api/module1/process`, {
                method: 'POST',
                body: formData
            });
            const module1Json = await module1Res.json();
            if (!module1Res.ok) throw new Error(module1Json?.error || 'Module 1 failed');

            const module1Data = module1Json?.data || module1Json;
            setExtractedData(module1Data);
            setArtifacts(prev => [...new Set([...prev, 0])]);

            setStatus('processing');
            setCurrentModule(1);
            setSelectedModule(1);
            setSubStep(0);

            setModule4Loading(true);
            const module4Res = await fetch(`${API_BASE}/api/module4/enrich`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(module1Data)
            });
            const module4Json = await module4Res.json();
            if (!module4Res.ok) throw new Error(module4Json?.error || 'Module 4 failed');
            setModule4Data(module4Json);
            setModule4Loading(false);
            setArtifacts(prev => [...new Set([...prev, 1])]);
            setCurrentModule(2);
            setSelectedModule(2);
            setSubStep(0);

            setTcoLoading(true);
            const module6Res = await fetch(`${API_BASE}/api/module6/tco-from-sourcing`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(module4Json)
            });
            const module6Json = await module6Res.json();
            if (!module6Res.ok) throw new Error(module6Json?.error || 'Module 6 failed');
            setTcoData(module6Json);
            setTcoLoading(false);
            setArtifacts(prev => [...new Set([...prev, 2])]);
            setCurrentModule(3);
            setSelectedModule(3);
            setSubStep(0);

            setBusinessPlanLoading(true);
            const businessPlanRes = await fetch(`${API_BASE}/api/module7/business-plan`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(module6Json)
            });
            const businessPlanJson = await businessPlanRes.json();
            if (!businessPlanRes.ok) throw new Error(businessPlanJson?.error || 'Business Plan failed');
            setBusinessPlanData(businessPlanJson);

            const pitchDeckRes = await fetch(`${API_BASE}/api/module7/pitch-deck`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(module6Json)
            });
            const pitchDeckJson = await pitchDeckRes.json();
            if (!pitchDeckRes.ok) throw new Error(pitchDeckJson?.error || 'Pitch Deck failed');
            setPitchDeckData(pitchDeckJson);
            setBusinessPlanLoading(false);
            setArtifacts(prev => [...new Set([...prev, 3])]);
            setStatus('finished');
        } catch (error) {
            console.error("❌ Workflow error:", error);
            setModule4Loading(false);
            setTcoLoading(false);
            setBusinessPlanLoading(false);
            setStatus('idle');
        }
    };

    const regenerateOne = (idx: number) => {
        setArtifacts(prev => prev.filter(i => i !== idx));
        setCurrentModule(idx);
        setSelectedModule(idx);
        setSubStep(0);
        setStatus('processing');
    };

    const regenerateAll = () => {
        setArtifacts([]);
        setCurrentModule(0);
        setSelectedModule(0);
        setSubStep(0);
        setStatus('processing');
    };

    const handleModuleClick = (idx: number) => {
        if (artifacts.includes(idx) || status === 'finished' || idx === currentModule) {
            setSelectedModule(idx);
        }
    };

    const handleArtifactDownload = (idx: number) => {
        const moduleType = MODULES[idx]?.type;
        if (moduleType === 'businessplan') {
            const url = businessPlanData?.download_url;
            if (url) window.open(url, '_blank', 'noopener,noreferrer');
            return;
        }
        if (moduleType === 'catalogue') {
            window.open('/catalog_output.pdf', '_blank', 'noopener,noreferrer');
            return;
        }
        if (moduleType === 'pitchdeck') {
            const url = pitchDeckData?.pdf_download_url;
            if (url) window.open(url, '_blank', 'noopener,noreferrer');
        }
    };

    const handleDownloadAll = () => {
        const urls = [businessPlanData?.download_url, pitchDeckData?.pdf_download_url, '/catalog_output.pdf'];
        urls.forEach((url) => {
            if (url) window.open(url, '_blank', 'noopener,noreferrer');
        });
    };

    const selectedModuleItem = MODULES[selectedModule];
    const activeStagePrimary = MODULES[currentModule];
    const overallProgress = Math.round(((currentModule * 4 + subStep) / (MODULES.length * 4)) * 100);
    const isSelectedProcessing = status === 'processing' && selectedModule === currentModule && !artifacts.includes(currentModule);
    const isSelectedDone = artifacts.includes(selectedModule) || status === 'finished' || selectedModule < currentModule;
    const selectedProgress = isSelectedProcessing ? (subStep / 4) * 100 : isSelectedDone ? 100 : 0;

    return (
        <>
            <style>{fontStyle}</style>

            <div className="flex h-screen bg-[#F8FAFC] overflow-hidden font-sans text-slate-900 selection:bg-indigo-100">

                {/* LEFT SIDEBAR */}
                <aside className="w-80 bg-white border-r border-slate-200 flex flex-col z-20 shadow-[4px_0_24px_rgba(0,0,0,0.02)]">
                    <div className="p-8 h-24 border-b border-slate-100 flex items-center gap-4">
                        <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-indigo-200">
                            <Building2 size={20} />
                        </div>
                        <div>
                            <span className="font-extrabold text-lg text-slate-900 tracking-tight block">RIBIF IA</span>
                            <div className="text-[10px] text-indigo-600 font-bold uppercase tracking-wider">Manager v5.0</div>
                        </div>
                    </div>
                    <div className="flex-1 overflow-y-auto p-6 space-y-2">
                        <div className="px-2 py-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest flex justify-between">
                            Étapes du Workflow
                            {status === 'finished' && <RefreshCw size={12} className="cursor-pointer hover:text-indigo-600 transition-colors" onClick={regenerateAll} />}
                        </div>
                        {MODULES.map((m, idx) => {
                            const isDone = artifacts.includes(idx);
                            const isActive = selectedModule === idx;
                            const isAvailable = isDone || status === 'finished' || idx === currentModule;
                            return (
                                <button
                                    key={m.id}
                                    onClick={() => handleModuleClick(idx)}
                                    disabled={!isAvailable}
                                    className={clsx(
                                        "w-full flex items-center gap-4 p-4 rounded-[16px] transition-all text-left relative overflow-hidden group",
                                        isActive ? "bg-indigo-50 border border-indigo-100" : "hover:bg-slate-50 border border-transparent",
                                        !isAvailable && "opacity-50 cursor-not-allowed"
                                    )}
                                >
                                    {isActive && <div className="absolute left-0 top-0 bottom-0 w-1 bg-indigo-600" />}
                                    <div className={clsx("w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border",
                                        isDone ? "bg-emerald-50 text-emerald-600 border-emerald-100" :
                                            isActive ? "bg-indigo-600 text-white border-indigo-600" :
                                                "bg-white text-slate-400 border-slate-200"
                                    )}>
                                        {isDone ? <Check size={16} strokeWidth={3} /> : <m.icon size={16} />}
                                    </div>
                                    <div className={clsx("text-sm font-bold truncate", isActive ? "text-indigo-900" : "text-slate-600 group-hover:text-slate-900")}>{m.title}</div>
                                </button>
                            );
                        })}
                    </div>
                    {status === 'processing' && (
                        <div className="p-6 border-t border-slate-100 bg-white">
                            <motion.div initial={{ y: 12, opacity: 0 }} animate={{ y: 0, opacity: 1 }} className="bg-slate-900 text-white px-5 py-4 rounded-2xl flex items-center gap-4 shadow-lg shadow-slate-300/40">
                                <div className="relative">
                                    <div className="absolute inset-0 bg-indigo-500 rounded-full animate-ping opacity-75"></div>
                                    <div className="relative w-9 h-9 bg-indigo-600 rounded-full flex items-center justify-center text-white border border-indigo-400">
                                        <Sparkles size={14} />
                                    </div>
                                </div>
                                <div className="flex-1">
                                    <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest leading-none mb-1">Progression globale</div>
                                    <div className="text-sm font-bold text-white">{activeStagePrimary?.statusText || "Traitement en cours"}</div>
                                    <div className="mt-2 h-1.5 bg-white/10 rounded-full overflow-hidden">
                                        <div className="h-full bg-indigo-500" style={{ width: `${Math.max(overallProgress, 6)}%` }} />
                                    </div>
                                </div>
                                <div className="text-base font-black text-indigo-300 font-mono">
                                    {overallProgress}%
                                </div>
                            </motion.div>
                        </div>
                    )}
                </aside>

                {/* CENTER PANEL */}
                <main className="flex-1 flex flex-col relative overflow-hidden bg-[#F8FAFC]">
                    <header className="h-24 border-b border-slate-200 flex items-center justify-between px-10 z-10 bg-white/80 backdrop-blur-md">
                        <div className="flex items-center gap-4">
                            <div className={`h-2.5 w-2.5 rounded-full ring-4 ring-opacity-20 ${status === 'processing' || status === 'uploading' ? 'bg-indigo-500 ring-indigo-500 animate-pulse' : 'bg-slate-300 ring-slate-300'}`} />
                            <h2 className="text-xs font-extrabold text-slate-500 uppercase tracking-widest">
                                {status === 'idle' ? "Prêt" : status === 'uploading' ? "Téléchargement & Analyse..." : status === 'finished' ? "Terminé" : "Traitement IA en cours"}
                            </h2>
                        </div>
                        <div className="flex gap-4">
                            {status === 'finished' && (
                                <button onClick={regenerateAll} className="bg-white border border-slate-200 hover:border-indigo-300 text-slate-600 px-6 py-2.5 rounded-full text-xs font-bold flex items-center gap-2 transition-all shadow-sm">
                                    <RefreshCw size={14} /> Relancer
                                </button>
                            )}
                            <button onClick={() => router.push('/twin')} className="bg-slate-900 hover:bg-indigo-600 text-white px-6 py-2.5 rounded-full text-xs font-bold flex items-center gap-2 transition-all shadow-lg shadow-indigo-200/50">
                                <BrainCircuit size={16} className="text-indigo-300" /> Jumeau Numérique
                            </button>
                        </div>
                    </header>

                    <div className="flex-1 p-6 relative overflow-y-auto">
                        {status === 'idle' ? (
                            <div className="h-full flex items-center justify-center p-10">
                                <label className="w-full max-w-4xl aspect-[16/9] bg-white border-2 border-dashed border-slate-300 rounded-[32px] flex flex-col items-center justify-center gap-8 cursor-pointer hover:border-indigo-500 hover:bg-indigo-50/30 transition-all group relative overflow-hidden">
                                    <input type="file" className="hidden" accept=".pdf" onChange={handleStart} />

                                    <div className="absolute inset-0 opacity-[0.03]" style={{ backgroundImage: 'radial-gradient(#4f46e5 1px, transparent 1px)', backgroundSize: '24px 24px' }} />

                                    <div className="w-24 h-24 bg-indigo-50 rounded-[2rem] flex items-center justify-center text-indigo-600 group-hover:scale-110 group-hover:bg-indigo-600 group-hover:text-white transition-all duration-300 shadow-sm z-10">
                                        <Upload size={32} />
                                    </div>
                                    <div className="text-center z-10 max-w-md">
                                        <h3 className="text-2xl font-black text-slate-800 mb-3">Initialiser le Projet</h3>
                                        <p className="text-slate-500 font-medium leading-relaxed">Glissez votre cahier des charges (PDF) pour lancer l'analyse IA.</p>
                                    </div>
                                    <div className="px-8 py-3 bg-slate-900 text-white rounded-xl text-sm font-bold z-10 group-hover:bg-indigo-600 transition-colors shadow-lg shadow-slate-200">
                                        Sélectionner un fichier
                                    </div>
                                </label>
                            </div>
                        ) : status === 'uploading' ? (
                            <div className="h-full w-full flex flex-col items-center justify-center">
                                <Loader2 size={48} className="text-indigo-600 animate-spin mb-4" />
                                <h3 className="text-xl font-bold text-slate-800">Analyse du PDF par IA</h3>
                                <p className="text-slate-500">Cela peut prendre quelques secondes.</p>
                            </div>
                        ) : (
                            <div className="h-full w-full bg-white rounded-[32px] border border-slate-200 shadow-sm overflow-auto relative">
                                <AnimatePresence mode="wait">
                                    <motion.div key={selectedModule} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="h-full w-full">
                                        {isSelectedProcessing ? (
                                            <ModuleLoadingView module={selectedModuleItem} progress={selectedProgress} />
                                        ) : (
                                            <>
                                                {selectedModuleItem.type === 'specs' && <SpecsView data={extractedData} />}
                                                {selectedModuleItem.type === 'plans' && <PlansView />}
                                                {selectedModuleItem.type === 'video' && <VideoView progress={selectedProgress} />}
                                                {selectedModuleItem.type === 'sourcing' && <SourcingView progress={selectedProgress} data={extractedData} module4Data={module4Data} loading={module4Loading} />}
                                                {selectedModuleItem.type === 'tco' && <TcoView data={tcoData} loading={tcoLoading} />}
                                                {selectedModuleItem.type === 'businessplan' && <BusinessPlanView businessPlanData={businessPlanData} pitchDeckData={pitchDeckData} loading={businessPlanLoading} />}
                                                {selectedModuleItem.type === 'catalogue' && <CatalogueTechniqueView />}
                                            </>
                                        )}
                                    </motion.div>
                                </AnimatePresence>

                            </div>
                        )}
                    </div>
                </main>

                {/* RIGHT SIDEBAR (Artifacts) */}
                <aside className="w-80 bg-white border-l border-slate-200 flex flex-col z-20 shadow-[-4px_0_24px_rgba(0,0,0,0.02)]">
                    <div className="h-24 p-8 border-b border-slate-100 flex items-center justify-between">
                        <h2 className="text-xs font-extrabold text-slate-500 uppercase tracking-widest">Livrables</h2>
                        <span className="bg-slate-100 text-slate-600 px-2 py-1 rounded-md text-[10px] font-bold">{artifacts.length} fichiers</span>
                    </div>
                    <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-slate-50/50">
                        <AnimatePresence>
                            {artifacts.length === 0 && (
                                <div className="h-40 border-2 border-dashed border-slate-200 rounded-2xl flex flex-col items-center justify-center p-6 text-center">
                                    <Info size={24} className="mb-2 text-slate-300" />
                                    <p className="text-xs font-bold text-slate-400">En attente de génération...</p>
                                </div>
                            )}
                            {artifacts.slice().reverse().map((idx) => (
                                <motion.div key={idx} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                                    className={clsx("bg-white rounded-[20px] border p-4 transition-all group shadow-sm hover:shadow-md", selectedModule === idx ? "border-indigo-400 ring-4 ring-indigo-50" : "border-slate-200")}>
                                    <div className="flex justify-between items-start mb-3">
                                        <div onClick={() => handleModuleClick(idx)} className="w-10 h-10 bg-indigo-50 rounded-full flex items-center justify-center text-indigo-600 group-hover:bg-indigo-600 group-hover:text-white transition-colors cursor-pointer">
                                            <Eye size={18} />
                                        </div>
                                        <div className="flex gap-1">
                                            <button onClick={() => regenerateOne(idx)} className="w-8 h-8 flex items-center justify-center rounded-full text-slate-400 hover:bg-slate-100 hover:text-indigo-600 transition-colors">
                                                <RefreshCw size={14} />
                                            </button>
                                            <button
                                                onClick={() => handleArtifactDownload(idx)}
                                                disabled={MODULES[idx].type !== 'businessplan' && MODULES[idx].type !== 'catalogue' && MODULES[idx].type !== 'pitchdeck'}
                                                className={clsx(
                                                    "w-8 h-8 flex items-center justify-center rounded-full transition-colors",
                                                    (MODULES[idx].type !== 'businessplan' && MODULES[idx].type !== 'catalogue' && MODULES[idx].type !== 'pitchdeck')
                                                        ? "text-slate-300 cursor-not-allowed"
                                                        : "text-slate-400 hover:bg-slate-100 hover:text-indigo-600"
                                                )}
                                            >
                                                <Download size={14} />
                                            </button>
                                        </div>
                                    </div>
                                    <div className="text-xs font-extrabold text-slate-800 truncate mb-2">{MODULES[idx].file}</div>
                                    <div className="flex items-center gap-1.5">
                                        <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                                        <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wide">Prêt à l'envoi</span>
                                    </div>
                                </motion.div>
                            ))}
                        </AnimatePresence>
                    </div>
                    {status === 'finished' && (
                        <div className="p-6 border-t border-slate-100 bg-white">
                            <button
                                onClick={handleDownloadAll}
                                className="w-full bg-indigo-600 text-white py-4 rounded-xl font-bold text-xs flex items-center justify-center gap-2 hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-200"
                            >
                                <Download size={16} /> TOUT TÉLÉCHARGER
                            </button>
                        </div>
                    )}
                </aside>
            </div>
        </>
    );
}