import { LayoutGrid, Plus, Settings } from "lucide-react";
import { motion } from "framer-motion";

interface ActionPanelProps {
  onCreateProject: () => void;
  onOpenSettings: () => void;
}

export const ActionPanel = ({ onCreateProject, onOpenSettings }: ActionPanelProps) => {
  return (
    <div className="w-[480px] bg-white dark:bg-[#0b0c10] border-l border-slate-200 dark:border-white/5 flex flex-col z-20 shadow-[-4px_0_24px_rgba(0,0,0,0.1)] dark:shadow-[-4px_0_24px_rgba(0,0,0,0.4)]">
      <div className="p-10 flex justify-end">
        <button
          onClick={onOpenSettings}
          className="w-12 h-12 rounded-full bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-white/10 hover:text-indigo-600 dark:hover:text-white cursor-pointer transition-colors border border-slate-200 dark:border-white/5 hover:border-slate-300 dark:hover:border-white/10"
          aria-label="Open settings"
        >
          <Settings size={22} />
        </button>
      </div>

      <div className="flex-1 px-10 flex flex-col justify-center pb-20">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
        >
          <div className="mb-8">
            <div className="w-16 h-16 bg-indigo-500/10 border border-indigo-500/20 rounded-2xl flex items-center justify-center text-indigo-600 dark:text-indigo-400 mb-6 shadow-lg shadow-indigo-500/10 dark:shadow-indigo-900/20">
              <LayoutGrid size={32} />
            </div>
            <h2 className="text-4xl font-extrabold mb-4 leading-tight text-slate-900 dark:text-white">
              Espace <br /> <span className="text-indigo-600 dark:text-indigo-400">Ingénieur</span>
            </h2>
            <p className="text-xl text-slate-500 dark:text-slate-400 font-medium leading-relaxed">
              Créez, simulez et déployez vos usines intelligentes en quelques clics.
            </p>
          </div>

          <button
            onClick={onCreateProject}
            className="w-full bg-indigo-600 hover:bg-indigo-700 dark:hover:bg-indigo-500 text-white p-2 rounded-[2rem] mb-4 transition-all group active:scale-[0.98] duration-100 shadow-xl shadow-indigo-600/20"
          >
            <div className="border-2 border-white/10 rounded-[1.5rem] py-8 flex flex-col items-center bg-indigo-600 group-hover:bg-indigo-700 dark:group-hover:bg-indigo-500 transition-colors">
              <div className="bg-white/20 w-16 h-16 rounded-full flex items-center justify-center mb-4 text-white backdrop-blur-sm">
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
