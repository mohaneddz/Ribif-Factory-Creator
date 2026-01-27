"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, Network, Box } from "lucide-react";

export default function Navbar() {
    const pathname = usePathname();

    const navClass = (path: string) =>
        `flex items-center gap-2 px-4 py-2 rounded-md transition-all ${
            pathname === path 
                ? "bg-blue-600 text-white" 
                : "text-slate-500 hover:text-slate-800 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-white dark:hover:bg-slate-800"
        }`;

    return (
        <nav className="h-16 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 flex items-center justify-between px-6 fixed w-full top-0 z-50 transition-colors">
            <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-blue-500 rounded flex items-center justify-center font-bold text-white dark:text-slate-900">AM</div>
                <div>
                    <h1 className="font-bold text-sm tracking-widest text-slate-900 dark:text-white">ALLO MAISON</h1>
                    <p className="text-[10px] text-blue-600 dark:text-blue-400">CERVEAU DIGITAL 5.0</p>
                </div>
            </div>

            <div className="flex gap-2">
                <Link href="/" className={navClass("/")}>
                    <Activity size={18} />
                    <span className="text-sm font-medium">Digital Twin</span>
                </Link>
                <Link href="/projects/new" className={navClass("/projects/new")}>
                    <Network size={18} />
                    <span className="text-sm font-medium">Nouveau Projet</span>
                </Link>
            </div>

            <div className="flex items-center gap-3">
        <span className="text-xs px-2 py-1 bg-green-100 text-green-700 border border-green-200 dark:bg-green-900 dark:text-green-400 dark:border-green-700 rounded transition-colors">
          SYSTEM ONLINE
        </span>
            </div>
        </nav>
    );
}
