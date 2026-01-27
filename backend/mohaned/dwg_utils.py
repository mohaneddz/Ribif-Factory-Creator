"""
DXF/DWG utility functions for drawing CAD elements
"""

import os
from dataclasses import dataclass
from typing import List, Tuple, Optional
from PIL import Image, ImageOps
import ezdxf
from ezdxf import units

from constants import (
    DXF_BLACK, DXF_BLUE, WALL_THICK_MM, WALL_HATCH_STEP, PILLAR_SIZE_MM,
    DOOR_WIDTH_MM, DOOR_DEPTH_MM, PIPE_GAP_MM, PIPE_LINE_WIDTH_MM,
    TEXT_H_MM, LEGEND_TEXT_H_MM, GRID_MM, AISLE_MM, EMBED_IMAGES_IN_CAD
)
from data import Machine

@dataclass
class PlacedMachine:
    m: Machine
    x: int
    y: int
    w: int
    h: int
    img_path: Optional[str]

@dataclass
class Room:
    name: str
    x: int
    y: int
    w: int
    h: int
    machines: List[PlacedMachine]


def ensure_layers(doc):
    """Create all necessary layers for the DXF document"""
    layers = [
        ("WALL_OUT", DXF_BLACK),
        ("WALL_IN",  DXF_BLACK),
        ("WALL_HATCH", DXF_BLUE),
        ("PILLARS", DXF_BLACK),
        ("DOORS", DXF_BLACK),
        ("GRID", DXF_BLACK),
        ("DIMS", DXF_BLACK),
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
    """Create custom linetypes for the DXF document"""
    if "DASHED" not in doc.linetypes:
        doc.linetypes.new("DASHED", dxfattribs={"description":"Dashed", "pattern":[0.8, 0.4, -0.4]})
    if "CENTER" not in doc.linetypes:
        doc.linetypes.new("CENTER", dxfattribs={"description":"Center", "pattern":[1.0, 0.6, -0.2, 0.2, -0.2]})


def draw_lwpoly(msp, pts, layer, closed=False, width=0, linetype=None):
    """Draw a lightweight polyline"""
    dxf = {"layer": layer, "closed": closed}
    if width and width > 0:
        dxf["const_width"] = width
    if linetype:
        dxf["linetype"] = linetype
    msp.add_lwpolyline(pts, dxfattribs=dxf)


def draw_rect(msp, x, y, w, h, layer, linetype=None):
    """Draw a rectangle"""
    pts = [(x,y),(x+w,y),(x+w,y+h),(x,y+h),(x,y)]
    draw_lwpoly(msp, pts, layer, closed=True, width=0, linetype=linetype)


def draw_pillar(msp, cx, cy, size=PILLAR_SIZE_MM):
    """Draw a pillar at the specified center point"""
    half = size/2
    draw_rect(msp, cx-half, cy-half, size, size, layer="PILLARS")


def draw_wall_hatch(msp, outer: Tuple[float,float,float,float], inner: Tuple[float,float,float,float], step=WALL_HATCH_STEP):
    """
    Simple hatch approximation between outer and inner rectangles using diagonal short segments (blue).
    This keeps it professional-ish while staying DXF-simple.
    """
    ox1, oy1, ox2, oy2 = outer
    ix1, iy1, ix2, iy2 = inner

    # draw diagonal strokes along the band (top, bottom, left, right)
    # bottom band
    yb1, yb2 = oy1, iy1
    x = ox1
    while x < ox2:
        msp.add_line((x, yb1), (x+step*0.6, yb2), dxfattribs={"layer":"WALL_HATCH"})
        x += step

    # top band
    yt1, yt2 = iy2, oy2
    x = ox1
    while x < ox2:
        msp.add_line((x, yt1), (x+step*0.6, yt2), dxfattribs={"layer":"WALL_HATCH"})
        x += step

    # left band
    xl1, xl2 = ox1, ix1
    y = oy1
    while y < oy2:
        msp.add_line((xl1, y), (xl2, y+step*0.6), dxfattribs={"layer":"WALL_HATCH"})
        y += step

    # right band
    xr1, xr2 = ix2, ox2
    y = oy1
    while y < oy2:
        msp.add_line((xr1, y), (xr2, y+step*0.6), dxfattribs={"layer":"WALL_HATCH"})
        y += step


def draw_outer_walls_arch(msp, x1, y1, x2, y2):
    """
    Proper architectural walls:
    - outer rectangle line
    - inner offset rectangle line (wall thickness)
    - entrance gap on BOTH outer and inner bottom edges
    - door leaves + arcs opening outward
    - 4 pillars on corners
    """
    t = WALL_THICK_MM

    # Pillars at corners
    draw_pillar(msp, x1, y1)
    draw_pillar(msp, x2, y1)
    draw_pillar(msp, x2, y2)
    draw_pillar(msp, x1, y2)

    # Door gap centered on bottom
    cx = (x1 + x2) / 2.0
    dL = cx - DOOR_WIDTH_MM/2
    dR = cx + DOOR_WIDTH_MM/2

    # Outer wall: draw as lines (not thick strokes)
    # bottom split
    msp.add_line((x1, y1), (dL, y1), dxfattribs={"layer":"WALL_OUT"})
    msp.add_line((dR, y1), (x2, y1), dxfattribs={"layer":"WALL_OUT"})
    # right/top/left full
    msp.add_line((x2, y1), (x2, y2), dxfattribs={"layer":"WALL_OUT"})
    msp.add_line((x2, y2), (x1, y2), dxfattribs={"layer":"WALL_OUT"})
    msp.add_line((x1, y2), (x1, y1), dxfattribs={"layer":"WALL_OUT"})

    # Inner wall rectangle offset
    ix1, iy1, ix2, iy2 = x1+t, y1+t, x2-t, y2-t
    # inner door gap (shifted up by thickness)
    idL = dL
    idR = dR
    inner_y = iy1

    # inner bottom split
    msp.add_line((ix1, inner_y), (idL, inner_y), dxfattribs={"layer":"WALL_IN"})
    msp.add_line((idR, inner_y), (ix2, inner_y), dxfattribs={"layer":"WALL_IN"})
    # inner right/top/left
    msp.add_line((ix2, iy1), (ix2, iy2), dxfattribs={"layer":"WALL_IN"})
    msp.add_line((ix2, iy2), (ix1, iy2), dxfattribs={"layer":"WALL_IN"})
    msp.add_line((ix1, iy2), (ix1, iy1), dxfattribs={"layer":"WALL_IN"})

    # Hatch between outer and inner
    draw_wall_hatch(msp, (x1,y1,x2,y2), (ix1,iy1,ix2,iy2), step=WALL_HATCH_STEP)

    # Door: double leaf opening outward (below outer wall)
    hingeL = (dL, y1)
    hingeR = (dR, y1)
    leaf = DOOR_WIDTH_MM/2

    # leaf lines outward (down)
    msp.add_line(hingeL, (dL + leaf*0.85, y1 - DOOR_DEPTH_MM), dxfattribs={"layer":"DOORS"})
    msp.add_line(hingeR, (dR - leaf*0.85, y1 - DOOR_DEPTH_MM), dxfattribs={"layer":"DOORS"})

    # swing arcs outward
    msp.add_arc(center=hingeL, radius=leaf*0.9, start_angle=270, end_angle=360, dxfattribs={"layer":"DOORS"})
    msp.add_arc(center=hingeR, radius=leaf*0.9, start_angle=180, end_angle=270, dxfattribs={"layer":"DOORS"})


def draw_room_partition_walls(msp, r: Room):
    """
    Interior partitions: use double-lines (outer+inner) lightly, no hatch.
    Keeps it clean & "real".
    """
    t = int(WALL_THICK_MM * 0.65)
    x1, y1, x2, y2 = r.x, r.y, r.x+r.w, r.y+r.h
    ix1, iy1, ix2, iy2 = x1+t, y1+t, x2-t, y2-t

    draw_rect(msp, x1, y1, x2-x1, y2-y1, layer="GROUPS")
    draw_rect(msp, ix1, iy1, ix2-ix1, iy2-iy1, layer="GROUPS", linetype="DASHED")


def draw_machine_symbol_vector(msp, doc, p: PlacedMachine):
    """Draw machine symbol with vector graphics"""
    # Footprint outline (blue)
    draw_rect(msp, p.x, p.y, p.w, p.h, layer="MACHINES")

    # Details (blue): control panel + barrels (gives top-view feel)
    cp_w = max(320, int(p.w*0.12))
    cp_h = max(220, int(p.h*0.18))
    draw_rect(msp, p.x + p.w - cp_w - 140, p.y + 140, cp_w, cp_h, layer="DETAILS")

    r = 130
    msp.add_circle((p.x + 260, p.y + 280), r, dxfattribs={"layer":"DETAILS"})
    msp.add_circle((p.x + 560, p.y + 280), r, dxfattribs={"layer":"DETAILS"})

    # Optional photo embedding layer (OFF by default)
    if EMBED_IMAGES_IN_CAD and p.img_path and os.path.exists(p.img_path):
        try:
            im = Image.open(p.img_path)
            im = ImageOps.exif_transpose(im)
            px_w, px_h = im.size
            s = min(p.w/px_w, p.h/px_h)
            iw, ih = px_w*s, px_h*s
            ix = p.x + (p.w - iw)/2.0
            iy = p.y + (p.h - ih)/2.0
            imgdef = doc.add_image_def(filename=p.img_path, size_in_pixel=(px_w, px_h))
            msp.add_image(imgdef, insert=(ix, iy), size_in_units=(iw, ih), dxfattribs={"layer":"IMAGES"})
        except Exception:
            pass


def draw_small_labels(msp, p: PlacedMachine):
    """Draw small labels under machine: name + model (black)"""
    x = p.x + 150
    y = p.y - 350
    msp.add_text(p.m.name, dxfattribs={"layer":"TEXT", "height": TEXT_H_MM}).set_placement((x, y))
    msp.add_text(p.m.model, dxfattribs={"layer":"TEXT", "height": TEXT_H_MM}).set_placement((x, y - TEXT_H_MM*1.4))


def draw_double_flow(msp, pts: List[Tuple[float,float]]):
    """Draw double-line conveyor / pipe (blue)"""
    up = [(x, y+PIPE_GAP_MM) for x,y in pts]
    dn = [(x, y-PIPE_GAP_MM) for x,y in pts]
    draw_lwpoly(msp, up, layer="FLOW", width=PIPE_LINE_WIDTH_MM)
    draw_lwpoly(msp, dn, layer="FLOW", width=PIPE_LINE_WIDTH_MM)


def draw_grid_bubbles(msp, x1, y1, x2, y2):
    """Draw grid lines with bubble annotations"""
    width  = x2-x1
    height = y2-y1
    nx = max(6, int(width // 14000) + 5)
    ny = max(5, int(height // 12000) + 4)

    xs = [x1 + i*(width/(nx-1)) for i in range(nx)]
    ys = [y1 + j*(height/(ny-1)) for j in range(ny)]

    for x in xs:
        draw_lwpoly(msp, [(x,y1),(x,y2)], layer="GRID", linetype="CENTER")
    for y in ys:
        draw_lwpoly(msp, [(x1,y),(x2,y)], layer="GRID", linetype="CENTER")

    bubble_r = 420
    top_y = y2 + 1400
    for i, x in enumerate(xs, start=1):
        msp.add_circle((x, top_y), bubble_r, dxfattribs={"layer":"GRID"})
        msp.add_text(str(i), dxfattribs={"layer":"GRID", "height": 260}).set_placement((x-120, top_y-160))
        msp.add_line((x, top_y-bubble_r), (x, y2), dxfattribs={"layer":"GRID"})

    left_x = x1 - 1800
    for j, y in enumerate(ys):
        letter = chr(ord("A")+j)
        msp.add_circle((left_x, y), bubble_r, dxfattribs={"layer":"GRID"})
        msp.add_text(letter, dxfattribs={"layer":"GRID", "height": 260}).set_placement((left_x-120, y-160))
        msp.add_line((left_x+bubble_r, y), (x1, y), dxfattribs={"layer":"GRID"})


def draw_overall_dims(msp, x1, y1, x2, y2):
    """Draw overall dimension annotations"""
    # top width
    off = 3200
    y = y2 + off
    msp.add_line((x1,y), (x2,y), dxfattribs={"layer":"DIMS"})
    msp.add_line((x1,y-260), (x1,y+260), dxfattribs={"layer":"DIMS"})
    msp.add_line((x2,y-260), (x2,y+260), dxfattribs={"layer":"DIMS"})
    msp.add_text(f"{int(x2-x1)} mm", dxfattribs={"layer":"DIMS", "height": 240}).set_placement(((x1+x2)/2 - 900, y+420))

    # left height
    x = x1 - off
    msp.add_line((x,y1), (x,y2), dxfattribs={"layer":"DIMS"})
    msp.add_line((x-260,y1), (x+260,y1), dxfattribs={"layer":"DIMS"})
    msp.add_line((x-260,y2), (x+260,y2), dxfattribs={"layer":"DIMS"})
    msp.add_text(f"{int(y2-y1)} mm", dxfattribs={"layer":"DIMS", "height": 240}).set_placement((x-1500, (y1+y2)/2))


def draw_legend(msp, x, y):
    """Draw legend with layer information"""
    msp.add_text("LEGEND", dxfattribs={"layer":"LEGEND", "height": 320}).set_placement((x, y))
    y -= 520
    lines = [
        "Black: walls / door / grid / dims / text",
        "Blue : machines / flow / hatch",
        f"Units: mm | Grid: {GRID_MM} | Aisle: {AISLE_MM}",
        "Walls: double-line + hatch",
    ]
    for line in lines:
        msp.add_text(line, dxfattribs={"layer":"LEGEND", "height": LEGEND_TEXT_H_MM}).set_placement((x, y))
        y -= 300


def draw_ground(doc, msp, width_mm: int = 40000, height_mm: int = 30000):
    """
    Draw a blank factory ground plan with walls, grid, dimensions, and legend.
    No machines included - just the basic structure.
    
    Args:
        doc: ezdxf document
        msp: modelspace
        width_mm: Interior width in millimeters
        height_mm: Interior height in millimeters
    """
    # Ensure layers and linetypes exist
    ensure_layers(doc)
    ensure_linetypes(doc)
    
    # Calculate boundaries (centered around origin)
    half_w = width_mm / 2.0
    half_h = height_mm / 2.0
    boundary_pad = 7000
    
    x1 = -half_w - boundary_pad
    y1 = -half_h - boundary_pad
    x2 = half_w + boundary_pad
    y2 = half_h + boundary_pad
    
    # Draw outer walls with door
    draw_outer_walls_arch(msp, x1, y1, x2, y2)
    
    # Draw grid with bubbles
    draw_grid_bubbles(msp, x1, y1, x2, y2)
    
    # Draw overall dimensions
    draw_overall_dims(msp, x1, y1, x2, y2)
    
    # Draw legend
    # draw_legend(msp, x1 + 1200, y2 - 1300)


def export_dxf_as_png(doc, output_path: str, dpi: int = 300):
    """
    Export the DXF document to a PNG image using ezdxf's drawing addon and matplotlib.
    
    Args:
        doc: ezdxf document to export
        output_path: Path to save the PNG file
        dpi: Resolution of the output image
    """
    try:
        import matplotlib.pyplot as plt
        from ezdxf.addons.drawing import RenderContext, Frontend
        from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
        
        # 1. Create a figure
        fig = plt.figure(figsize=(16, 9))
        ax = fig.add_axes([0, 0, 1, 1])
        
        # 2. Setup render context and backend
        ctx = RenderContext(doc)
        out = MatplotlibBackend(ax)
        
        # 3. Draw the modelspace content
        Frontend(ctx, out).draw_layout(doc.modelspace(), finalize=True)
        
        # 4. Finalize and save
        ax.set_aspect('equal')
        ax.axis('off')
        
        fig.savefig(output_path, dpi=dpi, bbox_inches='tight', pad_inches=0.1, facecolor='white')
        plt.close(fig)
        print(f"[+] CAD plot exported to PNG: {output_path}")
        
    except ImportError as e:
        print(f"[!] Warning: Could not export PNG from DXF. Missing dependencies: {e}")
        print("   Try: pip install matplotlib ezdxf")
    except Exception as e:
        print(f"[!] Warning: DXF to PNG export failed: {e}")


def generate_dxf(rooms, flows, find_machine_func, routing_func, out_dxf):
    """
    Generate complete factory DXF with walls, machines, and conveyors.
    
    Args:
        rooms: List[Room] with placed machines
        flows: List of (src_uid, dst_uid) tuples
        find_machine_func: Function to find machine by UID
        routing_func: Function to route between two machines (returns list of (x,y) points)
        out_dxf: Output DXF file path
    """
    # Create new DXF document
    doc = ezdxf.new(setup=True)
    doc.units = units.MM
    msp = doc.modelspace()
    
    # Setup layers and linetypes
    ensure_layers(doc)
    ensure_linetypes(doc)
    
    # Calculate canvas size from rooms
    if not rooms:
        canvas_w, canvas_h = 40000, 30000
    else:
        # Find bounds of all machines
        all_machines = []
        for r in rooms:
            all_machines.extend(r.machines)
        
        if all_machines:
            min_x = min(m.x for m in all_machines)
            min_y = min(m.y for m in all_machines)
            max_x = max(m.x + m.w for m in all_machines)
            max_y = max(m.y + m.h for m in all_machines)
            
            canvas_w = max(40000, int(max_x - min_x + 10000))
            canvas_h = max(30000, int(max_y - min_y + 10000))
        else:
            canvas_w, canvas_h = 40000, 30000
    
    # Draw ground (walls, grid, dimensions)
    draw_ground(doc, msp, canvas_w, canvas_h)
    
    # Draw all machines
    for room in rooms:
        # Draw room partitions if multiple rooms
        if len(rooms) > 1:
            draw_room_partition_walls(msp, room)
        
        # Draw each machine
        for machine in room.machines:
            draw_machine_symbol_vector(msp, doc, machine)
            draw_small_labels(msp, machine)
    
    # Draw flows (conveyors)
    for src_uid, dst_uid in flows:
        src = find_machine_func(rooms, src_uid)
        dst = find_machine_func(rooms, dst_uid)
        
        if src and dst:
            # Get routing waypoints
            pts = routing_func(src, dst)
            if pts and len(pts) >= 2:
                draw_double_flow(msp, pts)
    
    # Save DXF
    os.makedirs(os.path.dirname(out_dxf) or ".", exist_ok=True)
    doc.saveas(out_dxf)
    print(f"[+] DXF saved: {out_dxf}")
