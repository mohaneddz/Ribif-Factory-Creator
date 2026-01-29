"use client"

import { useMemo, useRef, useState, useEffect } from "react"
import { useThree, useFrame } from "@react-three/fiber"
import { useControls, button } from "leva"

export interface CameraDef {
    position: [number, number, number]
    target: [number, number, number]
    fov: number
    isVisible?: boolean
    locking?: boolean
}

export interface SceneLogicParams {
    defCam1?: Partial<CameraDef>
    defCam2?: Partial<CameraDef>
    defCam3?: Partial<CameraDef>
    defCam4?: Partial<CameraDef>
    defCam5?: Partial<CameraDef>
    defCam6?: Partial<CameraDef>
    defCam7?: Partial<CameraDef>
    defCam8?: Partial<CameraDef>
}

/**
 * Hook for UI-only logic (Leva controls, settings)
 */
export function useSceneSettings() {
    const { currentScene, showPerf, showAxes, showBoundingBox, showCenterBox } = useControls("Settings", {
        currentScene: { options: { "Scene 1 (Factory)": 1, "Scene 2 (Demo)": 2 }, value: 1, label: "Active Scene" },
        showPerf: { value: true, label: "Show Performance" },
        showAxes: { value: true, label: "Show Axes" },
        showBoundingBox: { value: false, label: "Show Bounding Box" },
        showCenterBox: { value: false, label: "Show Center Box" },
    })

    const { activeCam, autoRotate } = useControls("Camera System", {
        activeCam: { options: { "Camera 0 (Free)": 0, "Camera 1": 1, "Camera 2": 2, "Camera 3": 3, "Camera 4": 4, "Camera 5": 5, "Camera 6": 6, "Camera 7": 7, "Camera 8": 8 }, value: 0, label: "Active Camera" },
        autoRotate: { value: false, label: "Auto Rotate" },
    })

    return {
        currentScene,
        showPerf,
        showAxes,
        showBoundingBox,
        showCenterBox,
        activeCam,
        autoRotate,
    }
}

/**
 * Hook for managing scene-specific camera Leva controls.
 */
export function useCameraSettings(params?: SceneLogicParams) {
    // Temporarily hidden from Debug UI
    const cam1Settings = {
        position: params?.defCam1?.position ?? [-0, 1.35, -1.63],
        target: params?.defCam1?.target ?? [0, 0, 0],
        fov: params?.defCam1?.fov ?? 50,
        isVisible: params?.defCam1?.isVisible ?? true,
        locking: params?.defCam1?.locking ?? true
    }

    const cam2Settings = {
        position: params?.defCam2?.position ?? [0, 50, 0],
        target: params?.defCam2?.target ?? [0, 0, 0],
        fov: params?.defCam2?.fov ?? 50,
        isVisible: params?.defCam2?.isVisible ?? true,
        locking: params?.defCam2?.locking ?? true
    }

    const cam3Settings = {
        position: params?.defCam3?.position ?? [0, 100, 0],
        target: params?.defCam3?.target ?? [0, 0, 0],
        fov: params?.defCam3?.fov ?? 45,
        isVisible: params?.defCam3?.isVisible ?? true,
        locking: params?.defCam3?.locking ?? true
    }

    const cam4Settings = {
        position: params?.defCam4?.position ?? [10, 10, 10],
        target: params?.defCam4?.target ?? [0, 0, 0],
        fov: params?.defCam4?.fov ?? 50,
        isVisible: params?.defCam4?.isVisible ?? true,
        locking: params?.defCam4?.locking ?? true
    }

    const cam5Settings = {
        position: params?.defCam5?.position ?? [-10, 10, 10],
        target: params?.defCam5?.target ?? [0, 0, 0],
        fov: params?.defCam5?.fov ?? 50,
        isVisible: params?.defCam5?.isVisible ?? true,
        locking: params?.defCam5?.locking ?? true
    }

    const cam6Settings = {
        position: params?.defCam6?.position ?? [10, 10, -10],
        target: params?.defCam6?.target ?? [0, 0, 0],
        fov: params?.defCam6?.fov ?? 50,
        isVisible: params?.defCam6?.isVisible ?? true,
        locking: params?.defCam6?.locking ?? true
    }

    const cam7Settings = {
        position: params?.defCam7?.position ?? [-10, 10, -10],
        target: params?.defCam7?.target ?? [0, 0, 0],
        fov: params?.defCam7?.fov ?? 50,
        isVisible: params?.defCam7?.isVisible ?? true,
        locking: params?.defCam7?.locking ?? true
    }

    const cam8Settings = {
        position: params?.defCam8?.position ?? [0, 20, 0],
        target: params?.defCam8?.target ?? [0, 0, 0],
        fov: params?.defCam8?.fov ?? 45,
        isVisible: params?.defCam8?.isVisible ?? true,
        locking: params?.defCam8?.locking ?? true
    }

    // Controls hooks and effects disabled to hide from UI
    /*
    const [cam1Settings, setCam1] = useControls("Camera 1", () => ({
        position: params?.defCam1?.position ?? [-0, 1.35, -1.63],
        target: params?.defCam1?.target ?? [0, 0, 0],
        fov: params?.defCam1?.fov ?? 50,
        isVisible: { value: params?.defCam1?.isVisible ?? true, label: "Show Helper" },
        locking: { value: params?.defCam1?.locking ?? true, label: "Lock (Tripod)" }
    }), [params?.defCam1])

    const [cam2Settings, setCam2] = useControls("Camera 2", () => ({
        position: params?.defCam2?.position ?? [0, 50, 0],
        target: params?.defCam2?.target ?? [0, 0, 0],
        fov: params?.defCam2?.fov ?? 50,
        isVisible: { value: params?.defCam2?.isVisible ?? true, label: "Show Helper" },
        locking: { value: params?.defCam2?.locking ?? true, label: "Lock (Tripod)" }
    }), [params?.defCam2])

    const [cam3Settings, setCam3] = useControls("Camera 3", () => ({
        position: params?.defCam3?.position ?? [0, 100, 0],
        target: params?.defCam3?.target ?? [0, 0, 0],
        fov: params?.defCam3?.fov ?? 45,
        isVisible: { value: params?.defCam3?.isVisible ?? true, label: "Show Helper" },
        locking: { value: params?.defCam3?.locking ?? true, label: "Lock (Tripod)" }
    }), [params?.defCam3])

    // Force update Leva when params change (e.g. Hot Reload or props update)
    useEffect(() => {
        if (params?.defCam1) setCam1(params.defCam1)
    }, [params?.defCam1, setCam1])

    useEffect(() => {
        if (params?.defCam2) setCam2(params.defCam2)
    }, [params?.defCam2, setCam2])

    useEffect(() => {
        if (params?.defCam3) setCam3(params.defCam3)
    }, [params?.defCam3, setCam3])
    */

    return {
        cam1Settings,
        cam2Settings,
        cam3Settings,
        cam4Settings,
        cam5Settings,
        cam6Settings,
        cam7Settings,
        cam8Settings,
    }
}

