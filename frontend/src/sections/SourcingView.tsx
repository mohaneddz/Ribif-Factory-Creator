import { useState } from "react";
import { motion } from "framer-motion";
import { Globe, Layers, Loader2 } from "lucide-react";
import clsx from "clsx";

export const SourcingView = ({ progress, data, module4Data, loading }: { progress: number, data: any, module4Data: any, loading: boolean }) => {
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

    // If we have data but it's empty, show the "waiting" state.
    // However, if we are loading, the loader above takes precedence.
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
            <div className="w-80 bg-white rounded-3xl border border-slate-200 p-4 flex flex-col shadow-sm">
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
            <div className="flex-1 bg-white rounded-3xl border border-slate-200 p-6 overflow-hidden flex flex-col shadow-sm">
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
