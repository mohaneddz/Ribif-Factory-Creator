"use client"

import BaseScene from "./BaseScene"
import Scene1 from "./Scene1"
import Scene2 from "./Scene2"

/**
 * Main Scene component that handles the shared infrastructure (via BaseScene)
 * and switches between different scene contents based on user selection.
 */
export default function Scene() {
    return (
        <BaseScene>
            {(logic) => (
                <>
                    {logic.currentScene === 1 && <Scene1 logic={logic} />}
                    {logic.currentScene === 2 && <Scene2 logic={logic} />}
                </>
            )}
        </BaseScene>
    )
}
