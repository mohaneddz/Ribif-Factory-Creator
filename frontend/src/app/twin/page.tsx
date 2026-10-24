"use client";

import { useState, useEffect, useRef, useMemo } from "react";
import dynamic from "next/dynamic";
import { useFrame } from "@react-three/fiber";
import {
    LayoutDashboard, AlertTriangle, ShieldCheck, Factory,
    BarChart3, BrainCircuit, Settings, Server, Wind, CheckCircle2, Calculator,
    TrendingUp, Activity, Zap, Clock, DollarSign, ArrowRight, Building, Home
} from "lucide-react";
import {
    ScatterChart, Scatter, XAxis, YAxis, ZAxis, CartesianGrid, Tooltip as RechartsTooltip,
    ResponsiveContainer, Cell, BarChart, Bar, Legend, AreaChart, Area, Line, ComposedChart
} from 'recharts';
import * as THREE from "three";
import clsx from "clsx";
import Scene from "@/components/three/scenes/Scene";

// Dynamic import for Canvas to disable SSR (fixes ReactDOM.render compatibility with React 19)
const Canvas = dynamic(
    () => import("@react-three/fiber").then((mod) => mod.Canvas),
    { ssr: false }
);
// ==========================================
// 0. STYLES
// ==========================================

const fontStyle = `
  @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&display=swap');
  
  body, div, button, input, select, table {
    font-family: 'Outfit', sans-serif;
  }
`;

// ==========================================
// 1. DATA MODEL & CONFIGURATION
// ==========================================

// TCO Data from analysis
const TCO_DATA = {
    company_name: "SARL ALLO MAISON",
    project_name: "ALLO MAISON – Complexe Industriel Polymère & Matériaux Avancés",
    calculation_date: "2025-12-28",
    total_tco: 14006740000.0,
    average_annual_tco: 2801348000.0,
    tco_per_unit_revenue: 28.0135,
    machine_tco: [
        {
            machine_id: "M-01",
            machine_name: "Machine d'injection plastique",
            category: "Presse à injection",
            manufacturer: "KraussMaffei",
            initial_cost: 105000000.0,
            operations_cost: 85200000.0,
            maintenance_cost: 55200000.0,
            downtime_cost: 14400000.0,
            resale_value: 16200000.0,
            total_tco: 243600000.0,
            annual_tco: 20300000.0,
            lifetime_years: 12,
            cost_breakdown: {
                initial_pct: 40.42,
                operations_pct: 32.79,
                maintenance_pct: 21.25,
                downtime_pct: 5.54,
                resale_offset_pct: 6.24
            },
            estimated_purchase_price: 81000000.0,
            estimation_confidence: "medium"
        }
    ],
    total_machines_tco: 243600000.0,
    product_tco: [
        { nom_produit: "Panneaux polymères et composites", categorie: "semi-finished", landing_cost: 8120000.0, holding_cost: 1015000.0, quality_cost: 609000.0, administrative_cost: 1624000.0, total_tco: 11368000.0 },
        { nom_produit: "Revêtements de sol SPC à système clic étanche", categorie: "finished", landing_cost: 8120000.0, holding_cost: 1015000.0, quality_cost: 609000.0, administrative_cost: 1624000.0, total_tco: 11368000.0 },
        { nom_produit: "Portes intérieures, extérieures, techniques et grand format", categorie: "finished", landing_cost: 8120000.0, holding_cost: 1015000.0, quality_cost: 609000.0, administrative_cost: 1624000.0, total_tco: 11368000.0 },
        { nom_produit: "Panneaux muraux décoratifs et techniques", categorie: "finished", landing_cost: 8120000.0, holding_cost: 1015000.0, quality_cost: 609000.0, administrative_cost: 1624000.0, total_tco: 11368000.0 },
        { nom_produit: "Pièces thermoformées", categorie: "semi-finished", landing_cost: 8120000.0, holding_cost: 1015000.0, quality_cost: 609000.0, administrative_cost: 1624000.0, total_tco: 11368000.0 }
    ],
    total_products_tco: 56840000.0,
    raw_materials_tco: [
        { nom_materiau: "Polyuréthane (PU)", type_materiau: "Résine polymère", total_tco: 526500000.0, annual_cost: 405000000.0, transport_cost: 101250000.0, storage_cost: 12150000.0, wastage_cost: 8100000.0, estimation_confidence: "medium" },
        { nom_materiau: "Polyurée (2K)", type_materiau: "Résine polymère", total_tco: 394875000.0, annual_cost: 303750000.0, transport_cost: 75937500.0, storage_cost: 9112500.0, wastage_cost: 6075000.0, estimation_confidence: "medium" },
        { nom_materiau: "Résines époxy", type_materiau: "Résine polymère", total_tco: 102060000.0, annual_cost: 81000000.0, transport_cost: 17820000.0, storage_cost: 1620000.0, wastage_cost: 1620000.0, estimation_confidence: "medium" },
        { nom_materiau: "Isocyanates", type_materiau: "Produit chimique", total_tco: 54675000.0, annual_cost: 40500000.0, transport_cost: 11340000.0, storage_cost: 1620000.0, wastage_cost: 1215000.0, estimation_confidence: "medium" },
        { nom_materiau: "Polyols", type_materiau: "Produit chimique", total_tco: 56133000.0, annual_cost: 44550000.0, transport_cost: 9801000.0, storage_cost: 891000.0, wastage_cost: 891000.0, estimation_confidence: "medium" },
        { nom_materiau: "Verre de sécurité laminé", type_materiau: "Matériau de construction", total_tco: 189000000.0, annual_cost: 135000000.0, transport_cost: 40500000.0, storage_cost: 6750000.0, wastage_cost: 6750000.0, estimation_confidence: "medium" },
        { nom_materiau: "UTG (verre ultra-mince flexible)", type_materiau: "Matériau de construction", total_tco: 530550000.0, annual_cost: 405000000.0, transport_cost: 101250000.0, storage_cost: 12150000.0, wastage_cost: 12150000.0, estimation_confidence: "low" },
        { nom_materiau: "PVC", type_materiau: "Matériau polymère", total_tco: 215865000.0, annual_cost: 175500000.0, transport_cost: 35100000.0, storage_cost: 3510000.0, wastage_cost: 1755000.0, estimation_confidence: "high" },
        { nom_materiau: "SPC", type_materiau: "Matériau polymère", total_tco: 168750000.0, annual_cost: 135000000.0, transport_cost: 29700000.0, storage_cost: 2700000.0, wastage_cost: 1350000.0, estimation_confidence: "medium" },
        { nom_materiau: "ABS", type_materiau: "Matériau polymère", total_tco: 185625000.0, annual_cost: 148500000.0, transport_cost: 32670000.0, storage_cost: 2970000.0, wastage_cost: 1485000.0, estimation_confidence: "high" },
        { nom_materiau: "PC", type_materiau: "Matériau polymère", total_tco: 118125000.0, annual_cost: 94500000.0, transport_cost: 20790000.0, storage_cost: 1890000.0, wastage_cost: 945000.0, estimation_confidence: "medium" }
    ],
    total_raw_materials_tco: 2695788000.0,
    annual_tco: [
        { year: 1, machines_tco: 20300000.0, products_tco: 56840000.0, raw_materials_tco: 2695788000.0, total_tco: 2772928000.0, cumulative_tco: 2772928000.0 },
        { year: 2, machines_tco: 21721000.0, products_tco: 60818800.0, raw_materials_tco: 2884493160.0, total_tco: 2967032960.0, cumulative_tco: 5739960960.0 },
        { year: 3, machines_tco: 23241470.0, products_tco: 65076116.0, raw_materials_tco: 3086407681.2, total_tco: 3174725267.2, cumulative_tco: 8914686227.2 },
        { year: 4, machines_tco: 24868372.9, products_tco: 69631444.12, raw_materials_tco: 3302456218.88, total_tco: 3396956035.9, cumulative_tco: 12311642263.1 },
        { year: 5, machines_tco: 26609159.0, products_tco: 74505645.21, raw_materials_tco: 3533628154.21, total_tco: 3634742958.42, cumulative_tco: 15946385221.52 }
    ]
};

