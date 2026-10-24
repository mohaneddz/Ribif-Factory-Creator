"use client";

import React, { useState, useEffect, useRef, useMemo } from "react";
import {
    Activity, Zap, Thermometer, Box, TrendingUp, AlertTriangle,
    Settings2, Play, Pause, RefreshCw, BarChart3, Clock,
    Hammer, Volume2, ShieldCheck, Gauge, type LucideIcon
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, AreaChart, Area, BarChart, Bar, Cell
} from 'recharts';
import Simple3DViewer from "@/components/Simple3DViewer";
import {
    generateTelemetry, TelemetryData, SimulationParams, DEFAULT_SIM_PARAMS
} from "@/utils/digitalTwinUtils";

interface DigitalTwinViewProps {
    pipelineModelUrl?: string | null;
}

const MetricCard = ({
    label, value, unit, icon: Icon, color, trend, iconBg
}: {
    label: string, value: string | number, unit: string, icon: LucideIcon, color: string, trend?: string, iconBg: string
}) => (
    <div className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 p-3 sm:p-4 rounded-xl sm:rounded-2xl shadow-sm hover:shadow-md transition-shadow">
        <div className="flex justify-between items-start mb-1 sm:mb-2">
            <div className={`p-1.5 sm:p-2 rounded-lg sm:rounded-xl ${iconBg} ${color}`}>
                <Icon className="w-4 h-4 sm:w-[18px] sm:h-[18px]" />
            </div>
            {trend && (
                <span className={`text-[9px] sm:text-[10px] font-bold px-1 sm:px-1.5 py-0.5 rounded-md ${trend.startsWith('+') ? 'bg-emerald-50 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400' : 'bg-rose-50 dark:bg-rose-500/20 text-rose-600 dark:text-rose-400'}`}>
                    {trend}
                </span>
            )}
        </div>
        <div>
            <div className="text-[9px] sm:text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-0.5 truncate">{label}</div>
            <div className="flex items-baseline gap-1">
                <span className="text-base sm:text-xl font-black text-slate-900 dark:text-white">{value}</span>
                <span className="text-[10px] sm:text-xs font-bold text-slate-400">{unit}</span>
            </div>
        </div>
    </div>
);

