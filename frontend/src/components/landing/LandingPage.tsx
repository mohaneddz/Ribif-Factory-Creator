"use client";

import { motion } from "framer-motion";
import { ArrowRight, Factory, Cpu, BarChart3, FileText, Zap, Shield, Search, Box, Briefcase, Users, CheckCircle2 } from "lucide-react";
import { useRouter } from "next/navigation";

const features = [
  {
    icon: Factory,
    title: "Digital Twin",
    description: "Visualisez vos usines en 3D avec simulation temps réel",
    color: "from-indigo-500 to-purple-600",
  },
  {
    icon: Cpu,
    title: "IA Intégrée",
    description: "Extraction automatique des specs et optimisation intelligente",
    color: "from-emerald-500 to-teal-600",
  },
  {
    icon: BarChart3,
    title: "TCO & ROI",
    description: "Analyse financière complète avec projections sur 5 ans",
    color: "from-amber-500 to-orange-600",
  },
  {
    icon: FileText,
    title: "Business Plan",
    description: "Génération automatique de plans d'affaires et pitch decks",
    color: "from-rose-500 to-pink-600",
  },
  {
    icon: Zap,
    title: "Workflow Automatisé",
    description: "Pipeline complet du cahier des charges au jumeau digital",
    color: "from-cyan-500 to-blue-600",
  },
  {
    icon: Shield,
    title: "Sourcing Optimisé",
    description: "Recherche et négociation fournisseurs assistée par IA",
    color: "from-violet-500 to-indigo-600",
  },
];

