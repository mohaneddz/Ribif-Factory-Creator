"use client"

import { useMemo, useRef } from "react"
import { useThree } from "@react-three/fiber"

/**
 * Hook for Three.js specific logic (camera access, exports)
 * MUST be used INSIDE Canvas - this file should only be imported by
 * components that are dynamically loaded with ssr: false
 */
export function useSceneThreeLogic() {
    const { gl, scene, camera } = useThree()
    const controlsRef = useRef<any>(null)

    const handleExport = () => {
        gl.render(scene, camera)
        const dataURL = gl.domElement.toDataURL("image/png")
        const link = document.createElement("a")
        link.download = `capture-${new Date().toISOString()}.png`
        link.href = dataURL
        link.click()
    }

    const mockMachineStates = useMemo(() => [
        { id: "INJ-100T-01", status: "running", oee: 88, temp: 190 },
        { id: "EXT-120-01", status: "running", oee: 92, temp: 210 },
        { id: "RCY-GRIND-01", status: "warning", oee: 75, temp: 45 },
    ], [])

    return {
        gl,
        scene,
        camera,
        controlsRef,
        handleExport,
        mockMachineStates,
    }
}