/**
 * Hook for managing lighting Leva controls.
 */
export function useLightingSettings() {
    /*
    return useControls("Lighting", {
        shadowsEnabled: { value: true, label: "Shadows" },
        softShadows: { value: true, label: "Soft Shadows" },
        ambientOn: { value: true, label: "Ambient Light" },
        dirOn: { value: true, label: "Directional Light" },
        lightPos: { value: [22, 28, 14], label: "Light Position" },
        intensity: { value: 3.2, min: 0, max: 20, label: "Intensity" },
        bias: { value: -0.00015, min: -0.001, max: 0.001, step: 0.00001, label: "Bias" },
        normalBias: { value: 0.02, min: 0, max: 0.1, step: 0.001, label: "Normal Bias" },
        radius: { value: 4, min: 0, max: 20, label: "Shadow Radius" },
        shadowResolution: { value: 4096, options: [512, 1024, 2048, 4096], label: "Shadow Res" },
        showHelpers: { value: false, label: "Show Light Helpers" },
    })
    */
    return {
        shadowsEnabled: true,
        softShadows: true,
        ambientOn: true,
        dirOn: true,
        lightPos: [22, 28, 14] as [number, number, number],
        intensity: 3.2,
        bias: -0.00015,
        normalBias: 0.02,
        radius: 4,
        shadowResolution: 4096,
        showHelpers: false,
    }
}

/**
 * Hook for Three.js specific logic (camera access, exports)
 * MUST be used INSIDE Canvas.
 */
export function useSceneThreeLogic() {
    // This will error if called outside Canvas
    const { gl, scene, camera } = useThree()
    const controlsRef = useRef<any>(null)

    /*
    const { screenshotCam } = useControls("Screenshot Tool", {
        screenshotCam: {
            options: {
                "Cam 0 (Free)": 0,
                "Cam 1": 1,
                "Cam 2": 2,
                "Cam 3": 3,
                "Cam 4": 4,
                "Cam 5": 5,
                "Cam 6": 6,
                "Cam 7": 7,
                "Cam 8": 8
            },
            value: 0,
            label: "Target Camera"
        },
        "Take Screenshot": button((get) => {
            const currentCamNum = get("Screenshot Tool.screenshotCam")
            take_camera_screenshot(gl, scene, currentCamNum, `camera-${currentCamNum}-${Date.now()}`)
        })
    })
    */

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

/**
 * Compatibility export for components that expect the old structure
 * Use with caution: will only work if called within the correct context
 */
export function useSceneLogic(params?: SceneLogicParams) {
    const settings = useSceneSettings()
    const camSettings = useCameraSettings(params)
    return {
        ...settings,
        ...camSettings,
        mockMachineStates: [] as { id: string, status: string, oee: number, temp: number }[],
        cordsLeftCorner: [0, 0, 0] as [number, number, number],
        cordsRightCorner: [0, 0, 0] as [number, number, number],
        gl: null as any,
        scene: null as any,
        camera: null as any,
        controlsRef: { current: null },
        handleExport: () => { },
    }
}

export type BaseLogic = ReturnType<typeof useSceneSettings> & ReturnType<typeof useSceneThreeLogic>
