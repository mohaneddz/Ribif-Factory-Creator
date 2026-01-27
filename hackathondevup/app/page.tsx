"use client";

import React from "react";
import { useRouter } from "next/navigation";
import {
  Plus, Search, MapPin, Calendar,
  LayoutGrid, Settings,
  Box, Zap, Activity, MonitorPlay,
  Layers, Cpu, ArrowRight, ExternalLink
} from "lucide-react";
import { motion } from "framer-motion";
import clsx from "clsx";

// ==========================================
// CONFIGURATION
// ==========================================

const PROJECTS = [
  {
    id: "1",
    name: "Renault Tanger Ext.",
    client: "Groupe Renault",
    location: "Tanger, Maroc",
    date: "Oct 2024",
    status: "live",
    type: "Automobile",
  },
  {
    id: "2",
    name: "Sanofi Unité B",
    client: "Sanofi Pasteur",
    location: "Lyon, France",
    date: "Dec 2024",
    status: "live",
    type: "Pharmaceutique",
  },
  {
    id: "3",
    name: "H2 Green Pilot",
    client: "Engie Solutions",
    location: "Dunkerque, FR",
    date: "Jan 2025",
    status: "study",
    type: "Énergie",
  },
  {
    id: "4",
    name: "Amazon Logistique",
    client: "Amazon EU",
    location: "Marseille, FR",
    date: "Fév 2025",
    status: "study",
    type: "Logistique",
  }
];

// ==========================================
// STYLES
// ==========================================

const fontStyle = `
  @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&display=swap');
  
  body, div, button, input {
    font-family: 'Outfit', sans-serif;
  }
`;

// ==========================================
// COMPONENTS
// ==========================================

const StatusBadge = ({ status }: { status: string }) => {
  const isLive = status === 'live';
  return (
      <div className={clsx(
          "px-4 py-2 rounded-full text-xs font-bold border flex items-center gap-2",
          isLive
              ? "bg-emerald-50 text-emerald-700 border-emerald-100"
              : "bg-indigo-50 text-indigo-700 border-indigo-100"
      )}>
        <div className={clsx(
            "w-2 h-2 rounded-full",
            isLive ? "bg-emerald-500 animate-pulse" : "bg-indigo-500"
        )} />
        {isLive ? "OPÉRATIONNEL" : "EN ÉTUDE"}
      </div>
  );
};

