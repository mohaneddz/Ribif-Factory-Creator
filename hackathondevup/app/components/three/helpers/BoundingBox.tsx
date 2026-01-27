"use client"

import React, { useLayoutEffect, useRef } from "react"
import * as THREE from "three"

interface BoundingBoxProps {
    /** The minimum corner of the bounding box [x, y, z] */
    leftCorner: [number, number, number] | THREE.Vector3
    /** The maximum corner of the bounding box [x, y, z] */
    rightCorner: [number, number, number] | THREE.Vector3
    /** The components to be scaled and positioned within the box */
    children: React.ReactNode
    /** Optional: whether to maintain aspect ratio (uniform scaling). Defaults to false (stretches to fill) */
    keepAspectRatio?: boolean
    /** Optional: debug mode to show the box boundaries */
    debug?: boolean
}

/**
 * BoundingBox component
 * Automatically scales and positions its children to fit within the space
 * defined by the leftCorner and rightCorner.
 */
export default function BoundingBox({
    leftCorner,
    rightCorner,
    children,
    keepAspectRatio = false,
    debug = false,
}: BoundingBoxProps) {
    const outerRef = useRef<THREE.Group>(null)
    const innerRef = useRef<THREE.Group>(null)

    const min = Array.isArray(leftCorner) ? new THREE.Vector3(...leftCorner) : leftCorner
    const max = Array.isArray(rightCorner) ? new THREE.Vector3(...rightCorner) : rightCorner

    const targetSize = new THREE.Vector3().subVectors(max, min)
    const targetCenter = new THREE.Vector3().addVectors(min, max).multiplyScalar(0.5)

    useLayoutEffect(() => {
        if (!innerRef.current || !outerRef.current) return

        const updateLayout = () => {
            if (!innerRef.current) return

            // 1. Reset inner group to measure original bounds of children
            innerRef.current.scale.set(1, 1, 1)
            innerRef.current.position.set(0, 0, 0)
            innerRef.current.updateWorldMatrix(true, true)

            // 2. Compute current bounding box of the children
            const box = new THREE.Box3().setFromObject(innerRef.current)

            // If the box is empty or collapsed, we can't scale
            if (box.isEmpty()) return

            const currentSize = box.getSize(new THREE.Vector3())
            const currentCenter = box.getCenter(new THREE.Vector3())

            // 3. Calculate scale factors
            const safe = (v: number) => (v > 1e-6 ? v : 1)
            let sx = targetSize.x / safe(currentSize.x)
            let sy = targetSize.y / safe(currentSize.y)
            let sz = targetSize.z / safe(currentSize.z)

            if (keepAspectRatio) {
                const minScale = Math.min(sx, sy, sz)
                sx = sy = sz = minScale
            }

            // 4. Update inner group transform
            innerRef.current.scale.set(sx, sy, sz)

            // Re-measure after scaling to get the new center, or calculate it:
            // The relative center shift needed:
            // We want (currentCenter * scale) + position = targetCenter
            // position = targetCenter - (currentCenter * scale)
            innerRef.current.position.set(
                targetCenter.x - currentCenter.x * sx,
                targetCenter.y - currentCenter.y * sy,
                targetCenter.z - currentCenter.z * sz
            )
        }

        // Run once
        updateLayout()

        // Some children might be models that take time to load or update
        // We can use a small observer or just rely on React's lifecycle if they trigger re-renders
        // For GLTF models, they might need a bit more care.
        // We'll add a small timeout or just run it on next tick if needed, 
        // but useLayoutEffect should be enough if children are already "ready".
        // If they are React Three Fiber components, they usually populate the scene graph immediately.

        const timeout = setTimeout(updateLayout, 100)
        return () => clearTimeout(timeout)

    }, [children, leftCorner, rightCorner, keepAspectRatio, targetSize, targetCenter])

    return (
        <group ref={outerRef}>
            {debug && (
                <mesh position={targetCenter}>
                    <boxGeometry args={[targetSize.x, targetSize.y, targetSize.z]} />
                    <meshBasicMaterial color="lime" wireframe transparent opacity={0.3} />
                </mesh>
            )}
            <group ref={innerRef}>
                {children}
            </group>
        </group>
    )
}
