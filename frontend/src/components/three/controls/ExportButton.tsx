"use client"

import React from "react"
import { useThree } from "@react-three/fiber"
import { Html } from "@react-three/drei"

export default function ExportButton() {
    const { gl, scene, camera } = useThree()

    const handleExport = () => {
        // Force a render to ensure the buffer is up to date
        gl.render(scene, camera)

        const dataURL = gl.domElement.toDataURL("image/png")
        const link = document.createElement("a")
        link.download = `capture-${new Date().toISOString()}.png`
        link.href = dataURL
        link.click()
    }

    return (
        <Html
            style={{
                position: "fixed",
                bottom: "80px", // Offset slightly above bottom to avoid overlap if needed
                left: "20px",
                width: "150px"
            }}
        >
            <button
                onClick={handleExport}
                style={{
                    padding: "12px 24px",
                    backgroundColor: "#007AFF",
                    color: "white",
                    border: "none",
                    borderRadius: "8px",
                    fontWeight: "bold",
                    cursor: "pointer",
                    boxShadow: "0 4px 6px rgba(0,0,0,0.1)",
                    transition: "transform 0.2s, background-color 0.2s",
                    whiteSpace: "nowrap"
                }}
                onMouseOver={(e) => (e.currentTarget.style.backgroundColor = "#0056b3")}
                onMouseOut={(e) => (e.currentTarget.style.backgroundColor = "#007AFF")}
                onMouseDown={(e) => (e.currentTarget.style.transform = "scale(0.95)")}
                onMouseUp={(e) => (e.currentTarget.style.transform = "scale(1)")}
            >
                Export PNG
            </button>
        </Html>
    )
}
