"use client"

interface Props {
  activeCam: number
  pos: { x: number; y: number; z: number }
  target: { x: number; y: number; z: number }
}

export default function CameraStatusHUD({ activeCam, pos, target }: Props) {
  const camLabel = activeCam === 0 ? "FREE" : `CAM_${activeCam}`

  return (
    <div className="fixed bottom-0 right-0 z-[999999] pointer-events-none p-6 font-mono text-[#00dbde] [text-shadow:0_0_10px_rgba(0,219,222,0.5)] text-[10px] flex flex-col items-end gap-1 bg-black min-w-[220px]">

      <div className="flex flex-col gap-1 w-full items-end">
        <div className="flex gap-2">
          <span className="opacity-50">POS:</span>
          <span className="text-white tracking-wider">
            X: {pos.x.toFixed(2)} Y: {pos.y.toFixed(2)} Z: {pos.z.toFixed(2)}
          </span>
        </div>

        <div className="flex gap-2">
          <span className="opacity-50">LOOKING AT:</span>
          <span className="text-white tracking-wider">
            X: {target.x.toFixed(2)} Y: {target.y.toFixed(2)} Z: {target.z.toFixed(2)}
          </span>
        </div>
      </div>
    </div>
  )
}
