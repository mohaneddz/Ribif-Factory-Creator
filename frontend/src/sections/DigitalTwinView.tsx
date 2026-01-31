"use client";

import React, { useState, useEffect, useRef, useMemo } from "react";
import {
    Activity, Zap, Thermometer, Box, TrendingUp, AlertTriangle,
    Settings2, Play, Pause, RefreshCw, BarChart3, Clock,
    Hammer, Volume2, ShieldCheck, Gauge
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

export function DigitalTwinView({ pipelineModelUrl }: DigitalTwinViewProps) {
    const [isPlaying, setIsPlaying] = useState(true);
    const [params, setParams] = useState<SimulationParams>(DEFAULT_SIM_PARAMS);
    const [history, setHistory] = useState<TelemetryData[]>([]);
    const [currentData, setCurrentData] = useState<TelemetryData | null>(null);
    const timeStepRef = useRef(0);

    const boundingboxStart = useMemo(() => ({ x: -10, y: 0, z: -10 }), []);
    const boundingboxEnd = useMemo(() => ({ x: 10, y: 7, z: 0 }), []);

    // Simulation Loop
    useEffect(() => {
        if (!isPlaying) return;

        const interval = setInterval(() => {
            const newData = generateTelemetry(params, timeStepRef.current);
            timeStepRef.current += 1;

            setCurrentData(newData);
            setHistory(prev => {
                const newHistory = [...prev, newData];
                if (newHistory.length > 50) return newHistory.slice(1);
                return newHistory;
            });
        }, 1000);

        return () => clearInterval(interval);
    }, [isPlaying, params]);

    const MetricCard = ({
        label, value, unit, icon: Icon, color, trend, iconBg
    }: {
        label: string, value: string | number, unit: string, icon: any, color: string, trend?: string, iconBg: string
    }) => (
        <div className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 p-4 rounded-2xl shadow-sm">
            <div className="flex justify-between items-start mb-2">
                <div className={`p-2 rounded-xl ${iconBg} ${color}`}>
                    <Icon size={18} />
                </div>
                {trend && (
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-md ${trend.startsWith('+') ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-600'}`}>
                        {trend}
                    </span>
                )}
            </div>
            <div>
                <div className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-0.5">{label}</div>
                <div className="flex items-baseline gap-1">
                    <span className="text-xl font-black text-slate-900 dark:text-white">{value}</span>
                    <span className="text-xs font-bold text-slate-400">{unit}</span>
                </div>
            </div>
        </div>
    );

    return (
        <div className="h-full flex flex-col p-6 gap-6 bg-slate-50 dark:bg-transparent overflow-y-auto">
            {/* TOP SECTION: 3D + KEY METRICS */}
            <div className="grid grid-cols-12 gap-6 min-h-[400px]">
                {/* 3D Viewer (1/4th of page width approx) */}
                <div className="col-span-12 lg:col-span-4 bg-white dark:bg-[#1f2937] rounded-3xl border border-slate-200 dark:border-white/5 shadow-sm overflow-hidden relative">
                    <div className="absolute top-4 left-4 z-10 flex items-center gap-2 px-3 py-1.5 bg-white/80 dark:bg-black/40 backdrop-blur-md rounded-full border border-slate-200 dark:border-white/10">
                        <div className={`w-2 h-2 rounded-full ${isPlaying ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400'}`} />
                        <span className="text-[10px] font-bold text-slate-700 dark:text-slate-200 uppercase tracking-widest">
                            {isPlaying ? 'Live Simulation' : 'Simulation Paused'}
                        </span>
                    </div>

                    <Simple3DViewer
                        boundingboxStart={boundingboxStart}
                        boundingboxEnd={boundingboxEnd}
                        pipelineModel={pipelineModelUrl || undefined}
                        className="w-full h-full"
                    />

                    <div className="absolute bottom-4 left-4 right-4 z-10 flex justify-between items-center">
                        <button
                            onClick={() => setIsPlaying(!isPlaying)}
                            className="p-2.5 bg-indigo-600 text-white rounded-xl shadow-lg hover:bg-indigo-500 transition-colors"
                        >
                            {isPlaying ? <Pause size={18} fill="currentColor" /> : <Play size={18} fill="currentColor" />}
                        </button>
                        <div className="flex gap-2">
                            <button className="p-2.5 bg-white/90 dark:bg-white/10 backdrop-blur rounded-xl border border-slate-200 dark:border-white/10 text-slate-600 dark:text-slate-300">
                                <Settings2 size={18} />
                            </button>
                        </div>
                    </div>
                </div>

                {/* METRICS GRID */}
                <div className="col-span-12 lg:col-span-8 grid grid-cols-2 md:grid-cols-4 gap-4">
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
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-white dark:bg-[#1f2937] p-6 rounded-3xl border border-slate-200 dark:border-white/5 shadow-sm">
                    <div className="flex justify-between items-center mb-6">
                        <div className="flex items-center gap-2">
                            <BarChart3 size={18} className="text-indigo-600" />
                            <h3 className="font-bold text-slate-800 dark:text-white">Trend Analytics</h3>
                        </div>
                        <div className="flex gap-2">
                            <div className="flex items-center gap-1.5 text-[10px] font-bold text-slate-500 bg-slate-50 dark:bg-white/5 px-2 py-1 rounded-md">
                                <div className="w-2 h-2 rounded-full bg-rose-500" /> Temp
                            </div>
                            <div className="flex items-center gap-1.5 text-[10px] font-bold text-slate-500 bg-slate-50 dark:bg-white/5 px-2 py-1 rounded-md">
                                <div className="w-2 h-2 rounded-full bg-indigo-500" /> Power
                            </div>
                        </div>
                    </div>
                    <div className="h-64 w-full">
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

                <div className="bg-white dark:bg-[#1f2937] p-6 rounded-3xl border border-slate-200 dark:border-white/5 shadow-sm">
                    <div className="flex justify-between items-center mb-6">
                        <div className="flex items-center gap-2">
                            <Activity size={18} className="text-indigo-600" />
                            <h3 className="font-bold text-slate-800 dark:text-white">Performance Stability</h3>
                        </div>
                    </div>
                    <div className="h-64 w-full">
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
            <div className="bg-slate-900 rounded-3xl p-8 text-white relative overflow-hidden">
                <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500 rounded-full blur-[100px] opacity-10" />
                <div className="relative z-10">
                    <div className="flex items-center gap-3 mb-6">
                        <Settings2 className="text-indigo-400" />
                        <h3 className="text-lg font-bold">Dynamic Simulation Control</h3>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
                        <div className="space-y-4">
                            <div className="flex justify-between">
                                <label className="text-xs font-bold text-slate-400 uppercase">Target Temp</label>
                                <span className="text-xs font-mono font-bold text-indigo-400">{params.tempTarget}°C</span>
                            </div>
                            <input
                                type="range" min="20" max="150"
                                value={params.tempTarget}
                                onChange={(e) => setParams({ ...params, tempTarget: Number(e.target.value) })}
                                className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                            />
                        </div>
                        <div className="space-y-4">
                            <div className="flex justify-between">
                                <label className="text-xs font-bold text-slate-400 uppercase">Base Power</label>
                                <span className="text-xs font-mono font-bold text-indigo-400">{params.powerBase}kW</span>
                            </div>
                            <input
                                type="range" min="0" max="500"
                                value={params.powerBase}
                                onChange={(e) => setParams({ ...params, powerBase: Number(e.target.value) })}
                                className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                            />
                        </div>
                        <div className="space-y-4">
                            <div className="flex justify-between">
                                <label className="text-xs font-bold text-slate-400 uppercase">Usage Goal</label>
                                <span className="text-xs font-mono font-bold text-indigo-400">{params.usageTarget}%</span>
                            </div>
                            <input
                                type="range" min="0" max="100"
                                value={params.usageTarget}
                                onChange={(e) => setParams({ ...params, usageTarget: Number(e.target.value) })}
                                className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                            />
                        </div>
                        <div className="space-y-4">
                            <div className="flex justify-between">
                                <label className="text-xs font-bold text-slate-400 uppercase">Prod Rate</label>
                                <span className="text-xs font-mono font-bold text-indigo-400">{params.prodRateBase}u/h</span>
                            </div>
                            <input
                                type="range" min="0" max="1000"
                                value={params.prodRateBase}
                                onChange={(e) => setParams({ ...params, prodRateBase: Number(e.target.value) })}
                                className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                            />
                        </div>
                    </div>

                    <div className="mt-8 pt-6 border-t border-white/5 flex flex-wrap gap-4">
                        <div className="flex items-center gap-2 text-xs font-medium text-slate-400">
                            <ShieldCheck size={14} className="text-emerald-500" /> IA Safety Checks: <span className="text-emerald-500">Normal</span>
                        </div>
                        <div className="flex items-center gap-2 text-xs font-medium text-slate-400">
                            <Hammer size={14} className="text-indigo-400" /> Maintenance Risk: <span className="text-indigo-400">{currentData && currentData.vibration > 4 ? 'High' : 'Low'}</span>
                        </div>
                        <div className="flex items-center gap-2 text-xs font-medium text-slate-400">
                            <Clock size={14} className="text-slate-400" /> Runtime: <span className="text-white">{(timeStepRef.current / 60).toFixed(1)} mins</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