const INITIAL_MACHINES = [
    {
        id: "M-01", name: "Machine d'injection plastique", zone: "Injection", status: "running",
        health: 93.8, temp: 52, vibration: 2.22, power: 85, atex: false,
        capex: 105000000, mtbf: 2500, oee: 88, cycleTime: 12.5
    },
    {
        id: "EXT-120-01", name: "Extrudeuse 120mm SPC", zone: "Extrusion", status: "running",
        health: 85.8, temp: 65, vibration: 1.63, power: 78, atex: false,
        capex: 210000, mtbf: 1800, oee: 82, cycleTime: 0
    },
    {
        id: "THF-2000-01", name: "Thermoformeuse 2000", zone: "Thermoformage", status: "idle",
        health: 77.9, temp: 24, vibration: 0.05, power: 5, atex: false,
        capex: 180000, mtbf: 2100, oee: 75, cycleTime: 4.2
    },
    {
        id: "PNT-KUKA-01", name: "Robot Peinture KUKA", zone: "Peinture", status: "running",
        health: 98.2, temp: 45, vibration: 0.8, power: 22, atex: true,
        capex: 85000, mtbf: 5000, oee: 94, cycleTime: 8.0
    },
    {
        id: "STK-SOLV-01", name: "Stockage Solvants", zone: "Stockage", status: "safe",
        health: 100, temp: 18, vibration: 0, power: 2, atex: true,
        capex: 45000, mtbf: 9999, oee: 100, cycleTime: 0
    },
    {
        id: "RCY-GRIND-01", name: "Broyeur Recyclage", zone: "Recyclage", status: "warning",
        health: 62.4, temp: 85, vibration: 4.5, power: 90, atex: false,
        capex: 65000, mtbf: 900, oee: 55, cycleTime: 0
    },
];

const formatEUR = (num: number) => new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(num);
const formatDZD = (num: number) => new Intl.NumberFormat('fr-DZ', { maximumFractionDigits: 0 }).format(num) + ' DZD';
const formatBillion = (num: number) => {
    if (num >= 1e9) return (num / 1e9).toFixed(2) + ' Mrd DZD';
    if (num >= 1e6) return (num / 1e6).toFixed(2) + ' M DZD';
    return formatDZD(num);
};

// ==========================================
// 2. 3D COMPONENTS
// ==========================================

const RobotArm = ({ position, delay = 0 }: { position: [number, number, number], delay?: number }) => {
    const group = useRef<THREE.Group>(null);
    const arm1 = useRef<THREE.Mesh>(null);
    const arm2 = useRef<THREE.Mesh>(null);

    useFrame(({ clock }) => {
        const t = clock.getElapsedTime() + delay;
        if (group.current) group.current.rotation.y = Math.sin(t * 0.5) * 0.5 + Math.PI;
        if (arm1.current) arm1.current.rotation.x = Math.sin(t * 1) * 0.3;
        if (arm2.current) arm2.current.rotation.x = Math.sin(t * 1.5) * 0.5;
    });

    return (
        <group position={position} ref={group}>
            <mesh castShadow receiveShadow position={[0, 0.25, 0]}>
                <cylinderGeometry args={[0.6, 0.8, 0.5, 32]} />
                <meshStandardMaterial color="#475569" />
            </mesh>
            <group position={[0, 0.5, 0]}>
                <mesh castShadow position={[0, 0.5, 0]} ref={arm1}>
                    <boxGeometry args={[0.4, 1.5, 0.4]} />
                    <meshStandardMaterial color="#F59E0B" />
                    <group position={[0, 0.6, 0.2]}>
                        <mesh castShadow position={[0, 0.6, 0]} ref={arm2}>
                            <boxGeometry args={[0.3, 1.2, 0.3]} />
                            <meshStandardMaterial color="#F59E0B" />
                            <mesh position={[0, 0.7, 0]} rotation={[0, 0, Math.PI / 2]}>
                                <cylinderGeometry args={[0.1, 0.1, 0.6]} />
                                <meshStandardMaterial color="#94A3B8" />
                            </mesh>
                        </mesh>
                    </group>
                </mesh>
            </group>
        </group>
    );
};

const CNCMachine = ({ position, status = "running" }: { position: [number, number, number], status?: string }) => {
    return (
        <group position={position}>
            <mesh castShadow receiveShadow position={[0, 1, 0]}>
                <boxGeometry args={[2.5, 2, 2]} />
                <meshStandardMaterial color="#CBD5E1" metalness={0.5} roughness={0.2} />
            </mesh>
            <mesh position={[0, 1.2, 1.01]}>
                <planeGeometry args={[1.5, 1]} />
                <meshPhysicalMaterial color="#93C5FD" transmission={0.9} roughness={0} transparent opacity={0.5} />
            </mesh>
            <mesh position={[1, 2.2, 0.8]}>
                <cylinderGeometry args={[0.1, 0.1, 0.3]} />
                <meshStandardMaterial
                    color={status === 'running' ? "#10B981" : status === 'warning' ? "#F59E0B" : "#EF4444"}
                    emissive={status === 'running' ? "#10B981" : status === 'warning' ? "#F59E0B" : "#EF4444"}
                    emissiveIntensity={2}
                    toneMapped={false}
                />
            </mesh>
            <mesh position={[-0.8, 1, 1.05]} rotation={[-0.2, 0, 0]}>
                <boxGeometry args={[0.5, 0.4, 0.1]} />
                <meshStandardMaterial color="#1E293B" />
            </mesh>
        </group>
    );
};

const ConveyorBelt = ({ position, length = 10 }: { position: [number, number, number], length?: number }) => {
    return (
        <group position={position}>
            <mesh position={[0, 0.5, 0]} receiveShadow castShadow>
                <boxGeometry args={[length, 0.2, 1.5]} />
                <meshStandardMaterial color="#475569" />
            </mesh>
            {Array.from({ length: Math.ceil(length / 3) }).map((_, i) => (
                <mesh key={i} position={[-length / 2 + 1 + i * 3, 0.25, 0]} castShadow>
                    <cylinderGeometry args={[0.1, 0.1, 0.5]} />
                    <meshStandardMaterial color="#334155" />
                </mesh>
            ))}
        </group>
    );
};

const MovingProduct = ({ offset, zPath }: { offset: number, zPath: number }) => {
    const ref = useRef<THREE.Mesh>(null);
    useFrame(({ clock }) => {
        if (ref.current) {
            const t = (clock.getElapsedTime() * 2 + offset) % 20;
            ref.current.position.x = t - 10;
        }
    });
    return (
        <mesh ref={ref} position={[-10, 0.8, zPath]} castShadow>
            <boxGeometry args={[0.6, 0.4, 0.6]} />
            <meshStandardMaterial color="#4F46E5" />
        </mesh>
    );
};

const AGV = () => {
    const ref = useRef<THREE.Group>(null);
    useFrame(({ clock }) => {
        if (ref.current) {
            const t = clock.getElapsedTime() * 0.5;
            ref.current.position.x = Math.sin(t) * 8;
            ref.current.position.z = Math.cos(t) * 4 + 4;
            ref.current.rotation.y = Math.atan2(Math.cos(t) * -4, Math.cos(t) * 8) + Math.PI;
        }
    });
    return (
        <group ref={ref} position={[0, 0.15, 0]}>
            <mesh castShadow receiveShadow position={[0, 0.2, 0]}>
                <boxGeometry args={[1.2, 0.4, 0.8]} />
                <meshStandardMaterial color="#FACC15" />
            </mesh>
            <mesh position={[0.4, 0.1, 0.4]} rotation={[Math.PI / 2, 0, 0]}><cylinderGeometry args={[0.1, 0.1, 0.1]} /><meshStandardMaterial color="black" /></mesh>
            <mesh position={[-0.4, 0.1, 0.4]} rotation={[Math.PI / 2, 0, 0]}><cylinderGeometry args={[0.1, 0.1, 0.1]} /><meshStandardMaterial color="black" /></mesh>
            <mesh position={[0, 0.55, 0]}>
                <boxGeometry args={[0.8, 0.5, 0.6]} />
                <meshStandardMaterial color="#94A3B8" wireframe />
            </mesh>
        </group>
    );
};

