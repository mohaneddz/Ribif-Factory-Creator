import React from 'react'
import { Stats } from '@react-three/drei'

interface PerformanceStatsProps {
    show: boolean
}

export default function PerformanceStats({ show }: PerformanceStatsProps) {
    if (!show) return null

    return <Stats showPanel={0} className="stats" />
}
