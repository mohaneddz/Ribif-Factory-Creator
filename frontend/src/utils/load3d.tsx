import React, { Suspense, useLayoutEffect, useMemo, useRef, useState } from "react"
import { useGLTF, Clone, Edges } from "@react-three/drei"
import { useFrame } from "@react-three/fiber"
import * as THREE from "three"

interface Load3DProps {
    url: string
    size: [number, number, number]
    position?: [number, number, number]
    rotation?: [number, number, number]
    centered?: boolean          // center to its bounds center
    worldCenter?: boolean       // force model center to world origin
    castShadow?: boolean
    receiveShadow?: boolean
    boundingBox?: boolean
    centerBox?: boolean
    wireframe?: boolean         // simplified "blueprint" wireframe
    pulse?: boolean             // shimmer pulse effect
    placeholder?: boolean | React.ReactNode // display placeholder while loading
}

/**
 * Inner component that handles GLTF loading and manipulation
 */
function ModelRenderer({
    url,
    size,
    centered,
    worldCenter,
    castShadow,
    receiveShadow,
    boundingBox,
    centerBox,
    wireframe,
    pulse,
    rootRef
}: Omit<Load3DProps, "position" | "rotation" | "placeholder"> & { rootRef: React.RefObject<THREE.Group | null> }) {
    const { scene } = useGLTF(url)
    const model = useRef<THREE.Group>(null)
    const [debugInfo, setDebugInfo] = useState<{ center: THREE.Vector3; size: THREE.Vector3 } | null>(null)

    const scale = useMemo(() => {
        const box = new THREE.Box3().setFromObject(scene)
        const boxSize = box.getSize(new THREE.Vector3())
        const safe = (v: number) => (v > 1e-8 ? v : 1)
        const s = Math.min(size[0] / safe(boxSize.x), size[1] / safe(boxSize.y), size[2] / safe(boxSize.z)) || 1
        return s
    }, [scene, size])

    // Apply shadows and prepare pulse
    useLayoutEffect(() => {
        scene.traverse((o) => {
            const m = o as THREE.Mesh
            if (!m.isMesh) return

            m.castShadow = !!castShadow
            m.receiveShadow = !!receiveShadow

            if (m.material) {
                const materials = Array.isArray(m.material) ? m.material : [m.material]
                materials.forEach((mat: any) => {
                    // Hidden meshes if we are in "pure wireframe" mode or just toggling pulse transparency
                    if (pulse) mat.transparent = true
                })
            }
        })
    }, [scene, castShadow, receiveShadow, pulse])

    // Pulse Effect
    useFrame((state) => {
        if (!pulse) return
        const time = state.clock.getElapsedTime()
        const pulseValue = (Math.sin(time * 3) + 1) / 2 // 0 to 1
        
        scene.traverse((o) => {
            const m = o as THREE.Mesh
            if (!m.isMesh) return
            
            const materials = Array.isArray(m.material) ? m.material : [m.material]
            materials.forEach((mat: any) => {
                if (mat.opacity !== undefined) {
                    mat.opacity = 0.4 + pulseValue * 0.6
                }
                if (mat.emissive) {
                    const brightness = pulseValue * 0.5
                    mat.emissive.setRGB(brightness, brightness, brightness)
                }
            })
        })
    })

    // Formatting / Recenter
    useLayoutEffect(() => {
        if (!model.current) return

        model.current.position.set(0, 0, 0)
        model.current.rotation.set(0, 0, 0)
        model.current.scale.set(scale, scale, scale)
        model.current.updateWorldMatrix(true, true)

        const box = new THREE.Box3().setFromObject(model.current)
        const center = box.getCenter(new THREE.Vector3())

        if (centered || worldCenter) {
            model.current.position.x -= center.x
            model.current.position.y -= box.min.y
            model.current.position.z -= center.z
            model.current.updateWorldMatrix(true, true)
        }

        if (worldCenter && rootRef.current) {
            rootRef.current.position.set(0, 0, 0)
        }

        if ((boundingBox || centerBox) && model.current) {
            const finalBox = new THREE.Box3().setFromObject(model.current)
            const finalSize = finalBox.getSize(new THREE.Vector3())
            const finalCenter = finalBox.getCenter(new THREE.Vector3())

            if (rootRef.current) {
                rootRef.current.worldToLocal(finalCenter)
            }
            setDebugInfo({ center: finalCenter, size: finalSize })
        } else {
            setDebugInfo(null)
        }
    }, [scene, scale, centered, worldCenter, boundingBox, centerBox, rootRef])

    // Create a simplified wireframe clone of the scene if requested
    const wireframeElement = useMemo(() => {
        if (!wireframe) return null
        
        // We clone for wireframe to avoid mutating the original scene materials
        return (
            <group>
                <Clone object={scene}>
                    {/* Using Edges from drei inside a Clone's injection callback or as a child? 
                        Actually, Edges works best injected into every mesh. 
                        Since Clone is a black box, we will traverse the scene and manually render lines.
                    */}
                    {null}
                </Clone>
                {/* Fallback to traversal for Edges since Clone doesn't easily expose children for Edges injection */}
            </group>
        )
    }, [wireframe, scene])

    // Manual Wireframe Traversal for "Edges"
    const edgesElements: React.ReactNode[] = []
    if (wireframe) {
        scene.traverse((o: any) => {
            if (o.isMesh) {
                edgesElements.push(
                    <primitive object={o} key={o.uuid}>
                        <Edges threshold={15} color="#00dbde" />
                    </primitive>
                )
            }
        })
    }

    return (
        <>
            <group ref={model}>
                {/* Hide the main model surface if wireframe is active */}
                {!wireframe && <Clone object={scene} />}
                
                {/* Simplified Wireframe (Edges) Layer - Always visible if wireframe is true */}
                {wireframe && (
                    <group>
                        {scene.children.map((child, i) => (
                           <WireframeNode key={i} node={child} />
                        ))}
                    </group>
                )}
            </group>

            {boundingBox && debugInfo && (
                <mesh position={debugInfo.center}>
                    <boxGeometry args={[debugInfo.size.x, debugInfo.size.y, debugInfo.size.z]} />
                    <meshBasicMaterial color="lime" wireframe transparent opacity={0.5} />
                </mesh>
            )}

            {centerBox && debugInfo && (
                <mesh position={debugInfo.center}>
                    <boxGeometry args={[0.2, 0.2, 0.2]} />
                    <meshBasicMaterial color="red" />
                </mesh>
            )}
        </>
    )
}

