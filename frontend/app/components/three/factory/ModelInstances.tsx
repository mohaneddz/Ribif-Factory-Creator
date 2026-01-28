"use client"

import React from 'react'
import { Load3D } from '../../../utils/load3d'

export default function ModelInstances({
  shadowsEnabled,
}: {
  shadowsEnabled: boolean
}) {
  // Fixed positions for realistic showcase, moved inside the factory
  const fixedPositions: [number, number, number][] = [
    [0, 0, 0],
    [-0, 0, 0],
    [0, 0, -0],
  ]

  return (
    <>
      {fixedPositions.map((pos, idx) => (
        <Load3D
          key={`model-${idx}`}
          url="/models/duck.gltf"
          size={[2, 2, 2]}
          position={pos}
        />
      ))}
    </>
  )
}
