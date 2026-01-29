"""
Visualization layer: DXF and PNG rendering.
This is the only place where grid coordinates are scaled to millimeters.
"""
from __future__ import annotations

import os
import math
from typing import Dict, List, Optional, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image, ImageOps, ImageChops
import ezdxf
from ezdxf import units

from config import (
    CELL_MM,
    DXF_BLACK,
    DXF_BLUE,
    WALL_THICK_MM,
    WALL_HATCH_STEP,
    PILLAR_SIZE_MM,
    DOOR_WIDTH_MM,
    DOOR_DEPTH_MM,
    PIPE_GAP_MM,
    PIPE_LINE_WIDTH_MM,
    TEXT_H_MM,
    LEGEND_TEXT_H_MM,
    GRID_MM,
    AISLE_MM,
    BELT_HALF_WIDTH_MM,
    BELT_COLOR_MAIN,
    BELT_COLOR_EDGE,
    EMBED_IMAGES_IN_CAD,
    PNG_MACHINE_SCALE,
)
from log_utils import info, warn

Flow = Tuple[str, str]
Node = Tuple[int, int]
Path = List[Node]


class FactoryRenderer:
    def __init__(self, cell_mm: int = CELL_MM):
        self.cell_mm = cell_mm

    def _to_mm(self, v: int) -> int:
        return int(v * self.cell_mm)

    def _node_to_mm(self, node: Node) -> Tuple[float, float]:
        # Use cell centers for belt drawing
        return ((node[0] + 0.5) * self.cell_mm, (node[1] + 0.5) * self.cell_mm)

    def _placed_to_mm(self, p: Dict[str, object]) -> Dict[str, object]:
        return {
            "machine": p.get("machine", {}),
            "uid": p.get("uid"),
            "x": self._to_mm(int(p.get("x", 0))),
            "y": self._to_mm(int(p.get("y", 0))),
            "w": self._to_mm(int(p.get("w", 0))),
            "h": self._to_mm(int(p.get("h", 0))),
            "rot": p.get("rot", 0),
            "img_path": p.get("img_path"),
        }

    # =========================
    # PNG Rendering
    # =========================
    def render_png(
        self,
        layout_data: Dict[str, object],
        paths: Dict[Flow, Path],
        images_map: Optional[Dict[str, str]],
        output_path: str,
    ) -> None:
        placed = [self._placed_to_mm(p) for p in layout_data.get("placed", [])]

        all_machines = placed
        centers = {
            m["uid"]: (m["x"] + m["w"] / 2.0, m["y"] + m["h"] / 2.0)
            for m in all_machines
        }

        draw_items = []
        visual_rects = []

        for i, p in enumerate(all_machines):
            cx = p["x"] + p["w"] / 2.0
            cy = p["y"] + p["h"] / 2.0
            box_w = max(1.0, p["w"] * 0.9 * PNG_MACHINE_SCALE)
            box_h = max(1.0, p["h"] * 0.9 * PNG_MACHINE_SCALE)

            img_path = self._resolve_image_path(p, images_map)

            if img_path and os.path.exists(img_path):
                try:
                    im = Image.open(img_path).convert("RGBA")
                    im = ImageOps.exif_transpose(im)
                    im = trim_whitespace(im)

                    iw_px, ih_px = im.size
                    aspect = iw_px / ih_px if ih_px else 1.0
                    box_aspect = box_w / box_h if box_h else 1.0

                    if aspect > box_aspect:
                        draw_w = box_w
                        draw_h = box_w / aspect
                    else:
                        draw_h = box_h
                        draw_w = box_h * aspect

                    draw_x = cx - (draw_w / 2.0)
                    draw_y = cy - (draw_h / 2.0)

                    draw_items.append({"im": im, "extent": [draw_x, draw_x + draw_w, draw_y, draw_y + draw_h], "z": 10})
                    visual_rects.append((draw_x, draw_y, draw_x + draw_w, draw_y + draw_h))
                except Exception as exc:
                    warn(f"Image load failed for {img_path}: {exc}")
                    visual_rects.append((p["x"], p["y"], p["x"] + p["w"], p["y"] + p["h"]))
            else:
                visual_rects.append((p["x"], p["y"], p["x"] + p["w"], p["y"] + p["h"]))

        if not visual_rects:
            visual_rects = [self._rect_bounds(m["x"], m["y"], m["w"], m["h"]) for m in all_machines]

        minx, miny, maxx, maxy = self._compute_bounds_rects(visual_rects)

        pad_w = (maxx - minx) * 0.05
        pad_h = (maxy - miny) * 0.05
        minx -= pad_w
        maxx += pad_w
        miny -= pad_h
        maxy += pad_h

        current_w = maxx - minx
        current_h = maxy - miny
        target_aspect = 1.0

        if current_w / current_h > target_aspect:
            target_h = current_w / target_aspect
            diff = target_h - current_h
            miny -= diff / 2
            maxy += diff / 2
        else:
            target_w = current_h * target_aspect
            diff = target_w - current_w
            minx -= diff / 2
            maxx += diff / 2

        fig = plt.figure(figsize=(16, 9), dpi=100)
        ax = fig.add_subplot(111)
        ax.set_facecolor("#00FF00")
        fig.patch.set_facecolor("#00FF00")

        # Draw conveyors from routing paths
        for (src, dst), path in paths.items():
            pts = [self._node_to_mm(n) for n in path]
            if src in centers and dst in centers:
                pts = [centers[src]] + pts + [centers[dst]] if pts else [centers[src], centers[dst]]
            if len(pts) >= 2:
                _draw_conveyor_belt(ax, pts, width_mm=BELT_HALF_WIDTH_MM * 2)

        for item in draw_items:
            ax.imshow(item["im"], extent=item["extent"], zorder=item["z"])

        ax.set_xlim(minx, maxx)
        ax.set_ylim(miny, maxy)
        ax.set_aspect("equal", adjustable="box")
        ax.axis("off")
        plt.tight_layout(pad=0)

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        fig.savefig(output_path, bbox_inches="tight", pad_inches=0)
        plt.close(fig)
        info(f"PNG saved: {output_path}")

    # =========================
    # DXF Rendering
    # =========================
    def render_dxf(
        self,
        layout_data: Dict[str, object],
        paths: Dict[Flow, Path],
        output_path: str,
    ) -> None:
        placed = [self._placed_to_mm(p) for p in layout_data.get("placed", [])]

        doc = ezdxf.new(setup=True)
        doc.units = units.MM
        msp = doc.modelspace()

        ensure_layers(doc)
        ensure_linetypes(doc)

        if placed:
            min_x = min(p["x"] for p in placed)
            min_y = min(p["y"] for p in placed)
            max_x = max(p["x"] + p["w"] for p in placed)
            max_y = max(p["y"] + p["h"] for p in placed)
            pad = 7000
            x1 = min_x - pad
            y1 = min_y - pad
            x2 = max_x + pad
            y2 = max_y + pad
            draw_ground_bounds(msp, x1, y1, x2, y2)
        else:
            draw_ground(doc, msp, 40000, 30000)

        for machine in placed:
            draw_machine_symbol_vector(msp, doc, machine)
            draw_small_labels(msp, machine)

        centers = {
            p["uid"]: (p["x"] + p["w"] / 2.0, p["y"] + p["h"] / 2.0)
            for p in placed
        }
        for (src, dst), path in paths.items():
            pts = [self._node_to_mm(n) for n in path]
            if src in centers and dst in centers:
                pts = [centers[src]] + pts + [centers[dst]] if pts else [centers[src], centers[dst]]
            if len(pts) >= 2:
                draw_double_flow(msp, pts)

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        doc.saveas(output_path)
        info(f"DXF saved: {output_path}")

    # =========================
    # Helpers
    # =========================
    def _resolve_image_path(self, placed: Dict[str, object], images_map: Optional[Dict[str, str]]) -> Optional[str]:
        uid = placed.get("uid")
        if images_map and uid in images_map:
            return images_map[uid]
        img_path = placed.get("img_path")
        if isinstance(img_path, str):
            base, _ = os.path.splitext(img_path)
            nobg = f"{base}_nobg.png"
            if os.path.exists(nobg):
                return nobg
            return img_path
        machine = placed.get("machine", {})
        if isinstance(machine, dict):
            return machine.get("image_nobg_path") or machine.get("image_path") or machine.get("image")
        return None

    def _rect_bounds(self, x, y, w, h):
        return (x, y, x + w, y + h)

    def _compute_bounds_rects(self, rects):
        if not rects:
            return 0, 0, 1, 1
        minx = min(r[0] for r in rects)
        miny = min(r[1] for r in rects)
        maxx = max(r[2] for r in rects)
        maxy = max(r[3] for r in rects)
        return minx, miny, maxx, maxy