/**
 * Recursive component to apply Edges to all sub-meshes
 */
function WireframeNode({ node }: { node: any }) {
    if (node.isMesh) {
        return (
            <mesh position={node.position} rotation={node.rotation} scale={node.scale}>
                <primitive object={node.geometry} attach="geometry" />
                <meshBasicMaterial transparent opacity={0} depthWrite={false} />
                <Edges threshold={15} color="#00dbde" />
            </mesh>
        )
    }

    if (node.children?.length > 0) {
        return (
            <group position={node.position} rotation={node.rotation} scale={node.scale}>
                {node.children.map((child: any, i: number) => (
                    <WireframeNode key={i} node={child} />
                ))}
            </group>
        )
    }

    return null
}

/**
 * Placeholder component
 */
function DefaultPlaceholder({ size }: { size: [number, number, number] }) {
    return (
        <mesh position={[0, size[1] / 2, 0]}>
            <boxGeometry args={size} />
            <meshStandardMaterial 
                color="#222" 
                transparent 
                opacity={0.2} 
                wireframe 
            />
        </mesh>
    )
}

export const Load3D = React.memo(function Load3D(props: Load3DProps) {
    const {
        position = [0, 0, 0],
        rotation = [0, 0, 0],
        worldCenter = true,
        placeholder = false,
        size
    } = props

    const root = useRef<THREE.Group>(null)

    const fallback = useMemo(() => {
        if (!placeholder) return null
        if (typeof placeholder === "boolean") {
            return <DefaultPlaceholder size={size} />
        }
        return placeholder
    }, [placeholder, size])

    return (
        <group ref={root} position={worldCenter ? [0, 0, 0] : position} rotation={rotation}>
            <Suspense fallback={fallback}>
                <ModelRenderer {...props} rootRef={root} />
            </Suspense>
        </group>
    )
})

useGLTF.preload = (url: string) => useGLTF.preload(url)
