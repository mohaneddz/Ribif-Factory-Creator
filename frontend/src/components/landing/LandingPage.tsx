"use client";

import { motion } from "framer-motion";
import { ArrowRight, Factory, Cpu, BarChart3, FileText, Zap, Shield } from "lucide-react";
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

  return (
    <div className="min-h-screen bg-[#0b0c10] text-white overflow-hidden">
      {/* Background Effects */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/4 w-[600px] h-[600px] bg-indigo-500/20 rounded-full blur-[150px]" />
        <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-emerald-500/15 rounded-full blur-[140px]" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-purple-500/10 rounded-full blur-[200px]" />
      </div>

      {/* Navigation */}
      <nav className="relative z-50 flex items-center justify-between px-8 py-6 max-w-7xl mx-auto">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="flex items-center gap-3"
        >
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
            <Factory size={22} className="text-white" />
          </div>
          <span className="text-xl font-bold tracking-tight">RIBIF</span>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="flex items-center gap-4"
        >
          <button
            onClick={() => router.push("/auth/login")}
            className="px-5 py-2.5 text-sm font-semibold text-slate-300 hover:text-white transition-colors"
          >
            Se connecter
          </button>
          <button
            onClick={() => router.push("/auth/register")}
            className="px-5 py-2.5 text-sm font-bold bg-white text-slate-900 rounded-full hover:bg-slate-100 transition-all"
          >
            Créer un compte
          </button>
        </motion.div>
      </nav>

      {/* Hero Section */}
      <section className="relative z-10 max-w-7xl mx-auto px-8 pt-16 pb-24">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="text-center max-w-4xl mx-auto"
        >
          <div className="inline-flex items-center gap-2 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-4 py-2 text-xs uppercase tracking-[0.25em] text-indigo-300 mb-8">
            <Zap size={14} />
            Industrie 5.0 — Propulsé par l'IA
          </div>

          <h1 className="text-5xl md:text-7xl font-black leading-[1.1] mb-6">
            Transformez vos{" "}
            <span className="bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
              cahiers des charges
            </span>{" "}
            en usines digitales
          </h1>

          <p className="text-xl text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            RIBIF automatise l'analyse de vos specs, génère des layouts optimisés,
            et crée des jumeaux numériques 3D — de l'idée à la production en quelques heures.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => router.push("/auth/register")}
              className="group px-8 py-4 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-full text-lg font-bold flex items-center gap-3 shadow-xl shadow-indigo-500/25 hover:shadow-indigo-500/40 transition-shadow"
            >
              Commencer gratuitement
              <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
            </motion.button>

            <button
              onClick={() => router.push("/auth/login")}
              className="px-8 py-4 rounded-full text-lg font-semibold text-slate-300 border border-slate-700 hover:border-slate-500 hover:text-white transition-all"
            >
              J'ai déjà un compte
            </button>
          </div>
        </motion.div>

        {/* Floating Elements */}
        <div className="absolute top-32 left-10 opacity-20">
          <motion.div
            animate={{ y: [0, -20, 0] }}
            transition={{ duration: 5, repeat: Infinity }}
            className="w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600"
          />
        </div>
        <div className="absolute bottom-20 right-10 opacity-20">
          <motion.div
            animate={{ y: [0, 20, 0] }}
            transition={{ duration: 6, repeat: Infinity }}
            className="w-16 h-16 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600"
          />
        </div>
      </section>

      {/* Features Section */}
      <section className="relative z-10 max-w-7xl mx-auto px-8 py-24">
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl font-bold mb-4">
            Tout ce qu'il faut pour{" "}
            <span className="text-indigo-400">industrialiser</span>
          </h2>
          <p className="text-slate-400 text-lg max-w-2xl mx-auto">
            Une plateforme complète pour transformer vos projets industriels en réalité
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, index) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.1 }}
              className="group p-8 rounded-3xl bg-white/5 border border-white/10 hover:border-indigo-500/50 hover:bg-white/10 transition-all duration-300"
            >
              <div
                className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${feature.color} flex items-center justify-center mb-5 group-hover:scale-110 transition-transform`}
              >
                <feature.icon size={26} className="text-white" />
              </div>
              <h3 className="text-xl font-bold mb-2">{feature.title}</h3>
              <p className="text-slate-400 leading-relaxed">{feature.description}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative z-10 max-w-5xl mx-auto px-8 py-24">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          className="relative rounded-[2.5rem] bg-gradient-to-br from-indigo-600 via-purple-600 to-pink-600 p-12 md:p-16 text-center overflow-hidden"
        >
          {/* Glow effects */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent" />
          <div className="absolute -top-20 -right-20 w-60 h-60 bg-white/10 rounded-full blur-3xl" />
          <div className="absolute -bottom-20 -left-20 w-60 h-60 bg-white/10 rounded-full blur-3xl" />

          <div className="relative z-10">
            <h2 className="text-4xl md:text-5xl font-black mb-4">
              Prêt à révolutionner votre industrie?
            </h2>
            <p className="text-xl text-white/80 max-w-xl mx-auto mb-8">
              Rejoignez les entreprises qui transforment leurs projets industriels avec RIBIF.
            </p>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => router.push("/auth/register")}
              className="px-10 py-5 bg-white text-slate-900 rounded-full text-lg font-bold shadow-2xl hover:shadow-white/25 transition-shadow"
            >
              Démarrer maintenant — C'est gratuit
            </motion.button>
          </div>
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 border-t border-white/10 py-8 px-8">
        <div className="max-w-7xl mx-auto flex items-center justify-between text-sm text-slate-500">
          <span>© 2026 RIBIF. Tous droits réservés.</span>
          <div className="flex items-center gap-6">
            <a href="#" className="hover:text-white transition-colors">Confidentialité</a>
            <a href="#" className="hover:text-white transition-colors">Conditions</a>
            <a href="#" className="hover:text-white transition-colors">Contact</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