# =========================
# PNG helpers
# =========================
def trim_whitespace(im: Image.Image) -> Image.Image:
    """Crop white or transparent borders from an image."""
    try:
        if im.mode in ("RGBA", "LA"):
            bg = Image.new(im.mode, im.size, (255, 255, 255, 0))
            diff = ImageChops.difference(im, bg)
            bbox = diff.getbbox()
            if bbox:
                return im.crop(bbox)

        bg = Image.new(im.mode, im.size, im.getpixel((0, 0)))
        diff = ImageChops.difference(im, bg)
        diff = ImageChops.add(diff, diff, 2.0, -100)
        bbox = diff.getbbox()
        if bbox:
            return im.crop(bbox)
        return im
    except Exception:
        return im


def _draw_conveyor_belt(ax, pts: List[Tuple[float, float]], width_mm: float) -> None:
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]

    ax.plot(xs, ys, color=BELT_COLOR_MAIN, linewidth=width_mm / 40, solid_capstyle="round", zorder=5)
    ax.plot(xs, ys, color=BELT_COLOR_EDGE, linewidth=max(2, width_mm / 160), solid_capstyle="round", zorder=6)

    step = 3000.0
    for i in range(len(pts) - 1):
        x1, y1 = pts[i]
        x2, y2 = pts[i + 1]
        seg_len = math.hypot(x2 - x1, y2 - y1)
        if seg_len < 1:
            continue
        n = max(1, int(seg_len // step))
        for k in range(1, n + 1):
            t = (k * step) / seg_len
            if t >= 1:
                continue
            x = x1 + (x2 - x1) * t
            y = y1 + (y2 - y1) * t
            ax.add_patch(
                patches.Circle(
                    (x, y),
                    radius=width_mm / 140,
                    facecolor="white",
                    edgecolor=BELT_COLOR_EDGE,
                    linewidth=1,
                    zorder=7,
                )
            )


# =========================
# DXF helpers
# =========================
def ensure_layers(doc):
    layers = [
        ("WALL_OUT", 8),   # lighter grey for background plan
        ("WALL_IN", 8),
        ("WALL_HATCH", 8),
        ("PILLARS", 8),
        ("DOORS", 8),
        ("GRID", 8),
        ("DIMS", 8),
        ("TEXT", DXF_BLACK),
        ("LEGEND", DXF_BLACK),
        ("MACHINES", DXF_BLUE),
        ("DETAILS", DXF_BLUE),
        ("FLOW", DXF_BLUE),
        ("IMAGES", DXF_BLUE),
        ("GROUPS", 6),
    ]
    for lname, color in layers:
        if lname not in doc.layers:
            doc.layers.new(lname, dxfattribs={"color": color})


def ensure_linetypes(doc):
    if "DASHED" not in doc.linetypes:
        doc.linetypes.new("DASHED", dxfattribs={"description": "Dashed", "pattern": [0.8, 0.4, -0.4]})
    if "CENTER" not in doc.linetypes:
        doc.linetypes.new(
            "CENTER",
            dxfattribs={"description": "Center", "pattern": [1.0, 0.6, -0.2, 0.2, -0.2]},
        )


def draw_lwpoly(msp, pts, layer, closed=False, width=0, linetype=None):
    dxf = {"layer": layer, "closed": closed}
    if width and width > 0:
        dxf["const_width"] = width
    if linetype:
        dxf["linetype"] = linetype
    msp.add_lwpolyline(pts, dxfattribs=dxf)


def draw_rect(msp, x, y, w, h, layer, linetype=None):
    pts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]
    draw_lwpoly(msp, pts, layer, closed=True, width=0, linetype=linetype)


def draw_pillar(msp, cx, cy, size=PILLAR_SIZE_MM):
    half = size / 2
    draw_rect(msp, cx - half, cy - half, size, size, layer="PILLARS")


def draw_wall_hatch(msp, outer: Tuple[float, float, float, float], inner: Tuple[float, float, float, float], step=WALL_HATCH_STEP):
    ox1, oy1, ox2, oy2 = outer
    ix1, iy1, ix2, iy2 = inner

    yb1, yb2 = oy1, iy1
    x = ox1
    while x < ox2:
        msp.add_line((x, yb1), (x + step * 0.6, yb2), dxfattribs={"layer": "WALL_HATCH"})
        x += step

    yt1, yt2 = iy2, oy2
    x = ox1
    while x < ox2:
        msp.add_line((x, yt1), (x + step * 0.6, yt2), dxfattribs={"layer": "WALL_HATCH"})
        x += step

    xl1, xl2 = ox1, ix1
    y = oy1
    while y < oy2:
        msp.add_line((xl1, y), (xl2, y + step * 0.6), dxfattribs={"layer": "WALL_HATCH"})
        y += step

    xr1, xr2 = ix2, ox2
    y = oy1
    while y < oy2:
        msp.add_line((xr1, y), (xr2, y + step * 0.6), dxfattribs={"layer": "WALL_HATCH"})
        y += step


def draw_outer_walls_arch(msp, x1, y1, x2, y2):
    t = WALL_THICK_MM

    draw_pillar(msp, x1, y1)
    draw_pillar(msp, x2, y1)
    draw_pillar(msp, x2, y2)
    draw_pillar(msp, x1, y2)

    cx = (x1 + x2) / 2.0
    dL = cx - DOOR_WIDTH_MM / 2
    dR = cx + DOOR_WIDTH_MM / 2

    msp.add_line((x1, y1), (dL, y1), dxfattribs={"layer": "WALL_OUT"})
    msp.add_line((dR, y1), (x2, y1), dxfattribs={"layer": "WALL_OUT"})
    msp.add_line((x2, y1), (x2, y2), dxfattribs={"layer": "WALL_OUT"})
    msp.add_line((x2, y2), (x1, y2), dxfattribs={"layer": "WALL_OUT"})
    msp.add_line((x1, y2), (x1, y1), dxfattribs={"layer": "WALL_OUT"})

    ix1, iy1, ix2, iy2 = x1 + t, y1 + t, x2 - t, y2 - t
    inner_y = iy1

    msp.add_line((ix1, inner_y), (dL, inner_y), dxfattribs={"layer": "WALL_IN"})
    msp.add_line((dR, inner_y), (ix2, inner_y), dxfattribs={"layer": "WALL_IN"})
    msp.add_line((ix2, iy1), (ix2, iy2), dxfattribs={"layer": "WALL_IN"})
    msp.add_line((ix2, iy2), (ix1, iy2), dxfattribs={"layer": "WALL_IN"})
    msp.add_line((ix1, iy2), (ix1, iy1), dxfattribs={"layer": "WALL_IN"})

    draw_wall_hatch(msp, (x1, y1, x2, y2), (ix1, iy1, ix2, iy2), step=WALL_HATCH_STEP)

    hingeL = (dL, y1)
    hingeR = (dR, y1)
    leaf = DOOR_WIDTH_MM / 2

    msp.add_line(hingeL, (dL + leaf * 0.85, y1 - DOOR_DEPTH_MM), dxfattribs={"layer": "DOORS"})
    msp.add_line(hingeR, (dR - leaf * 0.85, y1 - DOOR_DEPTH_MM), dxfattribs={"layer": "DOORS"})

    msp.add_arc(center=hingeL, radius=leaf * 0.9, start_angle=270, end_angle=360, dxfattribs={"layer": "DOORS"})
    msp.add_arc(center=hingeR, radius=leaf * 0.9, start_angle=180, end_angle=270, dxfattribs={"layer": "DOORS"})


def draw_machine_symbol_vector(msp, doc, p: Dict[str, object]):
    draw_rect(msp, p["x"], p["y"], p["w"], p["h"], layer="MACHINES")

    cp_w = max(320, int(p["w"] * 0.12))
    cp_h = max(220, int(p["h"] * 0.18))
    draw_rect(msp, p["x"] + p["w"] - cp_w - 140, p["y"] + 140, cp_w, cp_h, layer="DETAILS")

    r = 130
    msp.add_circle((p["x"] + 260, p["y"] + 280), r, dxfattribs={"layer": "DETAILS"})
    msp.add_circle((p["x"] + 560, p["y"] + 280), r, dxfattribs={"layer": "DETAILS"})

    if EMBED_IMAGES_IN_CAD and p.get("img_path") and os.path.exists(p["img_path"]):
        try:
            im = Image.open(p["img_path"])
            im = ImageOps.exif_transpose(im)
            px_w, px_h = im.size
            s = min(p["w"] / px_w, p["h"] / px_h)
            iw, ih = px_w * s, px_h * s
            ix = p["x"] + (p["w"] - iw) / 2.0
            iy = p["y"] + (p["h"] - ih) / 2.0
            imgdef = doc.add_image_def(filename=p["img_path"], size_in_pixel=(px_w, px_h))
            msp.add_image(imgdef, insert=(ix, iy), size_in_units=(iw, ih), dxfattribs={"layer": "IMAGES"})
        except Exception:
            pass


def draw_small_labels(msp, p: Dict[str, object]):
    machine = p.get("machine", {}) if isinstance(p.get("machine"), dict) else {}
    name = str(machine.get("name") or "")
    model = str(machine.get("model") or p.get("uid") or "")

    x = p["x"] + 150
    y = p["y"] - 350
    msp.add_text(name, dxfattribs={"layer": "TEXT", "height": TEXT_H_MM}).set_placement((x, y))
    msp.add_text(model, dxfattribs={"layer": "TEXT", "height": TEXT_H_MM}).set_placement((x, y - TEXT_H_MM * 1.4))


def draw_double_flow(msp, pts: List[Tuple[float, float]]):
    up = [(x, y + PIPE_GAP_MM) for x, y in pts]
    dn = [(x, y - PIPE_GAP_MM) for x, y in pts]
    draw_lwpoly(msp, up, layer="FLOW", width=PIPE_LINE_WIDTH_MM)
    draw_lwpoly(msp, dn, layer="FLOW", width=PIPE_LINE_WIDTH_MM)


def draw_grid_bubbles(msp, x1, y1, x2, y2):
    width = x2 - x1
    height = y2 - y1
    nx = max(6, int(width // 14000) + 5)
    ny = max(5, int(height // 12000) + 4)

    xs = [x1 + i * (width / (nx - 1)) for i in range(nx)]
    ys = [y1 + j * (height / (ny - 1)) for j in range(ny)]

    for x in xs:
        draw_lwpoly(msp, [(x, y1), (x, y2)], layer="GRID", linetype="CENTER")
    for y in ys:
        draw_lwpoly(msp, [(x1, y), (x2, y)], layer="GRID", linetype="CENTER")

    bubble_r = 420
    top_y = y2 + 1400
    for i, x in enumerate(xs, start=1):
        msp.add_circle((x, top_y), bubble_r, dxfattribs={"layer": "GRID"})
        msp.add_text(str(i), dxfattribs={"layer": "GRID", "height": 260}).set_placement((x - 120, top_y - 160))
        msp.add_line((x, top_y - bubble_r), (x, y2), dxfattribs={"layer": "GRID"})

    left_x = x1 - 1800
    for j, y in enumerate(ys):
        letter = chr(ord("A") + j)
        msp.add_circle((left_x, y), bubble_r, dxfattribs={"layer": "GRID"})
        msp.add_text(letter, dxfattribs={"layer": "GRID", "height": 260}).set_placement((left_x - 120, y - 160))
        msp.add_line((left_x + bubble_r, y), (x1, y), dxfattribs={"layer": "GRID"})


def draw_overall_dims(msp, x1, y1, x2, y2):
    off = 3200
    y = y2 + off
    msp.add_line((x1, y), (x2, y), dxfattribs={"layer": "DIMS"})
    msp.add_line((x1, y - 260), (x1, y + 260), dxfattribs={"layer": "DIMS"})
    msp.add_line((x2, y - 260), (x2, y + 260), dxfattribs={"layer": "DIMS"})
    msp.add_text(f"{int(x2 - x1)} mm", dxfattribs={"layer": "DIMS", "height": 240}).set_placement(((x1 + x2) / 2 - 900, y + 420))

    x = x1 - off
    msp.add_line((x, y1), (x, y2), dxfattribs={"layer": "DIMS"})
    msp.add_line((x - 260, y1), (x + 260, y1), dxfattribs={"layer": "DIMS"})
    msp.add_line((x - 260, y2), (x + 260, y2), dxfattribs={"layer": "DIMS"})
    msp.add_text(f"{int(y2 - y1)} mm", dxfattribs={"layer": "DIMS", "height": 240}).set_placement((x - 1500, (y1 + y2) / 2))


def draw_ground(doc, msp, width_mm: int = 40000, height_mm: int = 30000):
    ensure_layers(doc)
    ensure_linetypes(doc)

    half_w = width_mm / 2.0
    half_h = height_mm / 2.0
    boundary_pad = 7000

    x1 = -half_w - boundary_pad
    y1 = -half_h - boundary_pad
    x2 = half_w + boundary_pad
    y2 = half_h + boundary_pad

    draw_outer_walls_arch(msp, x1, y1, x2, y2)
    draw_grid_bubbles(msp, x1, y1, x2, y2)
    draw_overall_dims(msp, x1, y1, x2, y2)


def draw_ground_bounds(msp, x1: float, y1: float, x2: float, y2: float):
    """Draw walls/grid/dims using explicit bounds (no centering)."""
    draw_outer_walls_arch(msp, x1, y1, x2, y2)
    draw_grid_bubbles(msp, x1, y1, x2, y2)
    draw_overall_dims(msp, x1, y1, x2, y2)
