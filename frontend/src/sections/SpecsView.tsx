import { Building2, Sparkles } from "lucide-react";
import clsx from "clsx";

export const SpecsView = ({ data }: any) => {
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
        <div className="h-full flex flex-col overflow-hidden bg-slate-50 dark:bg-[#0b0c10] transition-colors">
            {/* Fixed Header */}
            <div className="p-8 pb-4 border-b border-slate-100 dark:border-white/5 bg-white dark:bg-[#0b0c10] shrink-0 transition-colors">
                <div className="flex items-center gap-6">
                    <div className="w-16 h-16 bg-indigo-50 dark:bg-indigo-500/10 rounded-2xl flex items-center justify-center text-indigo-600 dark:text-indigo-400 border border-indigo-100 dark:border-indigo-500/20">
                        <Sparkles size={28} />
                    </div>
                    <div>
                        <h3 className="text-3xl font-extrabold text-slate-800 dark:text-white">Données Projet</h3>
                        <p className="text-base font-medium text-slate-500 dark:text-slate-400">Extraction automatique du cahier des charges</p>
                    </div>
                </div>
            </div>

            {/* Scrollable Content */}
            <div className="flex-1 overflow-y-auto p-8 pt-6 space-y-6">
                {/* Project Info Cards */}
                <div className="grid grid-cols-2 gap-6">
                    <div className="bg-white dark:bg-[#13141c] p-8 rounded-3xl border border-slate-200 dark:border-white/5 shadow-sm dark:shadow-none relative overflow-hidden group hover:border-indigo-300 dark:hover:border-indigo-500/50 transition-all">
                        <div className="absolute top-0 right-0 w-24 h-24 bg-slate-50 dark:bg-white/5 rounded-bl-[100px] -mr-4 -mt-4 transition-colors group-hover:bg-indigo-50 dark:group-hover:bg-indigo-500/10" />
                        <div className="relative z-10">
                            <div className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-2">Nom du Projet</div>
                            <div className="text-2xl font-bold text-slate-800 dark:text-white">{projectName}</div>
                            <div className="text-sm font-medium text-slate-500 dark:text-slate-400 mt-1">{companyName} ({info.raison_sociale || "N/A"})</div>
                        </div>
                    </div>

                    <div className="bg-white dark:bg-[#13141c] p-8 rounded-3xl border border-slate-200 dark:border-white/5 shadow-sm dark:shadow-none relative overflow-hidden group hover:border-indigo-300 dark:hover:border-indigo-500/50 transition-all">
                        <div className="absolute top-0 right-0 w-24 h-24 bg-slate-50 dark:bg-white/5 rounded-bl-[100px] -mr-4 -mt-4 transition-colors group-hover:bg-indigo-50 dark:group-hover:bg-indigo-500/10" />
                        <div className="relative z-10">
                            <div className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-2">Industrie</div>
                            <div className="text-2xl font-bold text-slate-800 dark:text-white">{industry}</div>
                            <div className="inline-block mt-2 px-3 py-1 rounded-full bg-indigo-50 dark:bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 text-xs font-bold uppercase">{type}</div>
                        </div>
                    </div>
                </div>

                {/* Description */}
                {description && (
                    <div className="bg-white dark:bg-[#13141c] p-6 rounded-3xl border border-slate-200 dark:border-white/5 shadow-sm dark:shadow-none">
                        <div className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-3">Description du Projet</div>
                        <p className="text-sm font-medium text-slate-600 dark:text-slate-300 leading-relaxed">{description}</p>
                    </div>
                )}

                {/* Objectives de Production - Main Section */}
                <div className="bg-indigo-600 dark:bg-indigo-600 p-8 rounded-3xl text-white relative overflow-hidden">
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
                    <div className="bg-white dark:bg-[#13141c] p-6 rounded-3xl border border-slate-200 dark:border-white/5 shadow-sm dark:shadow-none">
                        <div className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-3">Localisation</div>
                        <div className="space-y-2">
                            <div className="flex justify-between"><span className="text-sm text-slate-500 dark:text-slate-400">Zone</span><span className="text-sm font-bold text-slate-800 dark:text-white">{location.zone || "N/A"}</span></div>
                            <div className="flex justify-between"><span className="text-sm text-slate-500 dark:text-slate-400">Pays</span><span className="text-sm font-bold text-slate-800 dark:text-white">{location.pays || "N/A"}</span></div>
                            <div className="flex justify-between"><span className="text-sm text-slate-500 dark:text-slate-400">Échelle</span><span className="text-sm font-bold text-slate-800 dark:text-white">{info.taille_projet?.echelle || "N/A"}</span></div>
                        </div>
                    </div>
                    <div className="bg-white dark:bg-[#13141c] p-6 rounded-3xl border border-slate-200 dark:border-white/5 shadow-sm dark:shadow-none">
                        <div className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-3">Classification Danger</div>
                        <div className="mb-3">
                            <span className={clsx("px-3 py-1.5 rounded-full text-xs font-bold uppercase",
                                dangerClass.niveau_danger === "moyen" ? "bg-amber-50 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-100 dark:border-amber-500/20" :
                                    dangerClass.niveau_danger === "élevé" ? "bg-red-50 dark:bg-red-500/10 text-red-600 dark:text-red-400 border border-red-100 dark:border-red-500/20" :
                                        "bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-100 dark:border-emerald-500/20"
                            )}>{dangerClass.niveau_danger || "N/A"}</span>
                        </div>
                        <div className="flex flex-wrap gap-2">
                            {(dangerClass.type_dangers || []).map((d: string, i: number) => (
                                <span key={i} className="px-2 py-1 bg-slate-100 dark:bg-white/5 text-slate-600 dark:text-slate-400 rounded-lg text-xs font-medium">{d}</span>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Raw Materials Section */}
                {rawMaterials.length > 0 && (
                    <div className="bg-white dark:bg-[#13141c] p-6 rounded-3xl border border-slate-200 dark:border-white/5 shadow-sm dark:shadow-none">
                        <div className="flex justify-between items-center mb-4">
                            <div className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest">Matières Premières</div>
                            <span className="px-3 py-1 bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 rounded-full text-xs font-bold">{rawMaterials.length} matériaux</span>
                        </div>
                        <div className="max-h-64 overflow-y-auto space-y-3 pr-2">
                            {rawMaterials.map((mat: any, i: number) => (
                                <div key={i} className="p-4 bg-slate-50 dark:bg-white/5 rounded-xl border border-slate-100 dark:border-white/10 hover:border-indigo-200 dark:hover:border-indigo-500/50 transition-all">
                                    <div className="flex justify-between items-start mb-2">
                                        <div className="font-bold text-slate-800 dark:text-white">{mat.nom_materiau}</div>
                                        <span className="px-2 py-0.5 bg-white dark:bg-white/10 text-slate-500 dark:text-slate-400 rounded text-xs font-medium">{mat.categorie}</span>
                                    </div>
                                    <div className="text-xs text-slate-500 dark:text-slate-400 mb-2">{mat.type}</div>
                                    <div className="flex gap-4 text-xs">
                                        <span className="text-slate-600 dark:text-slate-300"><strong>Quantité:</strong> {mat.quantite_estimee?.valeur} {mat.quantite_estimee?.unite}/{mat.quantite_estimee?.periode}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Products Section */}
                {products.length > 0 && (
                    <div className="bg-white dark:bg-[#13141c] p-6 rounded-3xl border border-slate-200 dark:border-white/5 shadow-sm dark:shadow-none">
                        <div className="flex justify-between items-center mb-4">
                            <div className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest">Produits Fabriqués</div>
                            <span className="px-3 py-1 bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 rounded-full text-xs font-bold">{products.length} produits</span>
                        </div>
                        <div className="max-h-80 overflow-y-auto space-y-3 pr-2">
                            {products.map((prod: any, i: number) => (
                                <div key={i} className="p-4 bg-slate-50 dark:bg-white/5 rounded-xl border border-slate-100 dark:border-white/10 hover:border-emerald-200 dark:hover:border-emerald-500/50 transition-all">
                                    <div className="flex justify-between items-start mb-2">
                                        <div className="font-bold text-slate-800 dark:text-white">{prod.nom_produit}</div>
                                        <span className={clsx("px-2 py-0.5 rounded text-xs font-medium",
                                            prod.categorie === "finished" ? "bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400" : "bg-amber-50 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400"
                                        )}>{prod.categorie}</span>
                                    </div>
                                    <p className="text-xs text-slate-500 dark:text-slate-400 mb-2">{prod.description}</p>
                                    <div className="flex flex-wrap gap-2 mb-2">
                                        {(prod.specifications_techniques?.normes || []).map((n: string, j: number) => (
                                            <span key={j} className="px-2 py-0.5 bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 rounded text-xs font-medium">{n}</span>
                                        ))}
                                    </div>
                                    <div className="text-xs text-slate-600 dark:text-slate-400">
                                        <strong>Capacité:</strong> {prod.volume_production?.capacite} {prod.volume_production?.unite}/{prod.volume_production?.periode}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Machines with AI Generated Images */}
                {enrichedMachines.length > 0 && (
                    <div className="bg-white dark:bg-[#13141c] p-6 rounded-3xl border border-slate-200 dark:border-white/5 shadow-sm dark:shadow-none">
                        <div className="flex justify-between items-center mb-6">
                            <div className="flex items-center gap-3">
                                <div className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest">Machines Industrielles</div>
                                <span className="px-2 py-0.5 bg-purple-50 dark:bg-purple-500/10 text-purple-600 dark:text-purple-400 rounded text-[10px] font-bold">🤖 AI Generated</span>
                            </div>
                            {scrapingSummary && (
                                <span className={clsx(
                                    "px-3 py-1 rounded-full text-xs font-bold",
                                    scrapingSummary.successful_scrapes === scrapingSummary.total_machines
                                        ? "bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                                        : scrapingSummary.successful_scrapes > 0
                                            ? "bg-amber-50 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400"
                                            : "bg-red-50 dark:bg-red-500/10 text-red-600 dark:text-red-400"
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
                                    <div key={i} className="bg-slate-50 dark:bg-white/5 rounded-xl border border-slate-100 dark:border-white/10 overflow-hidden hover:border-purple-200 dark:hover:border-purple-500/50 hover:shadow-md transition-all">
                                        {/* Machine Image */}
                                        <div className="h-40 bg-gradient-to-br from-slate-100 to-slate-200 dark:from-white/5 dark:to-white/10 relative overflow-hidden">
                                            {hasImage ? (
                                                <img
                                                    src={machine.image_url}
                                                    alt={machine.nom_machine}
                                                    className="w-full h-full object-cover"
                                                />
                                            ) : (
                                                <div className="w-full h-full flex flex-col items-center justify-center text-slate-400 dark:text-slate-500">
                                                    <div className="w-12 h-12 bg-slate-200 dark:bg-white/10 rounded-xl flex items-center justify-center mb-2">
                                                        {hasError ? (
                                                            <span className="text-red-400">❌</span>
                                                        ) : (
                                                            <span className="text-slate-300 dark:text-slate-600">🔧</span>
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
                                            <div className="font-bold text-slate-800 dark:text-white mb-1 line-clamp-1">{machine.nom_machine}</div>
                                            <div className="text-xs text-slate-500 dark:text-slate-400 mb-2 line-clamp-1">{machine.type}</div>

                                            <div className="flex items-center gap-2 mb-3">
                                                <span className="px-2 py-0.5 bg-purple-50 dark:bg-purple-500/10 text-purple-600 dark:text-purple-400 rounded text-xs font-medium">
                                                    x{typeof machine.quantite_necessaire === 'object' ? machine.quantite_necessaire?.value : machine.quantite_necessaire || 1}
                                                </span>
                                                {machine.fabricant_recommande && (
                                                    <span className="px-2 py-0.5 bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 rounded text-xs font-medium truncate max-w-[120px]">
                                                        {typeof machine.fabricant_recommande === 'object' ? machine.fabricant_recommande?.value : machine.fabricant_recommande}
                                                    </span>
                                                )}
                                            </div>

                                            {/* Specifications */}
                                            {machine.specifications && (
                                                <div className="grid grid-cols-2 gap-1 text-[11px]">
                                                    {machine.specifications?.capacite && (
                                                        <div className="text-slate-600 dark:text-slate-400">
                                                            <span className="text-slate-400 dark:text-slate-600">Cap:</span> {typeof machine.specifications.capacite === 'object' ? machine.specifications.capacite.value : machine.specifications.capacite}
                                                        </div>
                                                    )}
                                                    {machine.specifications?.puissance && (
                                                        <div className="text-slate-600 dark:text-slate-400">
                                                            <span className="text-slate-400 dark:text-slate-600">Puis:</span> {typeof machine.specifications.puissance === 'object' ? machine.specifications.puissance.value : machine.specifications.puissance}
                                                        </div>
                                                    )}
                                                    {machine.performance?.rendement && (
                                                        <div className="text-slate-600 dark:text-slate-400">
                                                            <span className="text-slate-400 dark:text-slate-600">Rend:</span> {typeof machine.performance.rendement === 'object' ? `${(machine.performance.rendement.value * 100).toFixed(0)}%` : machine.performance.rendement}
                                                        </div>
                                                    )}
                                                    {machine.performance?.cadence && (
                                                        <div className="text-slate-600 dark:text-slate-400">
                                                            <span className="text-slate-400 dark:text-slate-600">Cad:</span> {typeof machine.performance.cadence === 'object' ? machine.performance.cadence.value : machine.performance.cadence}
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
                    <div className="bg-white dark:bg-[#13141c] p-6 rounded-3xl border border-slate-200 dark:border-white/5 shadow-sm dark:shadow-none">
                        <div className="flex justify-between items-center mb-4">
                            <div className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest">Processus de Production</div>
                            <span className="px-3 py-1 bg-sky-50 dark:bg-sky-500/10 text-sky-600 dark:text-sky-400 rounded-full text-xs font-bold">{process.length} étapes</span>
                        </div>
                        <div className="max-h-80 overflow-y-auto space-y-3 pr-2">
                            {process.map((step: any, i: number) => (
                                <div key={i} className="p-4 bg-slate-50 dark:bg-white/5 rounded-xl border border-slate-100 dark:border-white/10 hover:border-sky-200 dark:hover:border-sky-500/50 transition-all">
                                    <div className="flex items-center gap-3 mb-2">
                                        <span className="w-8 h-8 bg-sky-600 text-white rounded-full flex items-center justify-center text-xs font-bold">{step.numero_etape}</span>
                                        <div className="font-bold text-slate-800 dark:text-white">{step.nom_etape}</div>
                                        <span className="px-2 py-0.5 bg-sky-50 dark:bg-sky-500/10 text-sky-600 dark:text-sky-400 rounded text-xs font-medium">{step.type_operation}</span>
                                    </div>
                                    <p className="text-xs text-slate-500 dark:text-slate-400 mb-2">{step.description}</p>
                                    <div className="flex flex-wrap gap-1 mb-2">
                                        {(step.machines_utilisees || []).map((m: string, j: number) => (
                                            <span key={j} className="px-2 py-0.5 bg-white dark:bg-white/10 border border-slate-200 dark:border-white/10 text-slate-600 dark:text-slate-300 rounded text-xs">{m}</span>
                                        ))}
                                    </div>
                                    <div className="grid grid-cols-3 gap-2 text-xs text-slate-600 dark:text-slate-400">
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
                    <div className="bg-gradient-to-r from-indigo-600 to-purple-600 p-6 rounded-3xl text-white">
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
                        <div className="bg-white dark:bg-[#13141c] p-6 rounded-3xl border border-slate-200 dark:border-white/5 shadow-sm dark:shadow-none">
                            <div className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-4">Aspects Réglementaires</div>
                            <div className="space-y-4 max-h-64 overflow-y-auto pr-2">
                                {(reglementary.autorisations_requises || []).length > 0 && (
                                    <div>
                                        <div className="text-xs font-bold text-slate-600 dark:text-slate-400 mb-2">Autorisations Requises</div>
                                        <div className="space-y-1">
                                            {reglementary.autorisations_requises.slice(0, 5).map((a: string, i: number) => (
                                                <div key={i} className="text-xs text-slate-500 dark:text-slate-400 flex items-start gap-2">
                                                    <span className="w-1.5 h-1.5 bg-amber-400 rounded-full mt-1.5 shrink-0"></span>
                                                    {a}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                                {(reglementary.certifications || []).length > 0 && (
                                    <div>
                                        <div className="text-xs font-bold text-slate-600 dark:text-slate-400 mb-2">Certifications</div>
                                        <div className="flex flex-wrap gap-2">
                                            {reglementary.certifications.map((c: string, i: number) => (
                                                <span key={i} className="px-2 py-1 bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 rounded-lg text-xs font-medium">{c}</span>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Risks */}
                    {Object.keys(risks).length > 0 && (
                        <div className="bg-white dark:bg-[#13141c] p-6 rounded-3xl border border-slate-200 dark:border-white/5 shadow-sm dark:shadow-none">
                            <div className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-4">Analyse des Risques</div>
                            <div className="space-y-4 max-h-64 overflow-y-auto pr-2">
                                {(risks.risques_techniques || []).length > 0 && (
                                    <div>
                                        <div className="text-xs font-bold text-red-600 dark:text-red-400 mb-2">Risques Techniques</div>
                                        <div className="space-y-1">
                                            {risks.risques_techniques.slice(0, 3).map((r: string, i: number) => (
                                                <div key={i} className="text-xs text-slate-500 dark:text-slate-400 flex items-start gap-2">
                                                    <span className="w-1.5 h-1.5 bg-red-400 rounded-full mt-1.5 shrink-0"></span>
                                                    {r}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                                {(risks.strategies_mitigation || []).length > 0 && (
                                    <div>
                                        <div className="text-xs font-bold text-emerald-600 dark:text-emerald-400 mb-2">Stratégies de Mitigation</div>
                                        <div className="space-y-1">
                                            {risks.strategies_mitigation.slice(0, 3).map((s: string, i: number) => (
                                                <div key={i} className="text-xs text-slate-500 dark:text-slate-400 flex items-start gap-2">
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
                    <div className="bg-gradient-to-r from-emerald-500 to-teal-500 p-6 rounded-3xl text-white">
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
                    <div className="bg-white dark:bg-[#13141c] p-6 rounded-3xl border border-slate-200 dark:border-white/5 shadow-sm dark:shadow-none">
                        <div className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-4">Recommandations</div>
                        <div className="space-y-2">
                            {recommendations.map((rec: string, i: number) => (
                                <div key={i} className="flex items-start gap-3 p-3 bg-slate-50 dark:bg-white/5 rounded-xl">
                                    <span className="w-6 h-6 bg-indigo-600 text-white rounded-full flex items-center justify-center text-xs font-bold shrink-0">{i + 1}</span>
                                    <span className="text-sm text-slate-600 dark:text-slate-300">{rec}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};
