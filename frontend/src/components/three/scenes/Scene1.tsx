"use client"

import { Suspense } from "react"
import { Load3D } from "@/utils/load3d"
import { ComplexFactoryScene } from "../factory/ComplexFactory"
import { BaseLogic, useCameraSettings, useLightingSettings } from "@/hooks/useSceneLogic"
import Lighting from "../lighting/Lighting"
import CaptureCamera from "../cameras/CaptureCamera"

interface SceneContentProps {
    logic: BaseLogic
}

export default function Scene1({ logic }: SceneContentProps) {

    const {
        showBoundingBox,
        showCenterBox,
        mockMachineStates,
        activeCam,
        autoRotate
    } = logic

    const {
        cam1Settings,
        cam2Settings,
        cam3Settings,
        cam4Settings,
        cam5Settings,
        cam6Settings,
        cam7Settings,
        cam8Settings
    } = useCameraSettings({
        defCam1: { position: [0.5, 0, 9], target: [0, 3.5, 0], fov: 35, locking: true, isVisible: false }, //s
        defCam2: { position: [8, 3, 9], target: [0, 2.7, 0], fov: 35, locking: true, isVisible: false }, //s
        defCam3: { position: [0.3, 5, 8], target: [0, 2.1, 0], fov: 60, locking: true, isVisible: false }, //s

        defCam4: { position: [0.2, 1.97, -2], target: [0.1, 0.5, 0.38], fov: 70, locking: true, isVisible: false }, //d
        defCam5: { position: [0.2, 2.6, 1], target: [0.2, 0, 1], fov: 90, locking: true, isVisible: false }, //d
        defCam6: { position: [-0.2, 1, -0.3], target: [3, 1.5, 2.6], fov: 70, locking: true, isVisible: false }, //d
        defCam7: { position: [2.5, 0.75, -0.5], target: [1.22, 1.01, 1.3], fov: 70, locking: true, isVisible: false }, //d
        defCam8: { position: [1.56, 2.37, 2.24], target: [1.14, 1, 0], fov: 50, locking: true, isVisible: false } //d
    })

    const lightingSettings = useLightingSettings()

    return (
        <>
            {/* Background scene (keep it, but disable its lights if it has strong lighting) */}
            <ComplexFactoryScene machineStates={mockMachineStates} activeCam={activeCam} />

            {/* CINEMATIC LIGHTING RIG */}
            <Lighting {...lightingSettings} activeCam={activeCam} />

            {/* Factory Model */}
            <Suspense fallback={null}>
                <Load3D
                    url="/models/factory1.glb"
                    size={[10, 10, 10]}
                    worldCenter
                    boundingBox={showBoundingBox}
                    centerBox={showCenterBox}
                    castShadow
                    receiveShadow
                />
            </Suspense>

            {/* SCENE SPECIFIC CAMERAS */}
            <CaptureCamera
                name="Cam 1"
                isActive={activeCam === 1}
                position={cam1Settings.position as any}
                target={cam1Settings.target as any}
                fov={cam1Settings.fov}
                locking={cam1Settings.locking}
                isVisible={cam1Settings.isVisible}
                autoRotate={autoRotate}
            />

            <CaptureCamera
                name="Cam 2"
                isActive={activeCam === 2}
                position={cam2Settings.position as any}
                target={cam2Settings.target as any}
                fov={cam2Settings.fov}
                locking={cam2Settings.locking}
                isVisible={cam2Settings.isVisible}
                autoRotate={autoRotate}
            />

            <CaptureCamera
                name="Cam 3"
                isActive={activeCam === 3}
                position={cam3Settings.position as any}
                target={cam3Settings.target as any}
                fov={cam3Settings.fov}
                locking={cam3Settings.locking}
                isVisible={cam3Settings.isVisible}
                autoRotate={autoRotate}
            />

            <CaptureCamera
                name="Cam 4"
                isActive={activeCam === 4}
                position={cam4Settings.position as any}
                target={cam4Settings.target as any}
                fov={cam4Settings.fov}
                locking={cam4Settings.locking}
                isVisible={cam4Settings.isVisible}
                autoRotate={autoRotate}
            />

            <CaptureCamera
                name="Cam 5"
                isActive={activeCam === 5}
                position={cam5Settings.position as any}
                target={cam5Settings.target as any}
                fov={cam5Settings.fov}
                locking={cam5Settings.locking}
                isVisible={cam5Settings.isVisible}
                autoRotate={autoRotate}
            />

            <CaptureCamera
                name="Cam 6"
                isActive={activeCam === 6}
                position={cam6Settings.position as any}
                target={cam6Settings.target as any}
                fov={cam6Settings.fov}
                locking={cam6Settings.locking}
                isVisible={cam6Settings.isVisible}
                autoRotate={autoRotate}
            />

            <CaptureCamera
                name="Cam 7"
                isActive={activeCam === 7}
                position={cam7Settings.position as any}
                target={cam7Settings.target as any}
                fov={cam7Settings.fov}
                locking={cam7Settings.locking}
                isVisible={cam7Settings.isVisible}
                autoRotate={autoRotate}
            />

            <CaptureCamera
                name="Cam 8"
                isActive={activeCam === 8}
                position={cam8Settings.position as any}
                target={cam8Settings.target as any}
                fov={cam8Settings.fov}
                locking={cam8Settings.locking}
                isVisible={cam8Settings.isVisible}
                autoRotate={autoRotate}
            />
        </>
    )
}
