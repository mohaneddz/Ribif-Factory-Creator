import React from 'react'

export default function PrimitiveShapes({ shadowsEnabled }: { shadowsEnabled: boolean }) {
    return (
        <>
            {/* Scattered Cubes */}
            <mesh position={[0, 0, 0]} castShadow={shadowsEnabled} receiveShadow={shadowsEnabled}>
                <boxGeometry args={[1, 1, 1]} />
                <meshStandardMaterial color="hotpink" roughness={0.3} />
            </mesh>
            <mesh position={[0, 0, 0]} castShadow={shadowsEnabled} receiveShadow={shadowsEnabled}>
                <boxGeometry args={[2, 2, 2]} />
                <meshStandardMaterial color="orange" roughness={0.5} />
            </mesh>

            {/* Scattered Spheres */}
            <mesh position={[0, 0, 0]} castShadow={shadowsEnabled} receiveShadow={shadowsEnabled}>
                <sphereGeometry args={[1, 32, 32]} />
                <meshStandardMaterial color="lightblue" roughness={0.1} metalness={0.2} />
            </mesh>

            {/* Cone */}
            <mesh position={[0, 0, 0]} castShadow={shadowsEnabled} receiveShadow={shadowsEnabled}>
                <coneGeometry args={[1, 2, 32]} />
                <meshStandardMaterial color="lightgreen" />
            </mesh>
        </>
    )
}
