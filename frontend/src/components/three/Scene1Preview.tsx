"use client";

import { useSceneSettings } from "@/hooks/useSceneLogic";
import { useSceneThreeLogic } from "@/hooks/useSceneThreeLogic";
import Scene1 from "@/components/three/scenes/Scene1";

export default function Scene1Preview() {
    const settings = useSceneSettings();
    const threeLogic = useSceneThreeLogic();
    const logic = { ...settings, ...threeLogic, activeCam: 0 };
    return <Scene1 logic={logic} />;
}
