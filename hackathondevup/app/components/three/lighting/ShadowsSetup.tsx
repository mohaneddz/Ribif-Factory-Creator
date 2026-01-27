"use client"

import { useEffect } from 'react'
import { useThree } from '@react-three/fiber'
import * as THREE from 'three'

export default function ShadowsSetup({ enabled, soft }: { enabled: boolean; soft: boolean }) {
  const { gl } = useThree()

  useEffect(() => {
    if (!gl) return
    gl.shadowMap.enabled = enabled
    gl.shadowMap.type = soft ? THREE.PCFSoftShadowMap : THREE.PCFShadowMap
    gl.shadowMap.needsUpdate = true
  }, [gl, enabled, soft])

  return null
}
