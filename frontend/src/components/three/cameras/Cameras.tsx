import React, { useState } from 'react'
import * as THREE from 'three'

export default function Cameras() {
  const [cam1, setCam1] = useState<THREE.PerspectiveCamera | null>(null)
  const [cam2, setCam2] = useState<THREE.PerspectiveCamera | null>(null)

  return (
    <>
      <perspectiveCamera ref={setCam1} position={[5, 5, 5]} />
      {cam1 && <cameraHelper args={[cam1]} />}
      <perspectiveCamera ref={setCam2} position={[-5, 5, -5]} />
      {cam2 && <cameraHelper args={[cam2]} />}
    </>
  )
}
