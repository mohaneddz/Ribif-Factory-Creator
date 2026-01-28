"use client"

import React from 'react'
import * as THREE from 'three'

export default function GridObjects({
    positions,
    setPositions,
    dragIndex,
    setDragIndex,
    offsetRef,
    controlsRef,
    cellSize,
    boxSize,
    gridOffset,
    shadowsEnabled,
}: {
    positions: [number, number, number][]
    setPositions: React.Dispatch<React.SetStateAction<[number, number, number][]>>
    dragIndex: number | null
    setDragIndex: (i: number | null) => void
    offsetRef: React.MutableRefObject<THREE.Vector3>
    controlsRef: React.MutableRefObject<any>
    cellSize: number
    boxSize: number
    gridOffset: number
    shadowsEnabled: boolean
}) {
    return (
        <>
            {/* Ground plane (captures pointer for dragging) */}
            <mesh
                rotation={[-Math.PI / 2, 0, 0]}
                receiveShadow={shadowsEnabled}
                onPointerMove={(e: any) => {
                    if (dragIndex === null) return
                    e.stopPropagation()
                    const p = e.point
                    const newX = gridOffset + Math.round((p.x - offsetRef.current.x - gridOffset) / cellSize) * cellSize
                    const newZ = gridOffset + Math.round((p.z - offsetRef.current.z - gridOffset) / cellSize) * cellSize
                    setPositions((prev) => {
                        const next = prev.map((pos) => pos.slice() as [number, number, number])
                        next[dragIndex] = [newX, prev[dragIndex][1], newZ]
                        return next
                    })
                }}
                onPointerUp={(e: any) => {
                    if (dragIndex === null) return
                    e.stopPropagation()
                    setDragIndex(null)
                    if (controlsRef.current) controlsRef.current.enabled = true
                }}
            >
                <planeGeometry args={[100, 100]} />
                <meshStandardMaterial color="gray" />
            </mesh>

            {/* Boxes rendered in a checkerboard pattern (every other cell) */}
            {positions.map((pos: [number, number, number], k: number) => {
                const cols = Math.round(Math.sqrt(positions.length))
                const i = Math.floor(k / cols)
                const j = k % cols
                const occupied = (i + j) % 2 === 0
                if (!occupied) return null
                return (
                    <mesh
                        key={k}
                        position={pos as [number, number, number]}
                        castShadow={shadowsEnabled}
                        receiveShadow={shadowsEnabled}
                        onPointerDown={(e: any) => {
                            e.stopPropagation()
                            setDragIndex(k)
                            const p = e.point
                            offsetRef.current.set(p.x - pos[0], p.y - pos[1], p.z - pos[2])
                            if (controlsRef.current) controlsRef.current.enabled = false
                        }}
                        onPointerUp={(e: any) => {
                            e.stopPropagation()
                            setDragIndex(null)
                            if (controlsRef.current) controlsRef.current.enabled = true
                        }}
                        onPointerOver={(e: any) => {
                            e.stopPropagation()
                            document.body.style.cursor = 'grab'
                        }}
                        onPointerOut={(e: any) => {
                            e.stopPropagation()
                            document.body.style.cursor = 'default'
                        }}
                    >
                        <boxGeometry args={[boxSize, boxSize, boxSize]} />
                        <meshStandardMaterial color={dragIndex === k ? 'orange' : 'blue'} />
                    </mesh>
                )
            })}
        </>
    )
}
