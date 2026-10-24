"use client"

import React, { useEffect, useMemo, useRef } from "react"
import * as THREE from "three"
import { useThree } from "@react-three/fiber"
import { Environment } from "@react-three/drei"
import { RectAreaLightHelper } from "three/examples/jsm/helpers/RectAreaLightHelper.js"
import { RectAreaLightUniformsLib } from "three/examples/jsm/lights/RectAreaLightUniformsLib.js"

// Initialize RectAreaLight uniforms
RectAreaLightUniformsLib.init()

// ---- Helpers hook (no extra deps) ----
function useLightHelpers(
  items: Array<{
    light: React.RefObject<THREE.Light | null>
    type: "dir" | "point" | "rect"
    size?: number
    color?: THREE.ColorRepresentation
  }>
) {
  const { scene } = useThree()

  useEffect(() => {
    const helpers: THREE.Object3D[] = []

    for (const it of items) {
      const l = it.light.current
      if (!l) continue

      let h: THREE.Object3D | null = null
      const size = it.size ?? 0.5
      const color = it.color ?? "hotpink"

      if (it.type === "dir" && l instanceof THREE.DirectionalLight) {
        h = new THREE.DirectionalLightHelper(l, size, color)
      } else if (it.type === "point" && l instanceof THREE.PointLight) {
        h = new THREE.PointLightHelper(l, size, color)
      } else if (it.type === "rect" && l instanceof THREE.RectAreaLight) {
        h = new RectAreaLightHelper(l, color)
      }

      if (h) {
        scene.add(h)
        helpers.push(h)
      }
    }

    return () => {
      helpers.forEach((h) => {
        scene.remove(h)
        // @ts-expect-error helper may expose dispose
        h.dispose?.()
          ; (h as any).geometry?.dispose?.()
          ; (h as any).material?.dispose?.()
      })
    }
  }, [scene, items])
}

type LightingProps = {
  shadowsEnabled: boolean
  softShadows: boolean
  ambientOn: boolean
  dirOn: boolean

  // Key light
  lightPos: [number, number, number]
  intensity: number

  // Shadow tuning
  bias: number
  normalBias: number
  radius: number
  shadowResolution: number

  // Legacy props (kept for compatibility)
  accumulative?: boolean
  accumulativeFrames?: number
  activeCam?: number
  showHelpers?: boolean
}

export default function Lighting({
  shadowsEnabled,
  ambientOn,
  dirOn,
  lightPos,
  intensity,
  bias,
  normalBias,
  radius,
  shadowResolution,
  activeCam = 0,
  showHelpers = false,
}: LightingProps) {
  const keyRef = useRef<THREE.DirectionalLight | null>(null)

  const rectTopRef = useRef<THREE.RectAreaLight | null>(null)
  const rectSideRef = useRef<THREE.RectAreaLight | null>(null)
  const pLRef = useRef<THREE.PointLight | null>(null)
  const pRRef = useRef<THREE.PointLight | null>(null)
  const fillRef = useRef<THREE.DirectionalLight | null>(null)

  // Create helper list (stable)
  const helperItems = useMemo(
    () => [
      { light: rectTopRef, type: "rect" as const, color: "white" },
      { light: rectSideRef, type: "rect" as const, color: "#00ffd5" },
      { light: pLRef, type: "point" as const, size: 0.2, color: "cyan" },
      { light: pRRef, type: "point" as const, size: 0.2, color: "cyan" },
      { light: keyRef, type: "dir" as const, size: 1.5, color: "#ffd6b0" },
      { light: fillRef, type: "dir" as const, size: 1.5, color: "#b9c7ff" },
    ],
    []
  )

  // Attach helpers (only when lights exist and showHelpers is true)
  useLightHelpers(showHelpers ? helperItems : [])

  useEffect(() => {
    const key = keyRef.current
    if (!key) return

    key.shadow.mapSize.set(shadowResolution, shadowResolution)
    key.shadow.bias = bias
    key.shadow.normalBias = normalBias
    key.shadow.radius = radius

    const cam = key.shadow.camera
    cam.left = -20
    cam.right = 30
    cam.top = 20
    cam.bottom = -20
    cam.near = 0.1
    cam.far = 100
    cam.updateProjectionMatrix()
  }, [shadowResolution, bias, normalBias, radius])

  return (
    <>
      {activeCam !== 0 && (
        <Environment files="/models/env.hdr" background blur={0.02} environmentIntensity={0} />
      )}
      <rectAreaLight
        ref={rectTopRef}
        position={[0, 3, 1]}
        rotation={[-Math.PI / 2, 0, 0]}
        width={5}
        height={5}
        intensity={1.2}
        color="#ffffffff"
      />

      <pointLight ref={pLRef} position={[-2.5, 1.2, 2]} intensity={3} distance={16} decay={4} />
      <pointLight ref={pRRef} position={[2.5, 1.2, 2]} intensity={3} distance={16} decay={4} />

      {/* {ambientOn && <ambientLight intensity={0.02d} />} */}

      {dirOn && (
        <directionalLight
          ref={keyRef}
          position={lightPos}
          intensity={intensity}
          color={"#ffd6b0"}
          castShadow={shadowsEnabled}
          shadow-mapSize={[shadowResolution, shadowResolution]}
        />
      )}

      <directionalLight
        ref={fillRef}
        position={[-18, 16, -10]}
        intensity={0.4}
        color={"#b9c7ff"}
        castShadow={false}
      />
    </>
  )
}
