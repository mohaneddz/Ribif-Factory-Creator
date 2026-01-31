import { Loader2, Sparkles } from "lucide-react";

import { MOCK_TCO_DATA } from "./constants";

export const TcoView = ({ data, loading }: { data: any, loading: boolean }) => {
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
        <div className="h-full flex flex-col p-6 gap-6 bg-slate-50 dark:bg-[#0b0c10] transition-colors">
            {/* Top Cards: Total TCO & Annual Avg */}
            <div className="grid grid-cols-2 gap-6">
                <div className="bg-slate-900 dark:bg-[#13141c] rounded-3xl p-8 text-white relative overflow-hidden">
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

                <div className="bg-white dark:bg-[#13141c] border border-slate-200 dark:border-white/5 rounded-3xl p-8 relative overflow-hidden transition-colors">
                    <div className="text-slate-400 dark:text-slate-500 font-bold uppercase tracking-widest text-xs mb-2">Moyenne Annuelle</div>
                    <div className="text-4xl font-black text-slate-800 dark:text-white mb-2">
                        {(avgAnnualTco / 1000000000).toFixed(2)} Mrd
                        <span className="text-lg font-bold text-slate-400 dark:text-slate-500 ml-2">DZD/an</span>
                    </div>
                    <div className="h-1.5 w-full bg-slate-100 dark:bg-white/5 rounded-full mt-4 overflow-hidden">
                        <div className="h-full bg-emerald-500 w-[60%]" />
                    </div>
                </div>
            </div>

            <div className="flex-1 grid grid-cols-3 gap-6 min-h-0">
                {/* Annual Evolution Chart (Simplified) */}
                <div className="col-span-2 bg-white dark:bg-[#13141c] border border-slate-200 dark:border-white/5 rounded-3xl p-6 flex flex-col transition-colors">
                    <div className="flex justify-between items-center mb-6">
                        <h3 className="font-bold text-slate-800 dark:text-white">Évolution Annuelle des Coûts</h3>
                        <div className="flex gap-2">
                            <span className="flex items-center gap-1.5 text-[10px] font-bold text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-white/5 px-2 py-1 rounded-md">
                                <div className="w-2 h-2 rounded-full bg-indigo-500" /> Machines
                            </span>
                            <span className="flex items-center gap-1.5 text-[10px] font-bold text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-white/5 px-2 py-1 rounded-md">
                                <div className="w-2 h-2 rounded-full bg-emerald-500" /> Produits
                            </span>
                            <span className="flex items-center gap-1.5 text-[10px] font-bold text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-white/5 px-2 py-1 rounded-md">
                                <div className="w-2 h-2 rounded-full bg-amber-500" /> Matières
                            </span>
                        </div>
                    </div>
                    <div className="flex-1 min-h-[240px] flex items-end justify-between px-4 gap-4 pb-2">
                        {annualTco.length > 0 ? (() => {
                            const maxVal = Math.max(1, ...annualTco.map((y: any) => y.total_tco || 0));
                            const barMaxHeight = 200;
                            return annualTco.map((year: any, i: number) => {
                                const totalVal = year.total_tco || 0;
                                const barHeight = Math.max((totalVal / maxVal) * barMaxHeight, 16);
                                const machinesVal = year.machines_tco || 0;
                                const productsVal = year.products_tco || 0;
                                const materialsVal = year.raw_materials_tco || 0;
                                const totalParts = machinesVal + productsVal + materialsVal || 1;
                                const machinesPct = (machinesVal / totalParts) * 100;
                                const productsPct = (productsVal / totalParts) * 100;
                                const materialsPct = (materialsVal / totalParts) * 100;
                                return (
                                    <div key={i} className="flex-1 flex flex-col items-center gap-2 group">
                                        <div className="text-[10px] font-bold text-slate-400 dark:text-slate-500 opacity-0 group-hover:opacity-100 transition-opacity">
                                            {(totalVal / 1000000000).toFixed(1)} Mrd
                                        </div>
                                        <div className="w-full bg-slate-50 dark:bg-white/5 rounded-t-xl relative overflow-hidden" style={{ height: `${barHeight}px` }}>
                                            <div className="absolute bottom-0 left-0 right-0" style={{ height: `${machinesPct}%`, backgroundColor: '#6366f1' }} />
                                            <div className="absolute left-0 right-0" style={{ bottom: `${machinesPct}%`, height: `${productsPct}%`, backgroundColor: '#10b981' }} />
                                            <div className="absolute left-0 right-0" style={{ bottom: `${machinesPct + productsPct}%`, height: `${materialsPct}%`, backgroundColor: '#f59e0b' }} />
                                        </div>
                                        <div className="text-xs font-bold text-slate-600 dark:text-slate-400">Année {year.year ?? i + 1}</div>
                                    </div>
                                );
                            });
                        })() : (
                            <div className="flex-1 flex items-center justify-center text-slate-400 dark:text-slate-500">Pas de données</div>
                        )}
                    </div>
                </div>

                {/* Cost Distribution */}
                <div className="bg-slate-50 dark:bg-[#13141c] border border-slate-200 dark:border-white/5 rounded-3xl p-6 overflow-y-auto transition-colors">
                    <h3 className="font-bold text-slate-800 dark:text-white mb-4">Postes de Coûts</h3>

                    <div className="space-y-4">
                        <div className="bg-white dark:bg-white/5 p-4 rounded-xl border border-slate-100 dark:border-white/5 shadow-sm dark:shadow-none">
                            <div className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-2">Répartition Totale</div>
                            <div className="space-y-2 text-xs">
                                <div className="flex justify-between"><span className="text-slate-500 dark:text-slate-400">Machines</span><span className="font-bold text-slate-700 dark:text-slate-200">{(totalMachinesTco / 1000000000).toFixed(2)} Mrd</span></div>
                                <div className="flex justify-between"><span className="text-slate-500 dark:text-slate-400">Produits</span><span className="font-bold text-slate-700 dark:text-slate-200">{(totalProductsTco / 1000000000).toFixed(2)} Mrd</span></div>
                                <div className="flex justify-between"><span className="text-slate-500 dark:text-slate-400">Matières</span><span className="font-bold text-slate-700 dark:text-slate-200">{(totalMaterialsTco / 1000000000).toFixed(2)} Mrd</span></div>
                            </div>
                        </div>

                        {rawMaterialsTco.length > 0 && (
                            <div className="bg-white dark:bg-white/5 p-4 rounded-xl border border-slate-100 dark:border-white/5 shadow-sm dark:shadow-none">
                                <div className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-2">Matériaux (Top 3)</div>
                                <div className="space-y-3">
                                    {rawMaterialsTco.slice(0, 3).map((mat: any, i: number) => (
                                        <div key={i} className="flex justify-between items-center">
                                            <div className="text-xs font-bold text-slate-700 dark:text-slate-200 truncate max-w-[120px]">{mat.nom_materiau}</div>
                                            <div className="text-xs font-medium text-slate-500 dark:text-slate-400">{((mat.total_tco || 0) / 1000000).toFixed(0)}M</div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {productTco.length > 0 && (
                            <div className="bg-white dark:bg-white/5 p-4 rounded-xl border border-slate-100 dark:border-white/5 shadow-sm dark:shadow-none">
                                <div className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-2">Produits (Top 3)</div>
                                <div className="space-y-3">
                                    {productTco.slice(0, 3).map((prod: any, i: number) => (
                                        <div key={i} className="flex justify-between items-center">
                                            <div className="text-xs font-bold text-slate-700 dark:text-slate-200 truncate max-w-[120px]">{prod.nom_produit}</div>
                                            <div className="text-xs font-medium text-slate-500 dark:text-slate-400">{((prod.total_tco || 0) / 1000000).toFixed(0)}M</div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {machineTco.length > 0 && (
                            <div className="bg-white dark:bg-white/5 p-4 rounded-xl border border-slate-100 dark:border-white/5 shadow-sm dark:shadow-none">
                                <div className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-2">Machines ({machineTco.length})</div>
                                <div className="space-y-3">
                                    {machineTco.map((mac: any, i: number) => (
                                        <div key={i} className="space-y-2">
                                            <div className="text-xs font-bold text-slate-700 dark:text-slate-200 truncate">{mac.machine_name}</div>
                                            {mac.cost_breakdown && (
                                                <>
                                                    <div className="flex h-2 w-full rounded-full overflow-hidden gap-0.5">
                                                        <div className="bg-indigo-500" style={{ width: `${mac.cost_breakdown.initial_pct || 0}%` }} title="Initial" />
                                                        <div className="bg-emerald-500" style={{ width: `${mac.cost_breakdown.operations_pct || 0}%` }} title="Ops" />
                                                        <div className="bg-amber-500" style={{ width: `${mac.cost_breakdown.maintenance_pct || 0}%` }} title="Maint" />
                                                    </div>
                                                    <div className="flex justify-between text-[9px] text-slate-400 dark:text-slate-500 font-medium">
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