export default function LandingPage() {
  const router = useRouter();

  const workflowSteps = [
    {
      step: "01",
      title: "Analyse Intelligente",
      description: "Importez vos PDF/Cahiers des charges. Notre IA extrait et restructure automatiquement les besoins techniques.",
      icon: FileText
    },
    {
      step: "02",
      title: "Sourcing Global",
      description: "L'agent autonome scanne le web pour trouver les meilleurs fournisseurs et machines compatibles (Alibaba, Indiamart, etc.).",
      icon: Search
    },
    {
      step: "03",
      title: "Jumeau Numérique",
      description: "Visualisez votre usine en 3D. Inspectez les machines, les flux et l'agencement avant la moindre dépense.",
      icon: Box
    },
    {
      step: "04",
      title: "Business Plan",
      description: "Générez un dossier financier complet : TCO, ROI, OPEX/CAPEX et Pitch Deck prêt pour les investisseurs.",
      icon: Briefcase
    }
  ];

  const useCases = [
    {
      title: "Consultants Industriels",
      description: "Réduisez vos temps d'étude par 10. Livrez des pré-projets complets et chiffrés à vos clients en quelques heures.",
      stats: "-80% de temps d'étude"
    },
    {
      title: "Porteurs de Projet",
      description: "Passez de l'idée à la banque. Obtenez tous les documents techniques et financiers crédibles pour lever des fonds.",
      stats: "Dossiers bancables"
    },
    {
      title: "Bureaux d'Études",
      description: "Automatisez les tâches répétitives de sourcing et de chiffrage pour vous concentrer sur l'ingénierie à haute valeur.",
      stats: "Productivité x5"
    }
  ];

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-[#0b0c10] text-slate-900 dark:text-white overflow-hidden selection:bg-indigo-500/30 transition-colors">
      {/* Background Effects */}
      <div className="fixed inset-0 pointer-events-none opacity-50 dark:opacity-100">
        <div className="absolute top-0 left-1/4 w-[600px] h-[600px] bg-indigo-500/20 rounded-full blur-[150px]" />
        <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-emerald-500/15 rounded-full blur-[140px]" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-purple-500/10 rounded-full blur-[200px]" />
      </div>

      {/* Navigation */}
      <nav className="fixed top-0 inset-x-0 z-50 border-b border-slate-200 dark:border-white/5 bg-white/80 dark:bg-[#0b0c10]/80 backdrop-blur-lg transition-colors">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center gap-3"
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Factory size={22} className="text-white" />
            </div>
            <span className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">RIBIF</span>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center gap-4"
          >
             <button
              onClick={() => router.push("/auth/login")}
              className="px-5 py-2.5 text-sm font-semibold text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition-colors"
            >
              Se connecter
            </button>
            <button
              onClick={() => router.push("/auth/register")}
              className="px-5 py-2.5 text-sm font-bold bg-indigo-600 dark:bg-white text-white dark:text-slate-900 rounded-full hover:bg-indigo-700 dark:hover:bg-slate-200 transition-all shadow-lg shadow-indigo-200 dark:shadow-white/10"
            >
              Créer un compte
            </button>
          </motion.div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative z-10 max-w-7xl mx-auto px-6 pt-40 pb-32">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="text-center max-w-4xl mx-auto"
        >
          <div className="inline-flex items-center gap-2 rounded-full border border-indigo-500/30 bg-indigo-50 dark:bg-indigo-500/10 px-4 py-2 text-xs uppercase tracking-[0.25em] text-indigo-600 dark:text-indigo-300 mb-8 backdrop-blur-sm">
            <Zap size={14} />
            Industrie 5.0 — Propulsé par l'IA
          </div>

          <h1 className="text-5xl md:text-8xl font-black leading-[1.1] mb-8 tracking-tight text-slate-900 dark:text-white">
            Transformez vos{" "}
            <span className="bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 dark:from-indigo-400 dark:via-purple-400 dark:to-pink-400 bg-clip-text text-transparent">
              cahiers des charges
            </span>{" "}
            en usines digitales
          </h1>

          <p className="text-xl text-slate-500 dark:text-slate-400 max-w-2xl mx-auto mb-12 leading-relaxed">
            RIBIF automatise l'analyse de vos specs, génère des layouts optimisés,
            et crée des jumeaux numériques 3D — de l'idée à la production en quelques heures.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-5">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => router.push("/auth/register")}
              className="group px-8 py-4 bg-gradient-to-r from-indigo-600 to-purple-600 rounded-full text-lg font-bold flex items-center gap-3 shadow-xl shadow-indigo-600/25 hover:shadow-indigo-600/40 transition-all border border-indigo-500/20 text-white"
            >
              Commencer gratuitement
              <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
            </motion.button>

            <button
               onClick={() => router.push("/auth/login")}
               className="px-8 py-4 rounded-full text-lg font-semibold text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-white/10 hover:border-slate-300 dark:hover:border-white/20 hover:bg-slate-100 dark:hover:bg-white/5 hover:text-slate-900 dark:hover:text-white transition-all backdrop-blur-sm"
            >
              Démo interactive
            </button>
          </div>
        </motion.div>

        {/* Floating Elements (Decorations) */}
        <div className="absolute top-1/4 left-0 -translate-x-1/2 opacity-20 pointer-events-none">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 50, repeat: Infinity, ease: "linear" }}
            className="w-96 h-96 border border-dashed border-indigo-500/50 rounded-full"
          />
        </div>
      </section>

      {/* Stats Section */}
      <section className="relative z-10 border-y border-slate-200 dark:border-white/5 bg-slate-50/50 dark:bg-white/5 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 py-12 grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
            {[
                { label: "Temps gagné", value: "-80%" },
                { label: "Projets générés", value: "500+" },
                { label: "Précision Budget", value: "95%" },
                { label: "Fournisseurs", value: "10k+" }
            ].map((stat) => (
                <div key={stat.label}>
                    <div className="text-4xl font-black text-slate-900 dark:text-white mb-1">{stat.value}</div>
                    <div className="text-sm font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">{stat.label}</div>
                </div>
            ))}
        </div>
      </section>

      {/* Features Grid */}
      <section className="relative z-10 max-w-7xl mx-auto px-6 py-32">
        <div className="text-center mb-20">
          <h2 className="text-4xl md:text-5xl font-bold mb-6 text-slate-900 dark:text-white">
            Tout ce qu'il faut pour{" "}
            <span className="text-indigo-600 dark:text-indigo-400">industrialiser</span>
          </h2>
          <p className="text-slate-500 dark:text-slate-400 text-lg max-w-2xl mx-auto">
            Une plateforme complète pour transformer vos projets industriels en réalité
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((feature, index) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.1 }}
              className="group p-8 rounded-3xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 hover:border-indigo-500/50 hover:bg-white dark:hover:bg-white/10 transition-all duration-300 shadow-xl shadow-slate-200/50 dark:shadow-none"
            >
              <div
                className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${feature.color} flex items-center justify-center mb-6 group-hover:scale-110 transition-transform shadow-lg`}
              >
                <feature.icon size={26} className="text-white" />
              </div>
              <h3 className="text-xl font-bold mb-3 text-slate-900 dark:text-white">{feature.title}</h3>
              <p className="text-slate-500 dark:text-slate-400 leading-relaxed text-sm">{feature.description}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* How it Works / Workflow */}
      <section className="relative z-10 max-w-7xl mx-auto px-6 py-24">
         <div className="grid lg:grid-cols-2 gap-16 items-center">
             <div>
                 <h2 className="text-3xl md:text-5xl font-bold mb-8 text-slate-900 dark:text-white">Un workflow fluide, de l'idée à la production</h2>
                 <p className="text-lg text-slate-500 dark:text-slate-400 mb-12">Oubliez les fichiers Excel interminables et les semaines de sourcing manuel. RIBIF orchestre tout pour vous.</p>
                 
                 <div className="space-y-8">
                     {workflowSteps.map((step, i) => (
                         <div key={i} className="flex gap-6">
                             <div className="flex-shrink-0 w-12 h-12 rounded-full border border-indigo-500/30 bg-indigo-50 dark:bg-indigo-500/10 flex items-center justify-center text-indigo-600 dark:text-indigo-400 font-bold font-mono">
                                 {step.step}
                             </div>
                             <div>
                                 <h3 className="text-xl font-bold mb-2 flex items-center gap-2 text-slate-900 dark:text-white">
                                     {step.title}
                                 </h3>
                                 <p className="text-slate-500 dark:text-slate-400 leading-relaxed">{step.description}</p>
                             </div>
                         </div>
                     ))}
                 </div>
             </div>
             <div className="relative">
                 {/* Abstract representation of the app interface */}
                 <div className="absolute inset-0 bg-gradient-to-br from-indigo-600 to-purple-600 blur-[100px] opacity-20" />
                 <div className="relative bg-white dark:bg-[#13141c] border border-slate-200 dark:border-white/10 rounded-2xl p-2 shadow-2xl rotate-2 hover:rotate-0 transition-transform duration-500">
                     <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent" />
                     <div className="bg-slate-100 dark:bg-[#0b0c10] rounded-xl overflow-hidden aspect-[4/3] flex items-center justify-center border border-slate-200 dark:border-white/5">
                        <div className="text-center">
                            <Box size={64} className="mx-auto text-indigo-500 mb-4 opacity-80" />
                            <div className="text-slate-500 font-mono text-sm">Rendering 3D Twin...</div>
                        </div>
                     </div>
                 </div>
                 
                 {/* Floating cards */}
                 <div className="absolute -bottom-8 -left-8 bg-white dark:bg-[#1f2937] p-4 rounded-xl border border-slate-200 dark:border-white/10 shadow-xl max-w-[200px]">
                     <div className="flex items-center gap-3 mb-2">
                         <div className="w-2 h-2 rounded-full bg-emerald-500" />
                         <span className="text-xs font-bold text-slate-700 dark:text-slate-300">Sourcing terminé</span>
                     </div>
                     <div className="text-xs text-slate-500">12 fournisseurs identifiés avec succès.</div>
                 </div>
             </div>
         </div>
      </section>

      {/* Use Cases */}
      <section className="relative z-10 bg-slate-50/50 dark:bg-white/5 border-y border-slate-200 dark:border-white/10 py-32">
          <div className="max-w-7xl mx-auto px-6">
            <div className="text-center mb-16">
                <h2 className="text-4xl font-bold mb-4 text-slate-900 dark:text-white">Pour qui est fait RIBIF ?</h2>
                <p className="text-slate-500 dark:text-slate-400">Une solution adaptée à tous les acteurs de l'industrie</p>
            </div>

            <div className="grid md:grid-cols-3 gap-8">
                {useCases.map((useCase, i) => (
                    <div key={i} className="bg-white dark:bg-[#0b0c10] border border-slate-200 dark:border-white/10 rounded-3xl p-8 hover:border-indigo-500/30 transition-colors relative overflow-hidden group shadow-xl shadow-slate-200/50 dark:shadow-none">
                        <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:opacity-20 transition-opacity">
                            <Users size={80} className="text-indigo-600 dark:text-white" />
                        </div>
                        <h3 className="text-2xl font-bold mb-4 text-slate-900 dark:text-white">{useCase.title}</h3>
                        <p className="text-slate-500 dark:text-slate-400 mb-8 leading-relaxed h-24">{useCase.description}</p>
                        <div className="inline-flex items-center gap-2 px-3 py-1 bg-indigo-50 dark:bg-indigo-500/20 text-indigo-600 dark:text-indigo-300 rounded-full text-sm font-bold">
                            <CheckCircle2 size={14} />
                            {useCase.stats}
                        </div>
                    </div>
                ))}
            </div>
          </div>
      </section>

      {/* CTA Section */}
      <section className="relative z-10 max-w-5xl mx-auto px-6 py-32">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          className="relative rounded-[3rem] bg-gradient-to-br from-indigo-600 via-purple-600 to-pink-600 p-12 md:p-20 text-center overflow-hidden shadow-2xl shadow-indigo-500/30"
        >
          {/* Glow effects */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent" />
          <div className="absolute -top-20 -right-20 w-80 h-80 bg-white/20 rounded-full blur-3xl" />
          <div className="absolute -bottom-20 -left-20 w-80 h-80 bg-white/20 rounded-full blur-3xl" />

          <div className="relative z-10">
            <h2 className="text-4xl md:text-6xl font-black mb-6 tracking-tight text-white">
              Prêt à révolutionner votre industrie?
            </h2>
            <p className="text-xl text-white/90 max-w-2xl mx-auto mb-10 leading-relaxed font-medium">
              Rejoignez les entreprises qui transforment leurs projets industriels avec RIBIF. Commencez gratuitement dès aujourd'hui.
            </p>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => router.push("/auth/register")}
              className="px-10 py-5 bg-white text-slate-900 rounded-full text-lg font-bold shadow-xl hover:shadow-white/25 transition-all"
            >
              Démarrer maintenant
            </motion.button>
          </div>
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 border-t border-slate-200 dark:border-white/10 py-12 px-6 bg-slate-50 dark:bg-[#050608] transition-colors">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6 text-sm text-slate-500">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 dark:bg-white/10 flex items-center justify-center">
              <Factory size={16} className="text-white dark:text-slate-300" />
            </div>
            <span className="font-bold text-slate-900 dark:text-slate-300 text-base">RIBIF</span>
            <span className="ml-4">© 2026 RIBIF. Tous droits réservés.</span>
          </div>
          
          <div className="flex items-center gap-8">
            <a href="#" className="hover:text-indigo-600 dark:hover:text-white transition-colors">Confidentialité</a>
            <a href="#" className="hover:text-indigo-600 dark:hover:text-white transition-colors">Conditions</a>
            <a href="#" className="hover:text-indigo-600 dark:hover:text-white transition-colors">Contact</a>
            <a href="#" className="hover:text-indigo-600 dark:hover:text-white transition-colors">Twitter</a>
            <a href="#" className="hover:text-indigo-600 dark:hover:text-white transition-colors">LinkedIn</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
