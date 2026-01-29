import { clsx } from "clsx";

export default function Card({ children, className, title }: { children: React.ReactNode, className?: string, title?: string }) {
    return (
        <div className={clsx("bg-slate-800 border border-slate-700 rounded-lg p-4 shadow-xl", className)}>
            {title && <h3 className="text-slate-400 text-xs uppercase tracking-wider font-bold mb-3">{title}</h3>}
            {children}
        </div>
    );
}