export default function Dashboard() {
  const router = useRouter();

  return (
      <>
        <style>{fontStyle}</style>

        <div className="flex h-screen w-full bg-[#F8FAFC] text-slate-900 overflow-hidden selection:bg-indigo-100">

          {/* ==========================================
            LEFT: PROJECT LIST
            ========================================== */}
          <div className="flex-1 flex flex-col relative z-10 border-r border-slate-200">

            {/* Header */}
            <header className="h-32 px-10 flex items-center justify-between bg-white border-b border-slate-200">
              <div>
                <h1 className="text-4xl font-extrabold tracking-tight mb-1 text-slate-900">Projets</h1>
                <p className="text-slate-500 font-medium text-lg">Vue d'ensemble du parc</p>
              </div>

              <div className="w-80 bg-slate-50 h-14 rounded-full flex items-center px-6 border border-transparent focus-within:border-indigo-500 focus-within:bg-white focus-within:ring-4 focus-within:ring-indigo-50 transition-all">
                <Search size={20} className="text-slate-400" />
                <input
                    type="text"
                    placeholder="Rechercher..."
                    className="bg-transparent border-none outline-none w-full ml-3 text-lg font-medium placeholder-slate-400 text-slate-700"
                />
              </div>
            </header>

            {/* List Content */}
            <div className="flex-1 overflow-y-auto p-10 space-y-6 bg-[#F8FAFC]">
              {PROJECTS.map((project, idx) => (
                  <motion.div
                      key={project.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: idx * 0.1 }}
                      className="bg-white rounded-[32px] p-8 border border-slate-200 hover:border-indigo-300 hover:shadow-lg hover:shadow-slate-200/50 transition-all duration-300"
                  >
                    {/* Card Top Section */}
                    <div className="flex justify-between items-start mb-8">
                      <div className="flex items-center gap-5">
                        <div className="w-20 h-20 rounded-2xl bg-indigo-50 flex items-center justify-center text-indigo-600 border border-indigo-100 shadow-sm">
                          {project.type === 'Automobile' && <Box size={32} />}
                          {project.type === 'Pharmaceutique' && <Activity size={32} />}
                          {project.type === 'Énergie' && <Zap size={32} />}
                          {project.type === 'Logistique' && <Layers size={32} />}
                        </div>
                        <div>
                          <h2 className="text-2xl font-bold text-slate-900">{project.name}</h2>
                          <p className="text-base font-medium text-slate-500 mt-1 mb-3">{project.client}</p>

                          <div className="flex items-center gap-6 text-slate-400 text-sm font-semibold">
                            <span className="flex items-center gap-1.5"><MapPin size={16} className="text-indigo-400"/> {project.location}</span>
                            <span className="flex items-center gap-1.5"><Calendar size={16} className="text-indigo-400"/> {project.date}</span>
                          </div>
                        </div>
                      </div>
                      <StatusBadge status={project.status} />
                    </div>

                    {/* Bottom Action Area */}
                    <div className="pt-6 border-t border-slate-50 flex gap-3">

                      {/* ALWAYS VISIBLE: Details Button */}
                      <button
                          className={clsx(
                              "h-14 rounded-2xl bg-white border-2 border-slate-100 text-slate-600 font-bold text-lg flex items-center justify-center hover:border-indigo-200 hover:text-indigo-600 hover:bg-indigo-50 transition-all active:scale-[0.99]",
                              project.status === 'live' ? "px-6 w-auto" : "w-full px-8"
                          )}
                      >
                        {project.status === 'live' ? (
                            <span className="flex items-center gap-2">Détails <ExternalLink size={18} /></span>
                        ) : (
                            <span className="flex items-center gap-3"><ExternalLink size={20} /> Voir Détails</span>
                        )}
                      </button>

                      {/* CONDITIONALLY VISIBLE: Digital Twin Button */}
                      {project.status === 'live' && (
                          <button
                              onClick={() => router.push('/twin')}
                              className="flex-1 h-14 px-8 rounded-2xl bg-indigo-600 text-white font-bold text-lg flex items-center justify-center gap-3 hover:bg-indigo-700 hover:shadow-lg hover:shadow-indigo-200 transition-all active:scale-[0.99] group"
                          >
                            <MonitorPlay size={20} />
                            <span>Ouvrir Jumeau</span>
                            <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
                          </button>
                      )}

                    </div>
                  </motion.div>
              ))}
            </div>
          </div>

          {/* ==========================================
            RIGHT: ACTION PANEL
            ========================================== */}
          <div className="w-[480px] bg-white border-l border-slate-200 flex flex-col z-20 shadow-[-4px_0_24px_rgba(0,0,0,0.02)]">

            <div className="p-10 flex justify-end">
              <div className="w-12 h-12 rounded-full bg-slate-50 flex items-center justify-center text-slate-600 hover:bg-slate-100 hover:text-indigo-600 cursor-pointer transition-colors border border-transparent hover:border-slate-200">
                <Settings size={24} />
              </div>
            </div>

            <div className="flex-1 px-10 flex flex-col justify-center pb-20">
              <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.2 }}
              >
                <div className="mb-8">
                  <div className="w-16 h-16 bg-indigo-100 rounded-2xl flex items-center justify-center text-indigo-600 mb-6">
                    <LayoutGrid size={32} />
                  </div>
                  <h2 className="text-4xl font-extrabold mb-4 leading-tight text-slate-900">
                    Espace <br/> <span className="text-indigo-600">Ingénieur</span>
                  </h2>
                  <p className="text-xl text-slate-500 font-medium leading-relaxed">
                    Créez, simulez et déployez vos usines intelligentes en quelques clics.
                  </p>
                </div>

                <button
                    onClick={() => router.push('/workflow')}
                    className="w-full bg-indigo-600 hover:bg-indigo-700 text-white p-2 rounded-[32px] mb-4 transition-all group active:scale-[0.98] duration-100 shadow-xl shadow-indigo-200"
                >
                  <div className="border-2 border-white/20 rounded-[24px] py-8 flex flex-col items-center bg-indigo-600 group-hover:bg-indigo-700 transition-colors">
                    <div className="bg-white/20 w-16 h-16 rounded-full flex items-center justify-center mb-4 text-white">
                      <Plus size={32} strokeWidth={3} />
                    </div>
                    <span className="text-2xl font-bold">Nouveau Projet</span>
                    <span className="text-indigo-100 font-medium mt-1">Importer Specs / PDF</span>
                  </div>
                </button>


              </motion.div>
            </div>



          </div>
        </div>
      </>
  );
}