export function DigitalTwinView({ pipelineModelUrl }: DigitalTwinViewProps) {
    const [isPlaying, setIsPlaying] = useState(true);
    const [params, setParams] = useState<SimulationParams>(DEFAULT_SIM_PARAMS);
    const [history, setHistory] = useState<TelemetryData[]>([]);
    const [currentData, setCurrentData] = useState<TelemetryData | null>(null);
    const timeStepRef = useRef(0);
    const [elapsedSteps, setElapsedSteps] = useState(0);

    const boundingboxStart = useMemo(() => ({ x: -10, y: 0, z: -10 }), []);
    const boundingboxEnd = useMemo(() => ({ x: 10, y: 7, z: 0 }), []);

    // Simulation Loop
    useEffect(() => {
        if (!isPlaying) return;

        const interval = setInterval(() => {
            const newData = generateTelemetry(params, timeStepRef.current);
            timeStepRef.current += 1;
            setElapsedSteps(timeStepRef.current);

            setCurrentData(newData);
            setHistory(prev => {
                const newHistory = [...prev, newData];
                if (newHistory.length > 50) return newHistory.slice(1);
                return newHistory;
            });
        }, 1000);

        return () => clearInterval(interval);
    }, [isPlaying, params]);

    return (
        <div className="h-full flex flex-col p-3 sm:p-4 md:p-6 gap-3 sm:gap-4 md:gap-6 bg-slate-50 dark:bg-transparent overflow-y-auto">
            {/* TOP SECTION: 3D + KEY METRICS */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 sm:gap-4 md:gap-6 min-h-[280px] sm:min-h-[320px] lg:min-h-[400px]">
                {/* 3D Viewer (1/4th of page width approx) */}
                <div className="col-span-1 lg:col-span-4 h-[250px] sm:h-[300px] lg:h-auto bg-white dark:bg-[#1f2937] rounded-2xl sm:rounded-3xl border border-slate-200 dark:border-white/5 shadow-sm overflow-hidden relative">
                    <div className="absolute top-2 sm:top-4 left-2 sm:left-4 z-10 flex items-center gap-1.5 sm:gap-2 px-2 sm:px-3 py-1 sm:py-1.5 bg-white/80 dark:bg-black/40 backdrop-blur-md rounded-full border border-slate-200 dark:border-white/10">
                        <div className={`w-1.5 sm:w-2 h-1.5 sm:h-2 rounded-full ${isPlaying ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400'}`} />
                        <span className="text-[8px] sm:text-[10px] font-bold text-slate-700 dark:text-slate-200 uppercase tracking-widest">
                            {isPlaying ? 'Live' : 'Paused'}
                        </span>
                    </div>

                    <Simple3DViewer
                        boundingboxStart={boundingboxStart}
                        boundingboxEnd={boundingboxEnd}
                        pipelineModel={pipelineModelUrl || undefined}
                        className="w-full h-full"
                    />

                    <div className="absolute bottom-2 sm:bottom-4 left-2 sm:left-4 right-2 sm:right-4 z-10 flex justify-between items-center">
                        <button
                            onClick={() => setIsPlaying(!isPlaying)}
                            className="p-2 sm:p-2.5 bg-indigo-600 text-white rounded-lg sm:rounded-xl shadow-lg hover:bg-indigo-500 transition-colors"
                        >
                            {isPlaying ? <Pause className="w-4 h-4 sm:w-[18px] sm:h-[18px]" fill="currentColor" /> : <Play className="w-4 h-4 sm:w-[18px] sm:h-[18px]" fill="currentColor" />}
                        </button>
                        <div className="flex gap-2">
                            <button className="p-2 sm:p-2.5 bg-white/90 dark:bg-white/10 backdrop-blur rounded-lg sm:rounded-xl border border-slate-200 dark:border-white/10 text-slate-600 dark:text-slate-300">
                                <Settings2 className="w-4 h-4 sm:w-[18px] sm:h-[18px]" />
                            </button>
                        </div>
                    </div>
                </div>

                {/* METRICS GRID */}
                <div className="col-span-1 lg:col-span-8 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 sm:gap-3 md:gap-4">
                    <MetricCard
                        label="Température"
                        value={currentData?.temperature.toFixed(1) || "0"}
                        unit="°C"
                        icon={Thermometer}
                        color="text-rose-600"
                        iconBg="bg-rose-50"
                        trend={currentData ? (currentData.temperature > params.tempTarget ? "+0.5%" : "-0.2%") : undefined}
                    />
                    <MetricCard
                        label="Consommation"
                        value={currentData?.powerUsage.toFixed(1) || "0"}
                        unit="kW"
                        icon={Zap}
                        color="text-amber-500"
                        iconBg="bg-amber-50"
                    />
                    <MetricCard
                        label="Device Usage"
                        value={currentData?.deviceUsage.toFixed(1) || "0"}
                        unit="%"
                        icon={TrendingUp}
                        color="text-indigo-600"
                        iconBg="bg-indigo-50"
                    />
                    <MetricCard
                        label="Production Rate"
                        value={currentData?.productionRate.toFixed(0) || "0"}
                        unit="u/hr"
                        icon={Box}
                        color="text-emerald-600"
                        iconBg="bg-emerald-50"
                    />
                    <MetricCard
                        label="Vibration"
                        value={currentData?.vibration.toFixed(2) || "0"}
                        unit="G"
                        icon={Activity}
                        color="text-orange-500"
                        iconBg="bg-orange-50"
                    />
                    <MetricCard
                        label="Sound Level"
                        value={currentData?.soundLevel.toFixed(1) || "0"}
                        unit="dB"
                        icon={Volume2}
                        color="text-blue-500"
                        iconBg="bg-blue-50"
                    />
                    <MetricCard
                        label="Error Rate"
                        value={currentData?.errorRate.toFixed(2) || "0"}
                        unit="%"
                        icon={AlertTriangle}
                        color="text-red-500"
                        iconBg="bg-red-50"
                    />
                    <MetricCard
                        label="Remaining Life"
                        value={currentData?.remainingLife.toFixed(1) || "0"}
                        unit="%"
                        icon={Gauge}
                        color="text-slate-600"
                        iconBg="bg-slate-100"
                    />
                </div>
            </div>

            {/* MIDDLE SECTION: CHARTS */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 sm:gap-4 md:gap-6">
                <div className="bg-white dark:bg-[#1f2937] p-4 sm:p-6 rounded-2xl sm:rounded-3xl border border-slate-200 dark:border-white/5 shadow-sm">
                    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 sm:gap-0 mb-4 sm:mb-6">
                        <div className="flex items-center gap-2">
                            <BarChart3 className="w-4 h-4 sm:w-[18px] sm:h-[18px] text-indigo-600" />
                            <h3 className="text-sm sm:text-base font-bold text-slate-800 dark:text-white">Trend Analytics</h3>
                        </div>
                        <div className="flex gap-1.5 sm:gap-2">
                            <div className="flex items-center gap-1 sm:gap-1.5 text-[9px] sm:text-[10px] font-bold text-slate-500 bg-slate-50 dark:bg-white/5 px-1.5 sm:px-2 py-0.5 sm:py-1 rounded-md">
                                <div className="w-1.5 sm:w-2 h-1.5 sm:h-2 rounded-full bg-rose-500" /> Temp
                            </div>
                            <div className="flex items-center gap-1 sm:gap-1.5 text-[9px] sm:text-[10px] font-bold text-slate-500 bg-slate-50 dark:bg-white/5 px-1.5 sm:px-2 py-0.5 sm:py-1 rounded-md">
                                <div className="w-1.5 sm:w-2 h-1.5 sm:h-2 rounded-full bg-indigo-500" /> Power
                            </div>
                        </div>
                    </div>
                    <div className="h-48 sm:h-56 md:h-64 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={history}>
                                <defs>
                                    <linearGradient id="colorTemp" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.1} />
                                        <stop offset="95%" stopColor="#f43f5e" stopOpacity={0} />
                                    </linearGradient>
                                    <linearGradient id="colorPower" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#6366f1" stopOpacity={0.1} />
                                        <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                                <XAxis dataKey="timestamp" hide />
                                <YAxis axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 10 }} />
                                <Tooltip
                                    contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)' }}
                                />
                                <Area type="monotone" dataKey="temperature" stroke="#f43f5e" strokeWidth={2} fillOpacity={1} fill="url(#colorTemp)" />
                                <Area type="monotone" dataKey="powerUsage" stroke="#6366f1" strokeWidth={2} fillOpacity={1} fill="url(#colorPower)" />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                <div className="bg-white dark:bg-[#1f2937] p-4 sm:p-6 rounded-2xl sm:rounded-3xl border border-slate-200 dark:border-white/5 shadow-sm">
                    <div className="flex justify-between items-center mb-4 sm:mb-6">
                        <div className="flex items-center gap-2">
                            <Activity className="w-4 h-4 sm:w-[18px] sm:h-[18px] text-indigo-600" />
                            <h3 className="text-sm sm:text-base font-bold text-slate-800 dark:text-white">Performance Stability</h3>
                        </div>
                    </div>
                    <div className="h-48 sm:h-56 md:h-64 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={history}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                                <XAxis dataKey="timestamp" hide />
                                <YAxis axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 10 }} />
                                <Tooltip />
                                <Line type="monotone" dataKey="deviceUsage" stroke="#10b981" strokeWidth={2} dot={false} />
                                <Line type="monotone" dataKey="vibration" stroke="#f59e0b" strokeWidth={2} dot={false} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>

            {/* BOTTOM SECTION: SIMULATION CONTROLS */}
            <div className="bg-slate-900 rounded-2xl sm:rounded-3xl p-4 sm:p-6 md:p-8 text-white relative overflow-visible">
                <div className="absolute top-0 right-0 w-48 sm:w-64 h-48 sm:h-64 bg-indigo-500 rounded-full blur-[100px] opacity-10 pointer-events-none" />
                <div className="relative z-10">
                    <div className="flex items-center gap-2 sm:gap-3 mb-4 sm:mb-6">
                        <Settings2 className="w-4 h-4 sm:w-5 sm:h-5 text-indigo-400" />
                        <h3 className="text-sm sm:text-base md:text-lg font-bold">Dynamic Simulation Control</h3>
                    </div>

                    <div className="grid grid-cols-1 xs:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 md:gap-8">
                        <div className="space-y-3 sm:space-y-4">
                            <div className="flex justify-between items-center">
                                <label className="text-[10px] sm:text-xs font-bold text-slate-400 uppercase truncate mr-2">Target Temp</label>
                                <span className="text-[10px] sm:text-xs font-mono font-bold text-indigo-400 whitespace-nowrap">{params.tempTarget}°C</span>
                            </div>
                            <input
                                type="range" min="20" max="150"
                                value={params.tempTarget}
                                onChange={(e) => setParams({ ...params, tempTarget: Number(e.target.value) })}
                                className="w-full h-2 sm:h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                            />
                        </div>
                        <div className="space-y-3 sm:space-y-4">
                            <div className="flex justify-between items-center">
                                <label className="text-[10px] sm:text-xs font-bold text-slate-400 uppercase truncate mr-2">Base Power</label>
                                <span className="text-[10px] sm:text-xs font-mono font-bold text-indigo-400 whitespace-nowrap">{params.powerBase}kW</span>
                            </div>
                            <input
                                type="range" min="0" max="500"
                                value={params.powerBase}
                                onChange={(e) => setParams({ ...params, powerBase: Number(e.target.value) })}
                                className="w-full h-2 sm:h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                            />
                        </div>
                        <div className="space-y-3 sm:space-y-4">
                            <div className="flex justify-between items-center">
                                <label className="text-[10px] sm:text-xs font-bold text-slate-400 uppercase truncate mr-2">Usage Goal</label>
                                <span className="text-[10px] sm:text-xs font-mono font-bold text-indigo-400 whitespace-nowrap">{params.usageTarget}%</span>
                            </div>
                            <input
                                type="range" min="0" max="100"
                                value={params.usageTarget}
                                onChange={(e) => setParams({ ...params, usageTarget: Number(e.target.value) })}
                                className="w-full h-2 sm:h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                            />
                        </div>
                        <div className="space-y-3 sm:space-y-4">
                            <div className="flex justify-between items-center">
                                <label className="text-[10px] sm:text-xs font-bold text-slate-400 uppercase truncate mr-2">Prod Rate</label>
                                <span className="text-[10px] sm:text-xs font-mono font-bold text-indigo-400 whitespace-nowrap">{params.prodRateBase}u/h</span>
                            </div>
                            <input
                                type="range" min="0" max="1000"
                                value={params.prodRateBase}
                                onChange={(e) => setParams({ ...params, prodRateBase: Number(e.target.value) })}
                                className="w-full h-2 sm:h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                            />
                        </div>
                    </div>

                    <div className="mt-4 sm:mt-6 md:mt-8 pt-4 sm:pt-6 border-t border-white/5 flex flex-wrap gap-3 sm:gap-4">
                        <div className="flex items-center gap-1.5 sm:gap-2 text-[10px] sm:text-xs font-medium text-slate-400">
                            <ShieldCheck className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-emerald-500 flex-shrink-0" />
                            <span className="text-emerald-500">Normal</span>
                        </div>
                        <div className="flex items-center gap-1.5 sm:gap-2 text-[10px] sm:text-xs font-medium text-slate-400">
                            <Hammer className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-indigo-400 flex-shrink-0" />
                            <span className="text-indigo-400">{currentData && currentData.vibration > 4 ? 'High' : 'Low'}</span>
                        </div>
                        <div className="flex items-center gap-1.5 sm:gap-2 text-[10px] sm:text-xs font-medium text-slate-400">
                            <Clock className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-slate-400 flex-shrink-0" />
                            <span className="text-white">{(elapsedSteps / 60).toFixed(1)}m</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
