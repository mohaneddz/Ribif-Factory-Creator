"use client"

import { ReactNode, useCallback, useState, useRef, useMemo } from "react"
import dynamic from "next/dynamic"
import { useFrame } from "@react-three/fiber"
// import { PerformanceMonitor, Stats } from "@react-three/drei"
import { Leva } from "leva"
import * as THREE from "three"

// Dynamic import for Canvas to disable SSR (fixes ReactDOM.render compatibility with React 19)
const Canvas = dynamic(
    () => import("@react-three/fiber").then((mod) => mod.Canvas),
    { ssr: false }
)

import CaptureCamera from "../cameras/CaptureCamera"
import CameraStatusHUD from "../helpers/CameraStatusHUD"
import { useSceneSettings, BaseLogic, SceneLogicParams } from "@/hooks/useSceneLogic"
import { useSceneThreeLogic } from "@/hooks/useSceneThreeLogic"

interface BaseSceneProps extends SceneLogicParams {
    children: (logic: BaseLogic) => ReactNode
}

/**
 * R3F-only content (inside Canvas)
 */
function InnerSceneContent({ children, onHudUpdate }: BaseSceneProps & { onHudUpdate: (pos: { x: number, y: number, z: number }, target: { x: number, y: number, z: number }) => void }) {
    const settings = useSceneSettings()
    const threeLogic = useSceneThreeLogic()
    const { camera } = threeLogic
    const {
        activeCam,
        autoRotate,
        showAxes,
    } = settings

    const lastRenderTime = useRef(0)
    const fpsInterval = 1 / 60

    useFrame((state) => {
        // Handle HUD Update
        if (camera) {
            const controls = (state.controls as any)
            const target = controls?.target ? controls.target.clone() : new THREE.Vector3(0, 0, 0)

            // If controls are missing or target is 0,0,0, try to get looking direction as fallback
            if (!controls && camera) {
                camera.getWorldDirection(target).multiplyScalar(10).add(camera.position)
            }

            onHudUpdate(camera.position, target)
        }

        // FPS Limiter: Take control of the render loop (priority 1)
        const currentTime = state.clock.getElapsedTime()
        if (currentTime - lastRenderTime.current >= fpsInterval) {
            state.gl.render(state.scene, state.camera)
            lastRenderTime.current = currentTime
        }
    }, 1)

    const combinedLogic = { ...settings, ...threeLogic }

    const cam0Pos = useMemo<[number, number, number]>(() => [0.19, 1.27, -1.66], [])
    const cam0Target = useMemo<[number, number, number]>(() => [0.1, 0.76, 0.38], [])

    return (
        <>
            {children(combinedLogic as any)}

            {showAxes && (
                <>
                    <axesHelper args={[100]} />
                    <gridHelper args={[100, 100, "#888888", "#444444"]} />
                </>
            )}

            <CaptureCamera
                name="Cam 0"
                isActive={activeCam === 0}
                position={cam0Pos}
                target={cam0Target}
                fov={70}
                autoRotate={autoRotate}
            />
        </>
    )
}

/**
 * BaseScene = Canvas + DOM overlays
 * Key idea: CameraStatus must be OUTSIDE Canvas so it's fixed to screen.
 */
export default function BaseScene({ children }: BaseSceneProps) {
    const settings = useSceneSettings()
    const { activeCam, showPerf } = settings
    const [hudData, setHudData] = useState({
        pos: { x: 0, y: 0, z: 0 },
        target: { x: 0, y: 0, z: 0 }
    })

    const handleHudUpdate = useCallback((pos: { x: number, y: number, z: number }, target: { x: number, y: number, z: number }) => {
        setHudData(prev => {
            const posChanged = Math.abs(prev.pos.x - pos.x) > 0.001 || Math.abs(prev.pos.y - pos.y) > 0.001 || Math.abs(prev.pos.z - pos.z) > 0.001
            const targetChanged = Math.abs(prev.target.x - target.x) > 0.001 || Math.abs(prev.target.y - target.y) > 0.001 || Math.abs(prev.target.z - target.z) > 0.001

            if (!posChanged && !targetChanged) {
                return prev
            }
            return {
                pos: { x: pos.x, y: pos.y, z: pos.z },
                target: { x: target.x, y: target.y, z: target.z }
            }
        })
    }, [])

    return (
        <div style={{ width: "100vw", height: "100vh", position: "relative" }}>
            {/* THREE */}
            <Canvas
                shadows
                dpr={Math.min(2, typeof window !== "undefined" ? window.devicePixelRatio : 1)}
                gl={{
                    antialias: true,
                    powerPreference: "default",
                    alpha: false,
                    stencil: false,
                    depth: true,
                    preserveDrawingBuffer: true,
                }}
                camera={{ position: [0.7, 1.78, -3], fov: 45 }}
                frameloop="always"
            >
                <InnerSceneContent
                    onHudUpdate={handleHudUpdate}
                    children={(innerLogic) => children(innerLogic)}
                />
            </Canvas>
        </div>
    )
}
