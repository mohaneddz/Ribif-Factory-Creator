import React from 'react'
import { Load3D } from '../../../utils/load3d'

export default function DuckInstances() {
  return (
    <Load3D
      url="/models/duck.gltf"
      size={[2, 2, 2]}
      position={[0, 1, 0]}
    />
  )
}
