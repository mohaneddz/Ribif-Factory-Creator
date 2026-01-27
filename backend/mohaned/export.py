"""
Export layout to PNG and DXF formats.
"""

import os
from typing import List, Dict, Tuple
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import ezdxf
from ezdxf import units

from models import Placed
from routing import Path
from config import CELL_MM, OUTPUT_DIR


def to_mm(x: int) -> int:
    """Convert grid cells to millimeters."""
    return int(x * CELL_MM)


def export_png_square(
    placed: List[Placed],
    paths: Dict[Tuple[str,str], Path],
    n: int,
    out_path: str,
) -> None:
    """Export layout as PNG image."""
    fig, ax = plt.subplots(figsize=(12, 12))
    ax.set_aspect("equal")

    # Draw belts first
    for _, path in paths.items():
        xs = [p[0] for p in path]
        ys = [p[1] for p in path]
        ax.plot(xs, ys, color='blue', linewidth=2, alpha=0.6)

    # Draw machines
    for p in placed:
        rect = Rectangle((p.x, p.y), p.w, p.h, fill=False, edgecolor='black', linewidth=2)
        ax.add_patch(rect)
        ax.text(p.x + p.w/2, p.y + p.h/2, p.uid, ha="center", va="center", fontsize=8)

    # outer square
    ax.add_patch(Rectangle((0, 0), n, n, fill=False, edgecolor='red', linewidth=3))

    ax.set_xlim(-1, n + 1)
    ax.set_ylim(-1, n + 1)
    ax.invert_yaxis()
    ax.axis("off")
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    plt.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"[+] PNG saved: {out_path}")


def export_dxf_square(
    placed: List[Placed],
    paths: Dict[Tuple[str,str], Path],
    n: int,
    out_path: str,
) -> None:
    """Export layout as DXF file with real dimensions."""
    doc = ezdxf.new(setup=True)
    doc.units = units.MM
    msp = doc.modelspace()

    # layers
    if "MACHINES" not in doc.layers:
        doc.layers.add("MACHINES")
    if "BELTS" not in doc.layers:
        doc.layers.add("BELTS")
    if "BOUNDARY" not in doc.layers:
        doc.layers.add("BOUNDARY")

    # boundary square in mm
    size_mm = to_mm(n)
    msp.add_lwpolyline([(0,0),(size_mm,0),(size_mm,size_mm),(0,size_mm),(0,0)], dxfattribs={"layer":"BOUNDARY"})

    # machines (rects with real dimensions)
    for p in placed:
        x1 = to_mm(p.x)
        y1 = to_mm(p.y)
        x2 = to_mm(p.x + p.w)
        y2 = to_mm(p.y + p.h)
        msp.add_lwpolyline([(x1,y1),(x2,y1),(x2,y2),(x1,y2),(x1,y1)], dxfattribs={"layer":"MACHINES"})
        # Add centered text label
        cx = x1 + (x2-x1)/2
        cy = y1 + (y2-y1)/2
        msp.add_text(p.uid, dxfattribs={
            "height": 500, 
            "layer": "MACHINES"
        }).set_placement(
            (cx, cy),
            align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER
        )

    # belts
    for _, path in paths.items():
        pts = [(to_mm(x), to_mm(y)) for (x,y) in path]
        if len(pts) >= 2:
            msp.add_lwpolyline(pts, dxfattribs={"layer":"BELTS"})

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    doc.saveas(out_path)
    print(f"[+] DXF saved: {out_path}")