const ComplexFactoryScene = ({ machineStates, viewMode = 'exterior' }: { machineStates: any[], viewMode?: 'exterior' | 'interior' }) => {
    const cnc1Status = machineStates.find(m => m.id === "INJ-100T-01")?.status || "running";
    const cnc2Status = machineStates.find(m => m.id === "EXT-120-01")?.status || "running";
    const cnc3Status = machineStates.find(m => m.id === "RCY-GRIND-01")?.status || "warning";

    return (
        <>
            <Scene viewMode={viewMode} />
        </>
    );
};

// ==========================================
// 3. MAIN DASHBOARD COMPONENT
// ==========================================

const Header = ({ title, subtitle }: { title: string, subtitle: string }) => (
    <div className="bg-white border-b border-slate-200 px-8 py-6 mb-8 flex justify-between items-center sticky top-0 z-30">
        <div>
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">{title}</h1>
            <p className="text-sm font-medium text-slate-500">{subtitle}</p>
        </div>
        <div className="flex gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-50 border border-emerald-100">
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-xs font-bold text-emerald-700 uppercase tracking-wide">Live Connection</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-100 border border-slate-200">
                <ShieldCheck size={14} className="text-indigo-600" />
                <span className="text-xs font-bold text-slate-600 uppercase tracking-wide">Secure</span>
            </div>
        </div>
    </div>
);

