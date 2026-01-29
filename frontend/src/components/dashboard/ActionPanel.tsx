import { LayoutGrid, Plus, Settings } from "lucide-react";
import { motion } from "framer-motion";

interface ActionPanelProps {
  onCreateProject: () => void;
  onOpenSettings: () => void;
}

export const ActionPanel = ({ onCreateProject, onOpenSettings }: ActionPanelProps) => {
  return (
    <div className="w-[480px] bg-[var(--surface-1)] border-l border-[var(--border-1)] flex flex-col z-20 shadow-[-4px_0_24px_rgba(0,0,0,0.02)]">
      <div className="p-10 flex justify-end">
        <button
          onClick={onOpenSettings}
          className="w-12 h-12 rounded-full bg-[var(--surface-2)] flex items-center justify-center text-[var(--text-2)] hover:bg-slate-100 hover:text-indigo-600 cursor-pointer transition-colors border border-transparent hover:border-slate-200"
          aria-label="Open settings"
        >
          <Settings size={24} />
        </button>
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
            <h2 className="text-4xl font-extrabold mb-4 leading-tight text-[var(--text-1)]">
              Espace <br /> <span className="text-indigo-600">Ingénieur</span>
            </h2>
            <p className="text-xl text-[var(--text-2)] font-medium leading-relaxed">
              Créez, simulez et déployez vos usines intelligentes en quelques clics.
            </p>
          </div>

          <button
            onClick={onCreateProject}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white p-2 rounded-4xl mb-4 transition-all group active:scale-[0.98] duration-100 shadow-xl shadow-indigo-200"
          >
            <div className="border-2 border-white/20 rounded-3xl py-8 flex flex-col items-center bg-indigo-600 group-hover:bg-indigo-700 transition-colors">
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
  );
};
