import os
import math
from typing import List, Tuple
from PIL import Image, ImageOps, ImageChops
import matplotlib

matplotlib.use("Agg")  # Use non-GUI backend to avoid threading issues
import matplotlib.pyplot as plt
import matplotlib.patches as patches

from constants import BELT_HALF_WIDTH_MM, BELT_COLOR_MAIN, BELT_COLOR_EDGE, AISLE_MM, PNG_IMAGE_FILL
from dwg_utils import PlacedMachine, Room


def rect_bounds(x, y, w, h):
    """Calculate rectangle bounds"""
    return (x, y, x + w, y + h)

def compute_bounds_rects(rects):
    """Compute overall bounds from a list of rectangles"""
    if not rects:
        return 0, 0, 1, 1
    minx = min(r[0] for r in rects)
    miny = min(r[1] for r in rects)
    maxx = max(r[2] for r in rects)
    maxy = max(r[3] for r in rects)
    return minx, miny, maxx, maxy

def trim_whitespace(im):
    """
    Automatically crops white or transparent borders from an image.
    This ensures the machine occupies the maximum visual space inside its bounding box.
    """
    try:
        # If the image has an alpha channel, use it to find the bounding box
        if im.mode in ('RGBA', 'LA'):
            bg = Image.new(im.mode, im.size, (255, 255, 255, 0))
            diff = ImageChops.difference(im, bg)
            bbox = diff.getbbox()
            if bbox:
                return im.crop(bbox)
        
        # Fallback for RGB/L (or if alpha didn't help): looks for white border
        bg = Image.new(im.mode, im.size, im.getpixel((0,0)))
        diff = ImageChops.difference(im, bg)
        diff = ImageChops.add(diff, diff, 2.0, -100)
        bbox = diff.getbbox()
        if bbox:
            return im.crop(bbox)
            
        return im
    except Exception:
        # If trimming fails, return original
        return im

def _draw_conveyor_belt(ax, pts: List[Tuple[float, float]], width_mm: float):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]

    # Main thick belt
    ax.plot(xs, ys, color=BELT_COLOR_MAIN, linewidth=width_mm / 40, solid_capstyle="round", zorder=5)
    # Edge detail
    ax.plot(xs, ys, color=BELT_COLOR_EDGE, linewidth=max(2, width_mm / 160), solid_capstyle="round", zorder=6)

    # Rollers
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