export default function TwinDashboard() {
    const [view, setView] = useState<'overview' | 'machines' | 'maintenance' | 'safety' | 'tco'>('overview');
    const [selectedMachineId, setSelectedMachineId] = useState<string>(INITIAL_MACHINES[0].id);
    const [machines, setMachines] = useState(INITIAL_MACHINES);
    const [viewMode, setViewMode] = useState<'exterior' | 'interior'>('exterior');

    const [tcoParams, setTcoParams] = useState({
        years: 10,
        energyCostPerKwh: 0.15,
        maintenanceRate: 0.05,
        hoursPerYear: 6000
    });

    // Real-time simulation parameters
    const [voltage, setVoltage] = useState(220);
    const [energyCost, setEnergyCost] = useState(12); // DZD per kWh
    const [realtimeCostAccumulator, setRealtimeCostAccumulator] = useState(0);

    // Real-time chart data history (last 12 data points)
    const [chartHistory, setChartHistory] = useState<Array<{
        time: string;
        operations: number;
        maintenance: number;
        energy: number;
        total: number;
    }>>([]);

    // Update realtime data every 5 seconds
    useEffect(() => {
        // Initialize with some data points
        const initData = [];
        for (let i = 11; i >= 0; i--) {
            const baseOps = TCO_DATA.machine_tco[0].operations_cost / 365 / 24 / 12;
            const baseMaint = TCO_DATA.machine_tco[0].maintenance_cost / 365 / 24 / 12;
            const variation = 0.9 + Math.random() * 0.2;
            initData.push({
                time: `-${i * 5}s`,
                operations: baseOps * variation,
                maintenance: baseMaint * (0.95 + Math.random() * 0.1),
                energy: (220 + (Math.random() - 0.5) * 20) * 85 * 12 / 1000 * 5,
                total: 0
            });
        }
        initData.forEach(d => d.total = d.operations + d.maintenance + d.energy);
        // Seeded after mount: random values in a useState initializer would mismatch the server render
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setChartHistory(initData);

        const interval = setInterval(() => {
            // Random voltage fluctuation (±5%)
            setVoltage(prev => {
                const fluctuation = (Math.random() - 0.5) * 22;
                return Math.max(200, Math.min(240, prev + fluctuation));
            });

            // Get selected machine's power
            const selectedMachine = machines.find(m => m.id === selectedMachineId);
            const machinePower = selectedMachine?.power || 85;

            // Calculate new cost based on voltage and energy cost
            setRealtimeCostAccumulator(prev => {
                const energyConsumed = machinePower * 5 / 3600; // kWh for 5 seconds
                return prev + (energyConsumed * energyCost * 1000); // Convert to DZD
            });

            // Update chart history
            setChartHistory(prev => {
                const baseOps = TCO_DATA.machine_tco[0].operations_cost / 365 / 24 / 12;
                const baseMaint = TCO_DATA.machine_tco[0].maintenance_cost / 365 / 24 / 12;
                const voltageEffect = voltage / 220; // Higher voltage = higher cost
                const powerFactor = machinePower / 85; // Scale by power relative to base
                const newPoint = {
                    time: 'now',
                    operations: baseOps * voltageEffect * powerFactor * (0.95 + Math.random() * 0.1),
                    maintenance: baseMaint * powerFactor * (0.95 + Math.random() * 0.1),
                    energy: (voltage * machinePower * energyCost / 1000) * 5,
                    total: 0
                };
                newPoint.total = newPoint.operations + newPoint.maintenance + newPoint.energy;

                const newHistory = [...prev.slice(1), newPoint];
                // Update time labels
                return newHistory.map((d, i) => ({
                    ...d,
                    time: i === 11 ? 'now' : `-${(11 - i) * 5}s`
                }));
            });
        }, 5000);

        return () => clearInterval(interval);
    }, [voltage, energyCost, selectedMachineId, machines]);

    useEffect(() => {
        const interval = setInterval(() => {
            setMachines(prev => prev.map(m => {
                const tempFluctuation = (Math.random() - 0.5) * 2;
                const vibFluctuation = (Math.random() - 0.5) * 0.1;
                const powerFluctuation = (Math.random() - 0.5) * 5;

                let newStatus = m.status;
                const newTemp = Math.max(20, Math.min(120, m.temp + tempFluctuation));
                let newHealth = m.health;

                if (newTemp > 90) newStatus = "warning";
                else if (m.id === "THF-2000-01") newStatus = "idle";
                else newStatus = "running";

                if (newStatus === "warning") newHealth = Math.max(0, m.health - 0.05);

                return {
                    ...m,
                    temp: Number(newTemp.toFixed(1)),
                    vibration: Math.max(0, Number((m.vibration + vibFluctuation).toFixed(2))),
                    power: Math.max(0, Math.round(m.power + powerFluctuation)),
                    health: Number(newHealth.toFixed(1)),
                    status: newStatus
                };
            }));
        }, 1000);
        return () => clearInterval(interval);
    }, []);

    const tcoData = useMemo(() => {
        const target = machines.find(m => m.id === selectedMachineId) || machines[0];
        const capex = target.capex;
        const energyAnnual = target.power * tcoParams.hoursPerYear * tcoParams.energyCostPerKwh;
        const maintAnnual = target.capex * tcoParams.maintenanceRate;
        const data = [];
        let cumEnergy = 0;
        let cumMaint = 0;
        for (let i = 1; i <= tcoParams.years; i++) {
            cumEnergy += energyAnnual;
            cumMaint += maintAnnual;
            data.push({
                year: `Y${i}`,
                CAPEX: capex,
                OPEX_Energy: Math.round(cumEnergy),
                OPEX_Maint: Math.round(cumMaint),
                Total: Math.round(capex + cumEnergy + cumMaint)
            });
        }
        const totalTCO = capex + cumEnergy + cumMaint;
        const costPerHour = totalTCO / (tcoParams.hoursPerYear * tcoParams.years);
        return { chartData: data, total: totalTCO, hourly: costPerHour, machine: target };
    }, [selectedMachineId, tcoParams, machines]);

    // Compute detailed TCO breakdown for selected machine
    const selectedMachineTco = useMemo(() => {
        const machine = machines.find(m => m.id === selectedMachineId) || machines[0];
        const baseTco = TCO_DATA.machine_tco[0];

        // Scale costs based on power relative to base (85 kW) - primary scaling factor
        const powerRatio = machine.power / 85;

        // Determine if capex is in EUR (small values) or DZD (large values)
        // If capex < 1M, assume it's in EUR and convert to DZD (approx 1 EUR = 145 DZD)
        const capexInDZD = machine.capex < 1000000 ? machine.capex * 145 : machine.capex;

        // Calculate costs based on power ratio and machine's investment
        const initial_cost = capexInDZD;
        const operations_cost = baseTco.operations_cost * powerRatio;
        const maintenance_cost = baseTco.maintenance_cost * powerRatio;
        const downtime_cost = baseTco.downtime_cost * powerRatio * (100 - machine.oee) / 12; // Factor in OEE
        const total = initial_cost + operations_cost + maintenance_cost + downtime_cost;
        const resale_value = initial_cost * 0.154; // ~15.4% resale value
        const total_tco = total - resale_value;
        const annual_tco = total_tco / 12;

        return {
            machine_id: machine.id,
            machine_name: machine.name,
            category: machine.zone,
            manufacturer: machine.id === "M-01" ? "KraussMaffei" :
                machine.id.includes("KUKA") ? "KUKA Robotics" :
                    machine.id.includes("EXT") ? "Battenfeld-Cincinnati" : "Industrial Co.",
            initial_cost,
            operations_cost,
            maintenance_cost,
            downtime_cost,
            resale_value,
            total_tco,
            annual_tco,
            lifetime_years: 12,
            cost_breakdown: {
                initial_pct: Number(((initial_cost / total) * 100).toFixed(2)),
                operations_pct: Number(((operations_cost / total) * 100).toFixed(2)),
                maintenance_pct: Number(((maintenance_cost / total) * 100).toFixed(2)),
                downtime_pct: Number(((downtime_cost / total) * 100).toFixed(2)),
                resale_offset_pct: Number(((resale_value / total) * 100).toFixed(2))
            }
        };
    }, [selectedMachineId, machines]);

    const scatterData = machines.map(m => ({ x: m.temp, y: m.health, z: m.vibration * 100, name: m.name, status: m.status }));

    return (
        <>
            <style>{fontStyle}</style>

            <div className="flex h-screen bg-[#F8FAFC] overflow-hidden font-sans text-slate-900 selection:bg-indigo-100">
                {/* SIDEBAR */}
                <aside className="w-72 bg-white border-r border-slate-200 flex flex-col z-40 shadow-sm">
                    <div className="p-8 border-b border-slate-100 flex items-center gap-4">
                        <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-indigo-200">
                            <Factory size={20} />
                        </div>
                        <div>
                            <span className="font-extrabold text-lg text-slate-900 block">TWIN MANAGER</span>
                            <div className="text-[10px] text-indigo-600 font-bold uppercase tracking-wider">v5.0 Connected</div>
                        </div>
                    </div>
                    <nav className="p-4 space-y-1">
                        {[
                            { id: 'overview', label: "Vue d'ensemble", icon: LayoutDashboard },
                            { id: 'machines', label: "Parc Machines", icon: Server },
                            { id: 'maintenance', label: "Maintenance IA", icon: Settings },
                            { id: 'tco', label: "Optimisation TCO", icon: BarChart3 },
                            { id: 'safety', label: "Sécurité & ATEX", icon: ShieldCheck },
                        ].map(item => (
                            <button
                                key={item.id}
                                onClick={() => setView(item.id as any)}
                                className={clsx(
                                    "w-full flex items-center gap-4 px-5 py-4 rounded-2xl text-sm font-bold transition-all",
                                    view === item.id
                                        ? "bg-indigo-50 text-indigo-700 shadow-sm"
                                        : "text-slate-500 hover:bg-slate-50 hover:text-slate-900"
                                )}
                            >
                                <item.icon size={20} className={view === item.id ? "text-indigo-600" : "text-slate-400"} />
                                {item.label}
                            </button>
                        ))}
                    </nav>
                    <div className="mt-auto p-6 border-t border-slate-100">
                        <div className="bg-slate-50 p-5 rounded-2xl border border-slate-200">
                            <div className="text-[10px] font-bold text-slate-400 uppercase mb-3">Santé Usine</div>
                            <div className="flex justify-between items-center mb-2">
                                <span className="text-sm font-bold text-slate-700">Production</span>
                                <span className="text-sm font-bold text-emerald-600">92%</span>
                            </div>
                            <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
                                <div className="h-full bg-emerald-500 w-[92%] animate-pulse" />
                            </div>
                        </div>
                    </div>
                </aside>

                {/* MAIN CONTENT */}
                <main className="flex-1 overflow-y-auto bg-[#F8FAFC]">
                    {view === 'overview' && (
                        <div className="h-full flex flex-col">
                            <Header title="Tableau de Bord" subtitle="Supervision temps réel de l'unité de production" />

                            <div className="px-8 pb-8 flex flex-col h-full">
                                {/* KPI STRIP */}
                                <div className="grid grid-cols-4 gap-6 mb-8">
                                    {[
                                        { label: "OEE Global", val: "84.2%", icon: TrendingUp, color: "text-indigo-600", bg: "bg-indigo-50" },
                                        { label: "Conso Énergie", val: "420 kW/h", icon: Zap, color: "text-amber-500", bg: "bg-amber-50" },
                                        { label: "MTBF Moyen", val: "3200 Hrs", icon: Clock, color: "text-emerald-500", bg: "bg-emerald-50" },
                                        { label: "Coût Horaire", val: "1 250 €", icon: DollarSign, color: "text-slate-600", bg: "bg-slate-100" },
                                    ].map((kpi, i) => (
                                        <div key={i} className="bg-white p-6 rounded-3xl shadow-sm border border-slate-200 flex items-center gap-5 hover:border-indigo-200 transition-colors">
                                            <div className={`p-4 rounded-2xl ${kpi.bg} ${kpi.color}`}><kpi.icon size={24} /></div>
                                            <div>
                                                <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">{kpi.label}</div>
                                                <div className="text-2xl font-black text-slate-900">{kpi.val}</div>
                                            </div>
                                        </div>
                                    ))}
                                </div>

                                <div className="flex-1 relative rounded-4xl overflow-hidden shadow-xl border border-slate-200 bg-white">
                                    {/* View Mode Toggle Buttons */}
                                    <div className="absolute top-6 left-6 z-10 flex gap-2">
                                        <button
                                            onClick={() => setViewMode('exterior')}
                                            className={clsx(
                                                "flex items-center gap-2 px-4 py-2.5 rounded-xl font-bold text-sm transition-all border shadow-sm",
                                                viewMode === 'exterior'
                                                    ? "bg-indigo-600 text-white border-indigo-600 shadow-lg shadow-indigo-200"
                                                    : "bg-white/90 backdrop-blur text-slate-600 border-slate-200 hover:bg-white hover:border-indigo-200"
                                            )}
                                        >
                                            <Building size={18} />
                                            Exterior
                                        </button>
                                        <button
                                            onClick={() => setViewMode('interior')}
                                            className={clsx(
                                                "flex items-center gap-2 px-4 py-2.5 rounded-xl font-bold text-sm transition-all border shadow-sm",
                                                viewMode === 'interior'
                                                    ? "bg-indigo-600 text-white border-indigo-600 shadow-lg shadow-indigo-200"
                                                    : "bg-white/90 backdrop-blur text-slate-600 border-slate-200 hover:bg-white hover:border-indigo-200"
                                            )}
                                        >
                                            <Home size={18} />
                                            Interior
                                        </button>
                                    </div>
                                    <Canvas shadows camera={{ position: [15, 12, 15], fov: 45 }}>
                                        <ComplexFactoryScene machineStates={machines} viewMode={viewMode} />
                                    </Canvas>
                                    <div className="absolute bottom-6 right-6 bg-white/90 backdrop-blur px-6 py-4 rounded-2xl border border-slate-200 shadow-lg text-xs font-bold text-slate-600 flex flex-col gap-1">
                                        <div className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-emerald-500" /> Running</div>
                                        <div className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-amber-500" /> Idle</div>
                                        <div className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-red-500" /> Warning</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {view === 'machines' && (
                        <div className="h-full flex flex-col">
                            <Header title="Parc Machines" subtitle="État détaillé des équipements connectés" />
                            <div className="px-8 pb-8">
                                <div className="bg-white rounded-4xl shadow-sm border border-slate-200 overflow-hidden">
                                    <table className="w-full text-sm text-left">
                                        <thead className="bg-slate-50 text-slate-500 uppercase font-bold text-xs">
                                            <tr>
                                                <th className="px-8 py-5">ID / Nom</th>
                                                <th className="px-8 py-5">Status</th>
                                                <th className="px-8 py-5 text-center">Temp.</th>
                                                <th className="px-8 py-5 text-center">Power</th>
                                                <th className="px-8 py-5 text-center">OEE</th>
                                                <th className="px-8 py-5">Santé (IA Prediction)</th>
                                                <th className="px-8 py-5"></th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-slate-100">
                                            {machines.map(m => (
                                                <tr key={m.id} className="hover:bg-indigo-50/30 cursor-pointer transition-colors group" onClick={() => { setSelectedMachineId(m.id); setView('tco'); }}>
                                                    <td className="px-8 py-5">
                                                        <div className="font-bold text-slate-800 text-base">{m.name}</div>
                                                        <div className="font-medium text-xs text-slate-400 mt-1">{m.id}</div>
                                                    </td>
                                                    <td className="px-8 py-5">
                                                        <span className={clsx("px-3 py-1.5 rounded-full text-[11px] font-bold uppercase tracking-wide border inline-flex items-center gap-1.5",
                                                            m.status === 'running' ? 'bg-emerald-50 text-emerald-700 border-emerald-100' :
                                                                m.status === 'idle' ? 'bg-amber-50 text-amber-700 border-amber-100' :
                                                                    'bg-red-50 text-red-700 border-red-100'
                                                        )}>
                                                            <div className={clsx("w-1.5 h-1.5 rounded-full", m.status === 'running' ? 'bg-emerald-500' : m.status === 'idle' ? 'bg-amber-500' : 'bg-red-500')} />
                                                            {m.status}
                                                        </span>
                                                    </td>
                                                    <td className="px-8 py-5 text-center font-bold text-slate-600">{m.temp}°C</td>
                                                    <td className="px-8 py-5 text-center font-bold text-slate-600">{m.power} kW</td>
                                                    <td className="px-8 py-5 text-center">
                                                        <div className="inline-block px-3 py-1 rounded-lg bg-slate-100 font-bold text-slate-700 text-xs">{m.oee}%</div>
                                                    </td>
                                                    <td className="px-8 py-5">
                                                        <div className="flex items-center gap-4">
                                                            <div className="flex-1 bg-slate-100 h-2.5 rounded-full overflow-hidden">
                                                                <div className={clsx("h-full transition-all duration-500", m.health > 90 ? "bg-emerald-500" : m.health > 70 ? "bg-amber-500" : "bg-red-500")} style={{ width: `${m.health}%` }} />
                                                            </div>
                                                            <span className="text-xs font-bold w-8 text-slate-500">{m.health}%</span>
                                                        </div>
                                                    </td>
                                                    <td className="px-8 py-5">
                                                        <div className="w-8 h-8 rounded-full bg-slate-50 flex items-center justify-center text-slate-400 group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                                                            <ArrowRight size={16} />
                                                        </div>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    )}

                    {view === 'maintenance' && (
                        <div className="h-full flex flex-col">
                            <Header title="Maintenance Prédictive" subtitle="Analyse IA des points de défaillance" />
                            <div className="px-8 pb-8 h-[calc(100vh-140px)] grid grid-cols-12 gap-8">
                                <div className="col-span-8 bg-white p-8 rounded-4xl shadow-sm border border-slate-200 flex flex-col">
                                    <h3 className="text-lg font-bold text-slate-800 mb-2">Matrice de Risque</h3>
                                    <p className="text-sm text-slate-500 mb-6 font-medium">Corrélation Vibration / Température / Santé Machine</p>
                                    <div className="flex-1 min-h-0">
                                        <ResponsiveContainer width="100%" height="100%">
                                            <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                                                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                                                <XAxis type="number" dataKey="x" name="Temp" unit="°C" stroke="#94a3b8" tick={{ fill: '#64748b', fontSize: 12 }} />
                                                <YAxis type="number" dataKey="y" name="Santé" unit="%" stroke="#94a3b8" tick={{ fill: '#64748b', fontSize: 12 }} />
                                                <ZAxis type="number" dataKey="z" range={[100, 1000]} name="Vibration" />
                                                <RechartsTooltip cursor={{ strokeDasharray: '3 3' }} content={({ active, payload }) => {
                                                    if (active && payload && payload.length) {
                                                        const data = payload[0].payload;
                                                        return (
                                                            <div className="bg-slate-900 text-white p-3 rounded-xl text-xs shadow-xl border border-slate-700">
                                                                <div className="font-bold mb-2 text-sm">{data.name}</div>
                                                                <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                                                                    <span className="text-slate-400">Temp:</span> <span>{data.x}°C</span>
                                                                    <span className="text-slate-400">Santé:</span> <span>{data.y}%</span>
                                                                    <span className="text-slate-400">Vib:</span> <span>{(data.z / 100).toFixed(2)} G</span>
                                                                </div>
                                                            </div>
                                                        );
                                                    }
                                                    return null;
                                                }} />
                                                <Scatter name="Machines" data={scatterData} fill="#4f46e5">
                                                    {scatterData.map((entry, index) => (
                                                        <Cell key={`cell-${index}`} fill={entry.y < 70 ? "#ef4444" : entry.y < 90 ? "#f59e0b" : "#10b981"} />
                                                    ))}
                                                </Scatter>
                                            </ScatterChart>
                                        </ResponsiveContainer>
                                    </div>
                                </div>
                                <div className="col-span-4 bg-white p-8 rounded-4xl shadow-sm border border-slate-200 flex flex-col">
                                    <h3 className="text-lg font-bold text-slate-800 mb-6 flex items-center gap-2">
                                        <AlertTriangle size={20} className="text-amber-500" /> Alertes Critiques
                                    </h3>
                                    <div className="space-y-4 overflow-y-auto pr-2">
                                        {machines.slice().sort((a, b) => a.health - b.health).map(m => (
                                            <div key={m.id} className="p-5 border border-slate-100 rounded-[20px] bg-slate-50/50 hover:bg-white hover:border-slate-200 hover:shadow-md transition-all">
                                                <div className="flex justify-between mb-3">
                                                    <span className="font-bold text-sm text-slate-800">{m.name}</span>
                                                    <span className={clsx("text-[10px] font-bold uppercase px-2 py-1 rounded-lg", m.health < 80 ? "bg-red-100 text-red-600" : "bg-emerald-100 text-emerald-600")}>
                                                        {m.health < 80 ? "CRITICAL" : "OK"}
                                                    </span>
                                                </div>
                                                <div className="flex justify-between text-xs text-slate-500 font-bold mb-2">
                                                    <span>Santé</span>
                                                    <span>{m.health}%</span>
                                                </div>
                                                <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden mb-3">
                                                    <div className={clsx("h-full", m.health < 80 ? "bg-red-500" : "bg-emerald-500")} style={{ width: `${m.health}%` }} />
                                                </div>
                                                <div className="text-xs font-medium text-slate-400 flex items-center gap-2">
                                                    <BrainCircuit size={12} />
                                                    {m.health < 80 ? "Inspection requise (Roulements)" : "Maintenance prévue Semaine 42"}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {view === 'safety' && (
                        <div className="h-full flex flex-col">
                            <Header title="Sécurité & Environnement" subtitle="Monitoring ATEX et qualité de l'air" />
                            <div className="px-8 pb-8 space-y-8">
                                <div className="grid grid-cols-3 gap-8">
                                    <div className="bg-amber-50 border border-amber-100 p-8 rounded-4xl flex flex-col justify-between">
                                        <div className="flex items-start justify-between">
                                            <div>
                                                <h3 className="font-black text-amber-900 text-xl">Zones ATEX</h3>
                                                <p className="text-sm text-amber-700 mt-2 font-medium leading-relaxed">Surveillance active des gaz explosifs et poussières inflammables.</p>
                                            </div>
                                            <div className="p-3 bg-white rounded-2xl shadow-sm"><AlertTriangle className="text-amber-600" size={24} /></div>
                                        </div>
                                        <div className="mt-8 flex gap-3">
                                            <div className="px-4 py-2 bg-white/60 text-amber-900 text-xs font-bold rounded-xl border border-amber-200">2 Zones Actives</div>
                                            <div className="px-4 py-2 bg-emerald-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-emerald-200/50">Ventilation 100%</div>
                                        </div>
                                    </div>
                                    <div className="col-span-2 bg-white border border-slate-200 p-8 rounded-4xl shadow-sm">
                                        <h3 className="font-bold text-slate-800 mb-6 text-lg">Qualité de l&apos;Air (PPM Temps Réel)</h3>
                                        <div className="h-40">
                                            <ResponsiveContainer width="100%" height="100%">
                                                <AreaChart data={[
                                                    { t: '08:00', v: 20 }, { t: '09:00', v: 35 }, { t: '10:00', v: 25 }, { t: '11:00', v: 45 }, { t: '12:00', v: 30 }, { t: '13:00', v: 25 }
                                                ]}>
                                                    <defs>
                                                        <linearGradient id="colorPpm" x1="0" y1="0" x2="0" y2="1">
                                                            <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.2} />
                                                            <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                                                        </linearGradient>
                                                    </defs>
                                                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                                                    <XAxis dataKey="t" axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 12 }} />
                                                    <YAxis axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 12 }} />
                                                    <Area type="monotone" dataKey="v" stroke="#f59e0b" strokeWidth={3} fillOpacity={1} fill="url(#colorPpm)" />
                                                </AreaChart>
                                            </ResponsiveContainer>
                                        </div>
                                    </div>
                                </div>

                                <div className="bg-white rounded-4xl shadow-sm border border-slate-200 overflow-hidden">
                                    <table className="w-full text-sm">
                                        <thead className="bg-slate-50 text-slate-500 uppercase font-bold text-xs">
                                            <tr>
                                                <th className="px-8 py-5 text-left">Zone</th>
                                                <th className="px-8 py-5 text-left">Type Capteur</th>
                                                <th className="px-8 py-5 text-left">Statut</th>
                                                <th className="px-8 py-5 text-left">Concentration</th>
                                                <th className="px-8 py-5 text-left">Extraction</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-slate-100">
                                            {[
                                                { z: "Peinture Robotisée", type: "Solvant (VOC)", s: "SAFE", ppm: 120, v: "100%", trend: "stable" },
                                                { z: "Stockage Solvants", type: "Hydrocarbure", s: "SAFE", ppm: 45, v: "80%", trend: "down" },
                                                { z: "Mélange Additifs", type: "Poussière Fine", s: "WARNING", ppm: 280, v: "MAX", trend: "up" },
                                            ].map((row, i) => (
                                                <tr key={i} className="hover:bg-slate-50/50 transition-colors">
                                                    <td className="px-8 py-5 font-bold text-slate-800">{row.z}</td>
                                                    <td className="px-8 py-5 text-slate-500 font-medium">{row.type}</td>
                                                    <td className="px-8 py-5">
                                                        <span className={clsx("px-3 py-1.5 rounded-full text-[11px] font-bold flex w-fit items-center gap-1.5 uppercase tracking-wide",
                                                            row.s === 'SAFE' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
                                                        )}>
                                                            <CheckCircle2 size={12} /> {row.s}
                                                        </span>
                                                    </td>
                                                    <td className="px-8 py-5 font-bold text-slate-700">
                                                        {row.ppm} <span className="text-slate-400 text-xs font-normal">ppm</span>
                                                    </td>
                                                    <td className="px-8 py-5 flex items-center gap-2 text-slate-700 font-bold">
                                                        <Wind size={16} className={row.v === "MAX" ? "text-amber-500 animate-pulse" : "text-indigo-500"} /> {row.v}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    )}

                    {view === 'tco' && (
                        <div className="h-full flex flex-col">
                            <Header title="Analyse TCO – SARL ALLO MAISON" subtitle={`${TCO_DATA.project_name} • Calculé le ${TCO_DATA.calculation_date}`} />
                            <div className="px-8 pb-8 overflow-y-auto">
                                {/* Summary KPIs */}
                                <div className="grid grid-cols-4 gap-6 mb-8">
                                    <div className="bg-gradient-to-br from-indigo-600 to-indigo-700 p-6 rounded-3xl text-white shadow-lg shadow-indigo-200">
                                        <div className="text-[10px] font-bold uppercase tracking-widest opacity-80 mb-1">TCO Total (5 ans)</div>
                                        <div className="text-3xl font-black">{formatBillion(TCO_DATA.total_tco)}</div>
                                    </div>
                                    <div className="bg-white p-6 rounded-3xl shadow-sm border border-slate-200">
                                        <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1">TCO Annuel Moyen</div>
                                        <div className="text-2xl font-black text-slate-900">{formatBillion(TCO_DATA.average_annual_tco)}</div>
                                    </div>
                                    <div className="bg-white p-6 rounded-3xl shadow-sm border border-slate-200 border-l-4 border-l-indigo-500">
                                        <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1">TCO Machine Sélect.</div>
                                        <div className="text-2xl font-black text-slate-900">{formatBillion(selectedMachineTco.total_tco)}</div>
                                        <div className="text-[10px] text-indigo-600 font-medium mt-1 truncate">{selectedMachineTco.machine_name}</div>
                                    </div>
                                    <div className="bg-white p-6 rounded-3xl shadow-sm border border-slate-200">
                                        <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1">TCO Matières Premières</div>
                                        <div className="text-2xl font-black text-slate-900">{formatBillion(TCO_DATA.total_raw_materials_tco)}</div>
                                    </div>
                                </div>

                                {/* Real-time Simulation Controls & Chart */}
                                <div className="grid grid-cols-12 gap-6 mb-8">
                                    {/* Control Panel */}
                                    <div className="col-span-4 bg-white rounded-3xl shadow-sm border border-slate-200 p-6">
                                        <h3 className="text-lg font-bold text-slate-800 mb-6 flex items-center gap-3">
                                            <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg"><Settings size={20} /></div>
                                            Simulation Temps Réel
                                        </h3>

                                        {/* Machine Selection */}
                                        <div className="mb-6">
                                            <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-3">Machine Cible</label>
                                            <div className="relative">
                                                <select
                                                    value={selectedMachineId}
                                                    onChange={(e) => setSelectedMachineId(e.target.value)}
                                                    className="w-full p-4 bg-slate-50 border border-slate-200 rounded-xl font-bold text-slate-700 focus:ring-2 focus:ring-indigo-500 outline-none transition-all appearance-none pr-10"
                                                >
                                                    {machines.map(m => (
                                                        <option key={m.id} value={m.id}>{m.name}</option>
                                                    ))}
                                                </select>
                                                <div className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none">▼</div>
                                            </div>
                                            <div className="mt-3 p-3 bg-slate-50 rounded-xl text-xs space-y-1.5">
                                                <div className="flex justify-between">
                                                    <span className="text-slate-500">Zone:</span>
                                                    <span className="font-bold text-slate-700">{machines.find(m => m.id === selectedMachineId)?.zone}</span>
                                                </div>
                                                <div className="flex justify-between">
                                                    <span className="text-slate-500">Puissance:</span>
                                                    <span className="font-bold text-slate-700">{machines.find(m => m.id === selectedMachineId)?.power} kW</span>
                                                </div>
                                                <div className="flex justify-between">
                                                    <span className="text-slate-500">OEE:</span>
                                                    <span className="font-bold text-indigo-600">{machines.find(m => m.id === selectedMachineId)?.oee}%</span>
                                                </div>
                                            </div>
                                        </div>
                                        {/* Voltage Display (Random) */}
                                        <div className="p-5 bg-gradient-to-r from-purple-50 to-indigo-50 rounded-2xl border border-purple-100 mb-6">
                                            <div className="flex justify-between items-center mb-3">
                                                <span className="text-sm font-bold text-purple-800 flex items-center gap-2">
                                                    <Zap size={16} /> Tension Réseau
                                                </span>
                                                <span className={clsx("text-2xl font-black transition-all",
                                                    voltage > 230 ? "text-red-500" : voltage < 210 ? "text-amber-500" : "text-purple-700"
                                                )}>
                                                    {voltage.toFixed(1)} V
                                                </span>
                                            </div>
                                            <div className="w-full bg-purple-200/50 h-3 rounded-full overflow-hidden">
                                                <div
                                                    className={clsx("h-full transition-all duration-500 rounded-full",
                                                        voltage > 230 ? "bg-red-500" : voltage < 210 ? "bg-amber-500" : "bg-purple-500"
                                                    )}
                                                    style={{ width: `${((voltage - 200) / 40) * 100}%` }}
                                                />
                                            </div>
                                            <div className="flex justify-between text-[10px] text-purple-600 mt-1 font-medium">
                                                <span>200V</span>
                                                <span>240V</span>
                                            </div>
                                            <div className="text-[10px] text-purple-600 mt-2 flex items-center gap-1">
                                                <div className="w-1.5 h-1.5 rounded-full bg-purple-500 animate-pulse" />
                                                Simulation automatique (±5%)
                                            </div>
                                        </div>

                                        {/* Energy Cost Slider (User Controlled) */}
                                        <div className="p-5 bg-gradient-to-r from-emerald-50 to-teal-50 rounded-2xl border border-emerald-100 mb-6">
                                            <div className="flex justify-between items-center mb-3">
                                                <span className="text-sm font-bold text-emerald-800 flex items-center gap-2">
                                                    <DollarSign size={16} /> Coût Énergie
                                                </span>
                                                <span className="text-2xl font-black text-emerald-700">
                                                    {energyCost} DZD/kWh
                                                </span>
                                            </div>
                                            <input
                                                type="range"
                                                min="5"
                                                max="25"
                                                step="1"
                                                value={energyCost}
                                                onChange={(e) => setEnergyCost(parseInt(e.target.value))}
                                                className="w-full h-3 bg-emerald-200/50 rounded-lg appearance-none cursor-pointer accent-emerald-600"
                                            />
                                            <div className="flex justify-between text-[10px] text-emerald-600 mt-1 font-medium">
                                                <span>5 DZD</span>
                                                <span>25 DZD</span>
                                            </div>
                                        </div>

                                        {/* Accumulated Cost */}
                                        <div className="p-5 bg-gradient-to-r from-amber-50 to-orange-50 rounded-2xl border border-amber-200">
                                            <div className="text-sm font-bold text-amber-800 mb-2 flex items-center gap-2">
                                                <Activity size={16} /> Coût Accumulé
                                            </div>
                                            <div className="text-3xl font-black text-amber-900">
                                                {formatDZD(Math.round(realtimeCostAccumulator))}
                                            </div>
                                            <div className="text-xs text-amber-600 mt-2 flex items-center gap-2">
                                                <div className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
                                                Mise à jour toutes les 5 secondes
                                            </div>
                                        </div>
                                    </div>

                                    {/* Real-time Chart */}
                                    <div className="col-span-8 bg-white rounded-3xl shadow-sm border border-slate-200 p-6">
                                        <h3 className="text-lg font-bold text-slate-800 mb-4 flex items-center justify-between">
                                            <span className="flex items-center gap-3">
                                                <div className="p-2 bg-amber-50 text-amber-600 rounded-lg"><TrendingUp size={20} /></div>
                                                Coûts d&apos;Exploitation en Temps Réel
                                            </span>
                                            <span className="text-xs font-medium text-slate-400 flex items-center gap-2">
                                                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                                                Live • 5s interval
                                            </span>
                                        </h3>
                                        <div className="h-72">
                                            <ResponsiveContainer width="100%" height="100%">
                                                <ComposedChart data={chartHistory} margin={{ top: 20, right: 30, left: 10, bottom: 5 }}>
                                                    <defs>
                                                        <linearGradient id="colorOperations" x1="0" y1="0" x2="0" y2="1">
                                                            <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.3} />
                                                            <stop offset="95%" stopColor="#4f46e5" stopOpacity={0.05} />
                                                        </linearGradient>
                                                        <linearGradient id="colorEnergy" x1="0" y1="0" x2="0" y2="1">
                                                            <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
                                                            <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.05} />
                                                        </linearGradient>
                                                        <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
                                                            <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                                                            <stop offset="95%" stopColor="#10b981" stopOpacity={0.1} />
                                                        </linearGradient>
                                                    </defs>
                                                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                                                    <XAxis
                                                        dataKey="time"
                                                        axisLine={false}
                                                        tickLine={false}
                                                        tick={{ fontSize: 11, fill: '#94a3b8' }}
                                                    />
                                                    <YAxis
                                                        axisLine={false}
                                                        tickLine={false}
                                                        tickFormatter={(val) => `${(val / 1000).toFixed(0)}k`}
                                                        tick={{ fontSize: 11, fill: '#94a3b8' }}
                                                    />
                                                    <RechartsTooltip
                                                        cursor={{ stroke: '#e2e8f0', strokeWidth: 2 }}
                                                        contentStyle={{
                                                            borderRadius: '16px',
                                                            border: '1px solid #e2e8f0',
                                                            boxShadow: '0 10px 25px -5px rgb(0 0 0 / 0.1)',
                                                            padding: '12px 16px'
                                                        }}
                                                        formatter={(value) => value !== undefined ? formatDZD(Math.round(value as number)) : ''}
                                                    />
                                                    <Legend
                                                        wrapperStyle={{ paddingTop: '15px' }}
                                                        iconType="circle"
                                                        iconSize={8}
                                                    />
                                                    <Area
                                                        type="monotone"
                                                        dataKey="total"
                                                        stroke="#10b981"
                                                        strokeWidth={3}
                                                        fill="url(#colorTotal)"
                                                        name="Coût Total"
                                                        animationDuration={500}
                                                    />
                                                    <Line
                                                        type="monotone"
                                                        dataKey="operations"
                                                        stroke="#4f46e5"
                                                        strokeWidth={2.5}
                                                        dot={{ fill: '#4f46e5', r: 4 }}
                                                        activeDot={{ r: 6, stroke: '#fff', strokeWidth: 2 }}
                                                        name="Opérations"
                                                        animationDuration={500}
                                                    />
                                                    <Line
                                                        type="monotone"
                                                        dataKey="energy"
                                                        stroke="#f59e0b"
                                                        strokeWidth={2.5}
                                                        dot={{ fill: '#f59e0b', r: 4 }}
                                                        activeDot={{ r: 6, stroke: '#fff', strokeWidth: 2 }}
                                                        name="Énergie"
                                                        animationDuration={500}
                                                    />
                                                    <Line
                                                        type="monotone"
                                                        dataKey="maintenance"
                                                        stroke="#8b5cf6"
                                                        strokeWidth={2}
                                                        strokeDasharray="5 5"
                                                        dot={false}
                                                        name="Maintenance"
                                                        animationDuration={500}
                                                    />
                                                </ComposedChart>
                                            </ResponsiveContainer>
                                        </div>
                                    </div>
                                </div>

                                {/* Machine TCO Details */}
                                <div className="bg-white rounded-3xl shadow-sm border border-slate-200 p-6 mb-8">
                                    <h3 className="text-lg font-bold text-slate-800 mb-6 flex items-center gap-3">
                                        <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg"><Server size={20} /></div>
                                        TCO Machine: {selectedMachineTco.machine_name}
                                    </h3>
                                    <div className="grid grid-cols-2 gap-8">
                                        <div className="space-y-4">
                                            <div className="flex justify-between p-4 bg-slate-50 rounded-xl">
                                                <span className="text-sm font-medium text-slate-600">Fabricant</span>
                                                <span className="text-sm font-bold text-slate-900">{selectedMachineTco.manufacturer}</span>
                                            </div>
                                            <div className="flex justify-between p-4 bg-slate-50 rounded-xl">
                                                <span className="text-sm font-medium text-slate-600">Catégorie</span>
                                                <span className="text-sm font-bold text-slate-900">{selectedMachineTco.category}</span>
                                            </div>
                                            <div className="flex justify-between p-4 bg-slate-50 rounded-xl">
                                                <span className="text-sm font-medium text-slate-600">Durée de vie</span>
                                                <span className="text-sm font-bold text-slate-900">{selectedMachineTco.lifetime_years} ans</span>
                                            </div>
                                            <div className="flex justify-between p-4 bg-indigo-50 rounded-xl border border-indigo-100">
                                                <span className="text-sm font-medium text-indigo-700">TCO Total Machine</span>
                                                <span className="text-sm font-bold text-indigo-900">{formatBillion(selectedMachineTco.total_tco)}</span>
                                            </div>
                                        </div>
                                        <div className="space-y-3">
                                            {[
                                                { label: "Coût Initial", value: selectedMachineTco.initial_cost, pct: selectedMachineTco.cost_breakdown.initial_pct, color: "bg-indigo-500" },
                                                { label: "Opérations", value: selectedMachineTco.operations_cost, pct: selectedMachineTco.cost_breakdown.operations_pct, color: "bg-amber-500" },
                                                { label: "Maintenance", value: selectedMachineTco.maintenance_cost, pct: selectedMachineTco.cost_breakdown.maintenance_pct, color: "bg-emerald-500" },
                                                { label: "Temps d'arrêt", value: selectedMachineTco.downtime_cost, pct: selectedMachineTco.cost_breakdown.downtime_pct, color: "bg-red-400" },
                                            ].map((item, i) => (
                                                <div key={i} className="p-3 bg-slate-50 rounded-xl">
                                                    <div className="flex justify-between text-xs font-bold mb-2">
                                                        <span className="text-slate-600">{item.label}</span>
                                                        <span className="text-slate-900">{formatBillion(item.value)} ({item.pct}%)</span>
                                                    </div>
                                                    <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
                                                        <div className={`h-full ${item.color}`} style={{ width: `${item.pct}%` }} />
                                                    </div>
                                                </div>
                                            ))}
                                            <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-100">
                                                <div className="flex justify-between text-xs font-bold">
                                                    <span className="text-emerald-700">Valeur Résiduelle</span>
                                                    <span className="text-emerald-900">-{formatBillion(selectedMachineTco.resale_value)} ({selectedMachineTco.cost_breakdown.resale_offset_pct}%)</span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                {/* Products & Raw Materials Grid */}
                                <div className="grid grid-cols-2 gap-8 mb-8">
                                    {/* Products TCO */}
                                    <div className="bg-white rounded-3xl shadow-sm border border-slate-200 p-6">
                                        <h3 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-3">
                                            <div className="p-2 bg-emerald-50 text-emerald-600 rounded-lg"><Factory size={20} /></div>
                                            TCO Produits
                                            <span className="ml-auto text-sm font-bold text-emerald-600">{formatBillion(TCO_DATA.total_products_tco)}</span>
                                        </h3>
                                        <div className="space-y-3 max-h-64 overflow-y-auto pr-2">
                                            {TCO_DATA.product_tco.map((prod, i) => (
                                                <div key={i} className="p-4 bg-slate-50 rounded-xl hover:bg-slate-100 transition-colors">
                                                    <div className="flex justify-between items-start mb-2">
                                                        <span className="text-sm font-bold text-slate-800 flex-1 pr-4">{prod.nom_produit}</span>
                                                        <span className={clsx("px-2 py-1 text-[10px] font-bold uppercase rounded-lg", prod.categorie === 'finished' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700')}>
                                                            {prod.categorie === 'finished' ? 'Fini' : 'Semi-fini'}
                                                        </span>
                                                    </div>
                                                    <div className="text-lg font-black text-slate-900">{formatBillion(prod.total_tco)}</div>
                                                    <div className="flex gap-4 mt-2 text-[10px] text-slate-500">
                                                        <span>Landing: {formatDZD(prod.landing_cost)}</span>
                                                        <span>Stock: {formatDZD(prod.holding_cost)}</span>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Raw Materials TCO */}
                                    <div className="bg-white rounded-3xl shadow-sm border border-slate-200 p-6">
                                        <h3 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-3">
                                            <div className="p-2 bg-amber-50 text-amber-600 rounded-lg"><Zap size={20} /></div>
                                            TCO Matières Premières
                                            <span className="ml-auto text-sm font-bold text-amber-600">{formatBillion(TCO_DATA.total_raw_materials_tco)}</span>
                                        </h3>
                                        <div className="space-y-2 max-h-64 overflow-y-auto pr-2">
                                            {TCO_DATA.raw_materials_tco.slice(0, 8).map((mat, i) => (
                                                <div key={i} className="p-3 bg-slate-50 rounded-xl hover:bg-slate-100 transition-colors flex justify-between items-center">
                                                    <div>
                                                        <div className="text-sm font-bold text-slate-800">{mat.nom_materiau}</div>
                                                        <div className="text-[10px] text-slate-500">{mat.type_materiau}</div>
                                                    </div>
                                                    <div className="text-right">
                                                        <div className="text-sm font-black text-slate-900">{formatBillion(mat.total_tco)}</div>
                                                        <div className={clsx("text-[10px] font-bold", mat.estimation_confidence === 'high' ? 'text-emerald-600' : mat.estimation_confidence === 'medium' ? 'text-amber-600' : 'text-red-500')}>
                                                            {mat.estimation_confidence === 'high' ? '◉ Élevée' : mat.estimation_confidence === 'medium' ? '◉ Moyenne' : '◉ Faible'}
                                                        </div>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>

                                {/* Annual TCO Projection Chart */}
                                <div className="bg-white rounded-3xl shadow-sm border border-slate-200 p-6">
                                    <h3 className="text-lg font-bold text-slate-800 mb-6">Projection TCO sur 5 ans</h3>
                                    <div className="h-80">
                                        <ResponsiveContainer width="100%" height="100%">
                                            <BarChart data={TCO_DATA.annual_tco.map(y => ({
                                                year: `Année ${y.year}`,
                                                Machines: y.machines_tco,
                                                Produits: y.products_tco,
                                                Matières: y.raw_materials_tco,
                                                Total: y.total_tco
                                            }))} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                                                <XAxis dataKey="year" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#94a3b8' }} />
                                                <YAxis axisLine={false} tickLine={false} tickFormatter={(val) => `${(val / 1e9).toFixed(1)} Mrd`} tick={{ fontSize: 12, fill: '#94a3b8' }} />
                                                <RechartsTooltip
                                                    cursor={{ fill: '#f8fafc' }}
                                                    contentStyle={{ borderRadius: '16px', border: '1px solid #e2e8f0', boxShadow: '0 10px 25px -5px rgb(0 0 0 / 0.1)' }}
                                                    formatter={(value) => value !== undefined ? formatBillion(value as number) : ''}
                                                />
                                                <Legend wrapperStyle={{ paddingTop: '20px' }} iconType="circle" />
                                                <Bar dataKey="Machines" stackId="a" fill="#4f46e5" name="TCO Machines" radius={[0, 0, 4, 4]} />
                                                <Bar dataKey="Produits" stackId="a" fill="#10b981" name="TCO Produits" />
                                                <Bar dataKey="Matières" stackId="a" fill="#f59e0b" name="TCO Matières" radius={[6, 6, 0, 0]} />
                                            </BarChart>
                                        </ResponsiveContainer>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </main>
            </div>
        </>
    );
}