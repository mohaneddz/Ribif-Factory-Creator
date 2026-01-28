"use client"

import React, { useRef, useEffect, useMemo } from "react"
import { PerspectiveCamera, OrbitControls } from "@react-three/drei"
import { useThree, useFrame, RootState } from "@react-three/fiber"
import * as THREE from "three"

interface CaptureCameraProps {
    name: string
    isActive: boolean
    isVisible?: boolean
    locking?: boolean
    position: [number, number, number]
    target: [number, number, number]
    fov: number
    autoRotate?: boolean
    onCameraReady?: (camera: THREE.PerspectiveCamera) => void
}

export default function CaptureCamera({
    name,
    isActive,
    isVisible = false,
    locking = false,
    position,
    target,
    fov,
    autoRotate = false,
    onCameraReady
}: CaptureCameraProps) {
    const cameraRef = useRef<THREE.PerspectiveCamera>(null!)
    const controlsRef = useRef<any>(null)
    const setQuery = useThree((state) => state.set)

    useEffect(() => {
        if (isActive && cameraRef.current) {
            setQuery({ camera: cameraRef.current })
        }
    }, [isActive, setQuery])

    useEffect(() => {
        if (cameraRef.current && onCameraReady) {
            onCameraReady(cameraRef.current)
        }
    }, [onCameraReady])

    // Sync position and target when props change or when becoming active
    useEffect(() => {
        if (cameraRef.current) {
            cameraRef.current.position.set(...position)
            // Store target in userData so screenshot utility can find it
            cameraRef.current.userData.target = new THREE.Vector3(...target)
        }
        if (controlsRef.current) {
            controlsRef.current.target.set(...target)
            controlsRef.current.update()
        }
    }, [position, target, isActive])

    // Base direction and axes for looking around
    const baseDirParams = useMemo(() => {
        const posVec = new THREE.Vector3(...position)
        const tarVec = new THREE.Vector3(...target)
        const forward = new THREE.Vector3().subVectors(tarVec, posVec).normalize()
        const right = new THREE.Vector3().crossVectors(forward, new THREE.Vector3(0, 1, 0)).normalize()
        const up = new THREE.Vector3().crossVectors(right, forward).normalize()
        return { posVec, forward, right, up }
    }, [position, target])

    // Track mouse drag for looking around in tripod mode
    const dragOffset = useRef({ x: 0, y: 0 })
    const isDragging = useRef(false)

    useEffect(() => {
        if (!isActive || !locking) return

        const onMouseDown = (e: MouseEvent) => {
            if (e.button === 0) isDragging.current = true
        }
        const onMouseUp = () => {
            isDragging.current = false
        }
        const onMouseMove = (e: MouseEvent) => {
            if (isDragging.current) {
                // Sensitivity for looking around
                const sensitivity = 0.002
                dragOffset.current.x += e.movementX * sensitivity
                dragOffset.current.y -= e.movementY * sensitivity

                // Optional: Clamp vertical look if needed
                dragOffset.current.y = Math.max(-1, Math.min(1, dragOffset.current.y))
            }
        }

        window.addEventListener('mousedown', onMouseDown)
        window.addEventListener('mouseup', onMouseUp)
        window.addEventListener('mousemove', onMouseMove)

        return () => {
            window.removeEventListener('mousedown', onMouseDown)
            window.removeEventListener('mouseup', onMouseUp)
            window.removeEventListener('mousemove', onMouseMove)
        }
    }, [isActive, locking])

    // Update target dynamically on drag if locked
    useFrame(() => {
        if (isActive && controlsRef.current) {
            if (locking) {
                const { posVec, forward, right, up } = baseDirParams

                // Calculate a point far away based on accumulated drag offset
                const targetPoint = posVec.clone()
                    .add(forward)
                    .add(right.clone().multiplyScalar(dragOffset.current.x))
                    .add(up.clone().multiplyScalar(dragOffset.current.y))

                // We want the controls target to be very far away to act like "looking"
                const dir = targetPoint.clone().sub(posVec).normalize()
                controlsRef.current.target.copy(posVec.clone().add(dir.multiplyScalar(10)))
            }

            // Always sync back to userData for screenshot utility
            if (cameraRef.current) {
                cameraRef.current.userData.target = controlsRef.current.target.clone()
            }
        }
    })


    return (
        <>
            <PerspectiveCamera
                ref={cameraRef}
                name={name}
                makeDefault={isActive}
                fov={fov}
                near={0.1}
                far={2000}
            />
            {cameraRef.current && isVisible && <cameraHelper args={[cameraRef.current]} />}
            {isActive && (
                <OrbitControls
                    ref={controlsRef}
                    makeDefault
                    enablePan={!locking}
                    enableZoom={!locking}
                    enableRotate={!locking} // Disable left click rotation when locked
                    autoRotate={autoRotate}
                    autoRotateSpeed={0.5}
                    enableDamping={true}
                    dampingFactor={0.05}
                    key={isActive ? (locking ? 'tripod' : 'free') : 'inactive'}
                />
            )}
        </>
    )
}
