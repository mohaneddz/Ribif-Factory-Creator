import * as THREE from 'three';

/**
 * Utility function to take a screenshot from a specific camera in the scene.
 * @param gl The WebGLRenderer instance
 * @param scene The THREE.Scene instance
 * @param camNum The camera number to look for (assumes camera is named "Cam {camNum}")
 * @param save Optional filename to save the screenshot. If provided, triggers a download.
 * @returns The data URL of the captured image
 */
export const take_camera_screenshot = (
    gl: THREE.WebGLRenderer,
    scene: THREE.Scene,
    camNum: number,
    save?: string | null
): string => {
    let targetCamera: THREE.Camera | undefined;
    const camName = `Cam ${camNum}`;

    // Find the camera by name in the scene
    scene.traverse((obj) => {
        if (obj instanceof THREE.Camera && obj.name === camName) {
            targetCamera = obj;
        }
    });

    if (!targetCamera) {
        console.error(`[ScreenshotUtils] Camera "${camName}" not found in scene.`);
        return "";
    }

    // Render the specific camera to the canvas
    if (targetCamera.userData.target) {
        targetCamera.lookAt(targetCamera.userData.target);
    }

    // Force matrices to update one last time
    targetCamera.updateMatrixWorld(true);
    if ((targetCamera as any).isPerspectiveCamera) {
        (targetCamera as any).updateProjectionMatrix();
    }

    // Render the specific camera to the canvas
    // We use gl.render(scene, camera) directly. 
    // Since R3F's auto-render is handled by useFrame, this manual call
    // writes to the buffer right before we capture it.
    gl.clear(); // Clear depth/color to ensure no leftovers
    gl.render(scene, targetCamera);
    const dataURL = gl.domElement.toDataURL("image/png");

    if (save) {
        const filename = save.endsWith(".png") ? save : `${save}.png`;
        const link = document.createElement("a");
        link.download = filename;
        link.href = dataURL;
        link.click();
    }

    return dataURL;
};

interface PerspectiveArgs {
    position: [number, number, number];
    target: [number, number, number];
    fov?: number;
    aspect?: number;
    // Add more screenshot related things here if needed (e.g. resolution)
}

/**
 * Utility function to take a screenshot from a custom perspective.
 * @param gl The WebGLRenderer instance
 * @param scene The THREE.Scene instance
 * @param args Perspective arguments (position, target, fov, etc)
 * @param save Optional filename to save the screenshot. If provided, triggers a download.
 * @returns The data URL of the captured image
 */
export const take_perspective_screenshot = (
    gl: THREE.WebGLRenderer,
    scene: THREE.Scene,
    args: PerspectiveArgs,
    save?: string | null
): string => {
    const fov = args.fov || 50;
    const aspect = args.aspect || gl.domElement.width / gl.domElement.height;

    // Create a temporary camera
    const tempCam = new THREE.PerspectiveCamera(fov, aspect, 0.1, 2000);
    tempCam.position.set(...args.position);
    tempCam.lookAt(new THREE.Vector3(...args.target));
    tempCam.updateMatrixWorld();

    // Render the temporary camera
    gl.render(scene, tempCam);
    const dataURL = gl.domElement.toDataURL("image/png");

    if (save) {
        const filename = save.endsWith(".png") ? save : `${save}.png`;
        const link = document.createElement("a");
        link.download = filename;
        link.href = dataURL;
        link.click();
    }

    return dataURL;
};
