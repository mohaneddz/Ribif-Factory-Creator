import { Loader2, Sparkles, Cpu, Package, Calendar } from "lucide-react";

import { MOCK_TCO_DATA } from "./constants";

export const TcoView = ({ data, loading }: { data: any, loading: boolean }) => {
    // Use real data if available, otherwise fall back to mock
    const tcoData = data || MOCK_TCO_DATA;
    const totalTco = tcoData.total_tco || 0;
    const avgAnnualTco = tcoData.average_annual_tco || 0;
    const annualTco = tcoData.annual_tco || tcoData?.data?.annual_tco || [];
    const machineTco = tcoData.machine_tco || [];
    const rawMaterialsTco = tcoData.raw_materials_tco || [];
    const calcDate = tcoData.calculation_date || new Date().toISOString().split('T')[0];

    // Calculate totals from individual items if not provided
    const totalMachinesTco = tcoData.total_machines_tco || machineTco.reduce((sum: number, m: any) => sum + (m.total_tco || 0), 0);
    const totalMaterialsTco = tcoData.total_raw_materials_tco || rawMaterialsTco.reduce((sum: number, m: any) => sum + (m.total_tco || 0), 0);

    // Helper to render complex values (objects vs strings)
    const renderValue = (val: any) => {
        if (val === null || val === undefined) return "N/A";

        let target = val;

        // Handle stringified objects (like Python repr)
        if (typeof val === 'string' && val.trim().startsWith('{')) {
            try {
                const valueMatch = val.match(/['"](?:valeur|value)['"]\s*:\s*['"]([^'"]+)['"]/);
                if (valueMatch) return valueMatch[1];
            } catch (e) { }
        }

        if (typeof target === 'object' && !Array.isArray(target)) {
            return target.valeur ?? target.value ?? "N/A";
        }
        return target;
    };

    // Format currency based on value size
    const formatCurrency = (value: number) => {
        if (value >= 1000000000) {
            return `${(value / 1000000000).toFixed(2)} Mrd DZD`;
        } else if (value >= 1000000) {
            return `${(value / 1000000).toFixed(0)} M DZD`;
        } else {
            return `${value.toLocaleString()} DZD`;
        }
    };

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
        <div className="h-full flex flex-col p-4 sm:p-6 gap-4 sm:gap-6 bg-slate-50 dark:bg-[#0b0c10] transition-colors overflow-y-auto">
            {/* Top Card: Total TCO */}
            <div className="bg-slate-900 dark:bg-[#13141c] rounded-2xl sm:rounded-3xl p-4 sm:p-6 lg:p-8 text-white relative overflow-visible min-h-fit flex-shrink-0">
                <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500 rounded-full blur-[60px] opacity-20" />
                <div className="relative z-10">
                    <div className="text-slate-400 font-bold uppercase tracking-widest text-[10px] sm:text-xs mb-1 sm:mb-2">TCO Total (5 ans)</div>
                    <div className="text-2xl sm:text-3xl lg:text-4xl font-black mb-2 break-words">
                        {(totalTco / 1000000000).toFixed(2)} Milliards
                        <span className="text-sm sm:text-lg font-bold text-indigo-400 ml-2">DZD</span>
                    </div>
                    <div className="flex flex-wrap items-center gap-2 sm:gap-4 mt-3 sm:mt-4">
                        <div className="inline-flex items-center gap-2 px-2 sm:px-3 py-1 bg-white/10 rounded-full text-[10px] sm:text-xs font-medium">
                            <Sparkles size={12} className="text-indigo-300 flex-shrink-0" />
                            <span className="truncate">Calculé le {calcDate}</span>
                        </div>
                        <div className="inline-flex items-center gap-2 px-2 sm:px-3 py-1 bg-emerald-500/20 rounded-full text-[10px] sm:text-xs font-medium text-emerald-300">
                            <span className="truncate">Moyenne: {(avgAnnualTco / 1000000000).toFixed(2)} Mrd DZD/an</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* 5 Year TCO Calculation */}
            <div className="bg-white dark:bg-[#13141c] border border-slate-200 dark:border-white/5 rounded-2xl sm:rounded-3xl p-4 sm:p-6 transition-colors flex-shrink-0">
                <div className="flex items-center gap-3 mb-4 sm:mb-6">
                    <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-xl bg-indigo-100 dark:bg-indigo-500/20 flex items-center justify-center flex-shrink-0">
                        <Calendar size={18} className="text-indigo-600 dark:text-indigo-400" />
                    </div>
                    <h3 className="font-bold text-base sm:text-lg text-slate-800 dark:text-white">Calcul TCO sur 5 Ans</h3>
                </div>
                
                {annualTco.length > 0 ? (
                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 sm:gap-4">
                        {annualTco.map((year: any, i: number) => (
                            <div key={i} className="bg-slate-50 dark:bg-white/5 rounded-xl sm:rounded-2xl p-3 sm:p-4 text-center border border-slate-100 dark:border-white/5">
                                <div className="text-[10px] sm:text-xs font-bold text-indigo-600 dark:text-indigo-400 uppercase tracking-widest mb-1 sm:mb-2">
                                    Année {year.year ?? i + 1}
                                </div>
                                <div className="text-lg sm:text-2xl font-black text-slate-800 dark:text-white mb-0.5 sm:mb-1">
                                    {((year.total_tco || 0) / 1000000000).toFixed(2)}
                                </div>
                                <div className="text-[10px] sm:text-xs text-slate-500 dark:text-slate-400 font-medium">Mrd DZD</div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="text-center text-slate-400 dark:text-slate-500 py-8">Pas de données annuelles</div>
                )}
            </div>

            {/* Machines TCO Section */}
            <div className="bg-white dark:bg-[#13141c] border border-slate-200 dark:border-white/5 rounded-2xl sm:rounded-3xl p-4 sm:p-6 transition-colors flex-shrink-0">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-0 mb-4 sm:mb-6">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-xl bg-purple-100 dark:bg-purple-500/20 flex items-center justify-center flex-shrink-0">
                            <Cpu size={18} className="text-purple-600 dark:text-purple-400" />
                        </div>
                        <div>
                            <h3 className="font-bold text-base sm:text-lg text-slate-800 dark:text-white">TCO Machines</h3>
                            <p className="text-[10px] sm:text-xs text-slate-500 dark:text-slate-400">{machineTco.length} machine(s) identifiée(s)</p>
                        </div>
                    </div>
                    <div className="bg-purple-100 dark:bg-purple-500/20 px-3 sm:px-4 py-2 rounded-xl self-start sm:self-auto">
                        <div className="text-[10px] sm:text-xs text-purple-600 dark:text-purple-300 font-medium">Total Machines</div>
                        <div className="text-lg sm:text-xl font-black text-purple-700 dark:text-purple-300">{formatCurrency(totalMachinesTco)}</div>
                    </div>
                </div>

                {machineTco.length > 0 ? (
                    <div className="space-y-3">
                        {machineTco.map((mac: any, i: number) => {
                            // Calculate actual costs from percentages and total_tco
                            const totalCost = mac.total_tco || 0;
                            const hasBreakdown = mac.cost_breakdown && 
                                (mac.cost_breakdown.initial_pct !== undefined || 
                                 mac.cost_breakdown.operations_pct !== undefined || 
                                 mac.cost_breakdown.maintenance_pct !== undefined ||
                                 mac.cost_breakdown.initial_cost !== undefined ||
                                 mac.cost_breakdown.operations_cost !== undefined ||
                                 mac.cost_breakdown.maintenance_cost !== undefined);
                            
                            // Get actual costs - either from direct values or calculate from percentages
                            const initialCost = mac.cost_breakdown?.initial_cost ?? 
                                (mac.cost_breakdown?.initial_pct ? totalCost * mac.cost_breakdown.initial_pct / 100 : null);
                            const operationsCost = mac.cost_breakdown?.operations_cost ?? 
                                (mac.cost_breakdown?.operations_pct ? totalCost * mac.cost_breakdown.operations_pct / 100 : null);
                            const maintenanceCost = mac.cost_breakdown?.maintenance_cost ?? 
                                (mac.cost_breakdown?.maintenance_pct ? totalCost * mac.cost_breakdown.maintenance_pct / 100 : null);
                            
                            return (
                                <div key={i} className="bg-slate-50 dark:bg-white/5 rounded-xl sm:rounded-2xl p-3 sm:p-4 border border-slate-100 dark:border-white/5">
                                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 sm:gap-0">
                                        <div className="flex items-center gap-2 sm:gap-3 min-w-0">
                                            <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-purple-500/20 flex items-center justify-center text-purple-600 dark:text-purple-400 font-bold text-xs sm:text-sm flex-shrink-0">
                                                {i + 1}
                                            </div>
                                            <div className="min-w-0">
                                                <div className="font-bold text-sm sm:text-base text-slate-800 dark:text-white truncate">{renderValue(mac.machine_name)}</div>
                                                {mac.quantity && (
                                                    <div className="text-[10px] sm:text-xs text-slate-500 dark:text-slate-400">Quantité: {mac.quantity}</div>
                                                )}
                                            </div>
                                        </div>
                                        <div className="text-left sm:text-right ml-9 sm:ml-0">
                                            <div className="text-base sm:text-lg font-black text-slate-800 dark:text-white">{formatCurrency(mac.total_tco || 0)}</div>
                                        </div>
                                    </div>
                                    {hasBreakdown && (
                                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mt-3">
                                            {initialCost !== null && (
                                                <div className="bg-indigo-50 dark:bg-indigo-500/10 rounded-lg p-2 text-center">
                                                    <div className="text-[10px] text-indigo-600 dark:text-indigo-400 font-medium uppercase">Initial</div>
                                                    <div className="text-xs sm:text-sm font-bold text-indigo-700 dark:text-indigo-300">{formatCurrency(initialCost)}</div>
                                                </div>
                                            )}
                                            {operationsCost !== null && (
                                                <div className="bg-emerald-50 dark:bg-emerald-500/10 rounded-lg p-2 text-center">
                                                    <div className="text-[10px] text-emerald-600 dark:text-emerald-400 font-medium uppercase">Opérations</div>
                                                    <div className="text-xs sm:text-sm font-bold text-emerald-700 dark:text-emerald-300">{formatCurrency(operationsCost)}</div>
                                                </div>
                                            )}
                                            {maintenanceCost !== null && (
                                                <div className="bg-amber-50 dark:bg-amber-500/10 rounded-lg p-2 text-center">
                                                    <div className="text-[10px] text-amber-600 dark:text-amber-400 font-medium uppercase">Maintenance</div>
                                                    <div className="text-xs sm:text-sm font-bold text-amber-700 dark:text-amber-300">{formatCurrency(maintenanceCost)}</div>
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                ) : (
                    <div className="text-center text-slate-400 dark:text-slate-500 py-8">Aucune machine identifiée</div>
                )}
            </div>

            {/* Materials TCO Section */}
            <div className="bg-white dark:bg-[#13141c] border border-slate-200 dark:border-white/5 rounded-2xl sm:rounded-3xl p-4 sm:p-6 transition-colors flex-shrink-0">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-0 mb-4 sm:mb-6">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-xl bg-amber-100 dark:bg-amber-500/20 flex items-center justify-center flex-shrink-0">
                            <Package size={18} className="text-amber-600 dark:text-amber-400" />
                        </div>
                        <div>
                            <h3 className="font-bold text-base sm:text-lg text-slate-800 dark:text-white">TCO Matières Premières</h3>
                            <p className="text-[10px] sm:text-xs text-slate-500 dark:text-slate-400">{rawMaterialsTco.length} matériau(x) identifié(s)</p>
                        </div>
                    </div>
                    <div className="bg-amber-100 dark:bg-amber-500/20 px-3 sm:px-4 py-2 rounded-xl self-start sm:self-auto">
                        <div className="text-[10px] sm:text-xs text-amber-600 dark:text-amber-300 font-medium">Total Matières</div>
                        <div className="text-lg sm:text-xl font-black text-amber-700 dark:text-amber-300">{formatCurrency(totalMaterialsTco)}</div>
                    </div>
                </div>

                {rawMaterialsTco.length > 0 ? (
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead>
                                <tr className="border-b border-slate-200 dark:border-white/10">
                                    <th className="text-left py-3 px-4 text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-widest">Matériau</th>
                                    <th className="text-right py-3 px-4 text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-widest">Prix Unitaire</th>
                                    <th className="text-right py-3 px-4 text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-widest">TCO Total</th>
                                </tr>
                            </thead>
                            <tbody>
                                {rawMaterialsTco.map((mat: any, i: number) => (
                                    <tr key={i} className="border-b border-slate-100 dark:border-white/5 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors">
                                        <td className="py-3 px-4">
                                            <div className="flex items-center gap-3">
                                                <div className="w-8 h-8 rounded-lg bg-amber-500/20 flex items-center justify-center text-amber-600 dark:text-amber-400 font-bold text-sm">
                                                    {i + 1}
                                                </div>
                                                <span className="font-medium text-slate-800 dark:text-white">{renderValue(mat.nom_materiau)}</span>
                                            </div>
                                        </td>
                                        <td className="py-3 px-4 text-right text-slate-600 dark:text-slate-300 font-medium">
                                            {mat.unit_price ? `${(mat.unit_price).toLocaleString()} DZD` : 'N/A'}
                                        </td>
                                        <td className="py-3 px-4 text-right">
                                            <span className="font-bold text-slate-800 dark:text-white">{formatCurrency(mat.total_tco || 0)}</span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <div className="text-center text-slate-400 dark:text-slate-500 py-8">Aucune matière première identifiée</div>
                )}
            </div>
        </div>
    );
};