def save_design_plot_png(rooms: List[Room], flows, find_machine_func, routing_func, out_png="design_plot.png", use_processed_images=True):
    """
    Save design plot as PNG:
      - Images are auto-cropped to remove whitespace.
      - Images are scaled to 15% of layout width (unless constrained by neighbors).
      - Respects 'no overlap' constraint by checking nearest neighbors.
      - use_processed_images: If True (default), uses _nobg.png versions if available.
                              If False, uses raw cached images (for AI inference input).
    """
    
    # 1. Collect all machines
    all_machines = []
    for r in rooms:
        for p in r.machines:
            all_machines.append(p)
            
    # Calculate layout bounds (physical)
    phys_rects = [rect_bounds(m.x, m.y, m.w, m.h) for m in all_machines]
    p_minx, p_miny, p_maxx, p_maxy = compute_bounds_rects(phys_rects)
    layout_width = max(1.0, p_maxx - p_minx)
    
    # HEURISTIC: Target Size = 15% of total layout width
    # This is roughly 2x bigger than previous attempts
    IDEAL_IMG_SIZE = max(3000.0, layout_width * 0.15) 
    
    # 2. Determine Image Sizes based on nearest neighbor
    draw_items = []
    visual_rects = [] 

    for i, p in enumerate(all_machines):
        # Calculate distance to nearest neighbor to prevent overlap
        min_dist = float('inf')
        cx = p.x + p.w / 2.0
        cy = p.y + p.h / 2.0
        
        for j, other in enumerate(all_machines):
            if i == j: continue
            ocx = other.x + other.w / 2.0
            ocy = other.y + other.h / 2.0
            dist = math.hypot(cx - ocx, cy - ocy)
            if dist < min_dist:
                min_dist = dist
        
        # Determine allowed size
        # We allow the image to fill 95% of the gap to the nearest neighbor.
        if min_dist == float('inf'):
            allowed_size = IDEAL_IMG_SIZE * 1.5 # Isolated machines can be even bigger
        else:
            allowed_size = min_dist * 0.95
            
        # Target size is the lesser of the Ideal Size (visual consistency) and Allowed Size (geometry constraint)
        # We also enforce a hard floor (e.g. 1000mm) so machines don't vanish even if they are touching.
        target_size = max(1000.0, min(IDEAL_IMG_SIZE, allowed_size))

        if p.img_path and os.path.exists(p.img_path):
            try:
                # Determine which image to use
                img_to_load = p.img_path
                if use_processed_images:
                    # Check if a _nobg.png version exists
                    base, ext = os.path.splitext(p.img_path)
                    nobg_path = f"{base}_nobg.png"
                    if os.path.exists(nobg_path):
                        img_to_load = nobg_path
                
                im = Image.open(img_to_load).convert("RGBA")
                im = ImageOps.exif_transpose(im)
                
                # CRITICAL: Trim whitespace so the "machine" fills the box
                im = trim_whitespace(im)
                
                # Calculate aspect ratio
                iw_px, ih_px = im.size
                aspect = iw_px / ih_px
                
                # Fit into bounding box defined by target_size
                if aspect > 1:
                    draw_w = target_size
                    draw_h = target_size / aspect
                else:
                    draw_h = target_size
                    draw_w = target_size * aspect
                
                # Center image on the machine's center
                draw_x = cx - (draw_w / 2.0)
                draw_y = cy - (draw_h / 2.0)
                
                draw_items.append({
                    "im": im,
                    "extent": [draw_x, draw_x + draw_w, draw_y, draw_y + draw_h],
                    "z": 10
                })
                # Add to bounds so plot zooms out to fit large images
                visual_rects.append((draw_x, draw_y, draw_x + draw_w, draw_y + draw_h))
            except Exception as e:
                print(f"Error loading image {p.img_path}: {e}")
                visual_rects.append((p.x, p.y, p.x + p.w, p.y + p.h))
        else:
            visual_rects.append((p.x, p.y, p.x + p.w, p.y + p.h))

    # --- Setup Plot Bounds ---
    if not visual_rects:
        visual_rects = [rect_bounds(m.x, m.y, m.w, m.h) for m in all_machines]
        
    minx, miny, maxx, maxy = compute_bounds_rects(visual_rects)

    # Add 5% padding
    pad_w = (maxx - minx) * 0.05
    pad_h = (maxy - miny) * 0.05
    minx -= pad_w
    maxx += pad_w
    miny -= pad_h
    maxy += pad_h

    # Enforce 1:1 square aspect ratio
    current_w = maxx - minx
    current_h = maxy - miny
    target_aspect = 1.0  # 1:1 square aspect ratio

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

    # --- Plotting ---
    fig = plt.figure(figsize=(16, 9), dpi=100)
    ax = fig.add_subplot(111)
    ax.set_facecolor("#00FF00")
    fig.patch.set_facecolor("#00FF00")

    # Draw Conveyors
    for src, dst in flows:
        a = find_machine_func(rooms, src)
        b = find_machine_func(rooms, dst)
        if not a or not b:
            continue
        pts = routing_func(a, b)
        _draw_conveyor_belt(ax, pts, width_mm=BELT_HALF_WIDTH_MM * 2)

    # Draw Images
    for item in draw_items:
        ax.imshow(item["im"], extent=item["extent"], zorder=item["z"])

    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    plt.tight_layout(pad=0)
    fig.savefig(out_png, bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    print(f"[+] Saved: {out_png}")