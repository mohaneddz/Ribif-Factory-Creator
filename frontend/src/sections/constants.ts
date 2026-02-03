import { BookOpen, Box, BrainCircuit, Briefcase, Calculator, FileText, Globe, Layers, Mail, Presentation, Video } from "lucide-react";

export const fontStyle = `
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

export const API_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "";

export const MODULES = [
    { id: 1, title: "Analyse Specs", icon: FileText, file: "Specs_V1.pdf", type: "specs", statusText: "Extraction des données..." },
    { id: 2, title: "Sourcing Global", icon: Globe, file: "Liste_Sourcing.xlsx", type: "sourcing", statusText: "Recherche fournisseurs..." },
    { id: 3, title: "Email Center", icon: Mail, file: "Email_Negotiations.md", type: "email", statusText: "Préparation des emails..." },
    { id: 4, title: "Analyse TCO", icon: Calculator, file: "Rapport_TCO.json", type: "tco", statusText: "Calcul des coûts..." },
    { id: 5, title: "Business Plan", icon: Briefcase, file: "Business_Plan.xlsx", type: "businessplan", statusText: "Génération du plan..." },
    { id: 6, title: "Catalogue Technique", icon: BookOpen, file: "Catalogue_Produits.pdf", type: "catalogue", statusText: "Génération du catalogue..." },
    { id: 7, title: "2D Layout Design", icon: Layers, file: "layout_square.dxf", type: "layout2d", statusText: "Génération du layout 2D..." },
    { id: 8, title: "3D Model Generation", icon: Box, file: "factory_model.glb", type: "model3d", statusText: "Modélisation 3D..." },
    { id: 9, title: "Video Model Presentation", icon: Video, file: "Presentation_HD.mp4", type: "video", statusText: "Rendu vidéo HD..." },
    { id: 10, title: "Digital Twin", icon: BrainCircuit, file: "Digital_Twin_Live.json", type: "twin", statusText: "Initialisation du Jumeau Numérique..." }
];

export const MODULE_LOADING_META: Record<
  string,
  { kicker: string; description: string; bullets: string[]; accent: string; glow: string }
> = {
  specs: {
    kicker: "Lecture du cahier des charges",
    description: "Extraction des infos clés : contraintes, matières, capacités, exigences.",
    bullets: ["Lecture & synthèse", "Extraction champs clés", "Structuration JSON"],
    accent: "from-indigo-600 via-violet-600 to-fuchsia-600",
    glow: "bg-fuchsia-500",
  },
  layout2d: {
    kicker: "Plan 2D",
    description: "Génération d’un plan 2D simplifié basé sur les zones et l’implantation.",
    bullets: ["Définition des zones", "Placement de base", "Export 2D"],
    accent: "from-emerald-600 via-teal-600 to-cyan-600",
    glow: "bg-cyan-500",
  },
  model3d: {
    kicker: "Modèle 3D",
    description: "Construction d’un volume 3D indicatif pour visualisation.",
    bullets: ["Volume indicatif", "Assemblage simple", "Export 3D"],
    accent: "from-slate-700 via-slate-800 to-indigo-800",
    glow: "bg-indigo-400",
  },
  video: {
    kicker: "Rendu immersif",
    description: "Rendu de visualisation basique à partir de la scène 3D.",
    bullets: ["Rendu simple", "Quelques vues", "Export vidéo"],
    accent: "from-amber-500 via-orange-500 to-rose-500",
    glow: "bg-rose-500",
  },
  email: {
    kicker: "Négociation email",
    description: "Génération d’emails de contact et suivi des réponses.",
    bullets: ["Brouillon d’email", "Suivi & relance", "Résumé des échanges"],
    accent: "from-sky-600 via-blue-600 to-indigo-600",
    glow: "bg-blue-500",
  },
  sourcing: {
    kicker: "Sourcing",
    description: "Recherche de fournisseurs + shortlist simple alignée aux besoins.",
    bullets: ["Recherche fournisseurs", "Shortlist", "Liens & contacts"],
    accent: "from-sky-600 via-blue-600 to-indigo-600",
    glow: "bg-blue-500",
  },
  tco: {
    kicker: "Analyse des coûts",
    description: "Estimation des coûts principaux et synthèse par poste.",
    bullets: ["CAPEX estimatif", "OPEX estimatif", "Tableau récapitulatif"],
    accent: "from-slate-700 via-slate-800 to-indigo-800",
    glow: "bg-indigo-400",
  },
  businessplan: {
    kicker: "Plan d'affaires",
    description: "Structuration d’un business plan court avec chiffres clés.",
    bullets: ["Résumé & pitch", "Hypothèses clés", "Chiffres principaux"],
    accent: "from-emerald-600 via-green-600 to-lime-600",
    glow: "bg-lime-400",
  },  pitchdeck: {
    kicker: "Pitch Deck",
    description: "Présentation PDF pour investisseurs avec les éléments clés du projet.",
    bullets: ["Slides automatiques", "Chiffres clés", "Export PDF"],
    accent: "from-purple-600 via-fuchsia-600 to-pink-600",
    glow: "bg-pink-400",
  },  catalogue: {
    kicker: "Catalogue technique",
    description: "Compilation des éléments techniques dans un PDF propre.",
    bullets: ["Compilation contenu", "Mise en page simple", "Export PDF"],
    accent: "from-indigo-700 via-blue-700 to-slate-900",
    glow: "bg-indigo-300",
  },
  twin: {
    kicker: "Simulation & Monitoring",
    description: "Tableau de bord simple avec indicateurs et courbes basiques.",
    bullets: ["KPIs basiques", "Graphiques simples", "Données simulées"],
    accent: "from-indigo-600 via-violet-600 to-fuchsia-600",
    glow: "bg-fuchsia-500",
  },
};


export const MOCK_TCO_DATA = {
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
        { "nom_materiau": "Polyuréthane (PU)", "total_tco": 526500000.0, "unit_price": 3500 },
        { "nom_materiau": "Polyurée (2K)", "total_tco": 394875000.0, "unit_price": 4800 },
        { "nom_materiau": "Résines époxy", "total_tco": 102060000.0, "unit_price": 2900 },
        { "nom_materiau": "UTG (verre flexible)", "total_tco": 530550000.0, "unit_price": 28000 }
    ]
};

export const BUSINESS_PLAN_TABS = [
    { id: 'bmc', label: 'Business Model Canvas', shortLabel: 'BMC' },
    { id: 'capex', label: 'CapEx', shortLabel: 'CapEx' },
    { id: 'opex', label: 'OpEx', shortLabel: 'OpEx' },
    { id: 'pricing', label: 'Pricing', shortLabel: 'Pricing' },
    { id: 'roi', label: 'Analyse ROI', shortLabel: 'ROI' },
];

// Mock data for Business Plan sections
export const MOCK_BUSINESS_PLAN_DATA = {
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

export const MOCK_PITCH_DECK = {
    filename: "PitchDeck_RIBIF_Project.pptx",
    slides_count: 10,
    size_mb: 2.4,
    created_at: "2025-12-28"
};

export const MOCK_EXTRACTED_DATA = {
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

export const MOCK_MODULE4_DATA = {
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
                    email_address: "blahaibrahim2005@gmail.com",
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
                    email_address: "blahaibrahim2005@gmail.com",
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
                    email_address: "blahaibrahim2005@gmail.com",
                    customs_algeria_info: "Inspection préalable conseillée",
                    relevance_score: 0.83
                }
            ]
        }
    ]
};

export const MOCK_BUSINESS_PLAN_RESPONSE = {
    filename: "Business_Plan_RIBIF.pdf",
    download_url: "/pdf_dash.pdf"
};

export const MOCK_PITCH_DECK_RESPONSE = {
    ...MOCK_PITCH_DECK,
    pdf_filename: "PitchDeck_RIBIF_Project.pdf",
    pdf_download_url: "/pdf_dash.pdf",
    data: { slides: Array.from({ length: 10 }, (_, i) => ({ page: i + 1 })) }
};
