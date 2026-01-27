"use client"

import { Grid } from "@react-three/drei"

/**
 * Simplified Factory Background (No animated machines or labels)
 */
export const ComplexFactoryScene = ({ machineStates, activeCam = 0 }: { machineStates: any[], activeCam?: number }) => {
    return (
        <group name="ComplexFactoryBackground">

            {activeCam === 0 && (
                <Grid position={[0, 0, 0]} args={[100, 100]} cellColor="#303030" sectionColor="#505050" infiniteGrid fadeDistance={50} />
            )}

        </group>
    );
};
