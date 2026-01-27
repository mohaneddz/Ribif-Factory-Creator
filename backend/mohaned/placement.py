"""
Machine placement logic with greedy heuristic.
"""

import os
import math
import random
from typing import List, Tuple, Dict, Set, Optional

from models import Machine, Placed
from grid import OccupancyGrid
from io_utils import download_image_to_png
from config import (
    CELL_MM, INPUT_DIMENSIONS_IN_METERS, MIN_FOOTPRINT, MAX_FOOTPRINT,
    KEEP_OUT, CANDIDATES_PER_MACHINE, BBOX_AREA_W, FLOW_LEN_W
)


def dim_to_mm(v: float) -> float:
    """Convert dimension to mm based on input unit setting."""
    return v * 1000.0 if INPUT_DIMENSIONS_IN_METERS else v


def quantize_footprint(m: Machine) -> Tuple[int, int]:
    """Convert machine dimensions to grid cells."""
    w_mm = dim_to_mm(m.width)
    h_mm = dim_to_mm(m.height)
    cw = max(MIN_FOOTPRINT, min(MAX_FOOTPRINT, int(round(w_mm / CELL_MM))))
    ch = max(MIN_FOOTPRINT, min(MAX_FOOTPRINT, int(round(h_mm / CELL_MM))))
    return cw, ch


def expand_machines(machines: List[Machine]) -> List[Tuple[Machine, str]]:
    """Expand machines with count > 1 into individual instances."""
    out: List[Tuple[Machine, str]] = []
    for m in machines:
        if m.count <= 1:
            out.append((m, m.model))
        else:
            for i in range(m.count):
                out.append((m, f"{m.model}_{i+1}"))
    return out


def build_graph(flows: List[Tuple[str, str]]) -> Dict[str, Set[str]]:
    """Build adjacency graph from flows."""
    g: Dict[str, Set[str]] = {}
    for a, b in flows:
        g.setdefault(a, set()).add(b)
        g.setdefault(b, set()).add(a)
    return g


def bbox_of(placed: List[Placed]) -> Tuple[int,int,int,int]:
    """Calculate bounding box of placed machines."""
    if not placed:
        return (0,0,0,0)
    minx = min(p.x for p in placed)
    miny = min(p.y for p in placed)
    maxx = max(p.x + p.w for p in placed)
    maxy = max(p.y + p.h for p in placed)
    return (minx, miny, maxx, maxy)


def bbox_area(placed: List[Placed]) -> int:
    """Calculate bounding box area."""
    minx, miny, maxx, maxy = bbox_of(placed)
    return max(0, (maxx - minx) * (maxy - miny))


def estimate_flow_cost(placed_by_id: Dict[str, Placed], uid: str, cand: Placed, flows: List[Tuple[str,str]]) -> float:
    """Estimate flow cost for a candidate placement."""
    cost = 0.0
    cx, cy = cand.center()
    for a, b in flows:
        if a == uid and b in placed_by_id:
            px, py = placed_by_id[b].center()
            cost += abs(cx - px) + abs(cy - py)
        elif b == uid and a in placed_by_id:
            px, py = placed_by_id[a].center()
            cost += abs(cx - px) + abs(cy - py)
    return cost


def candidate_positions(grid: OccupancyGrid, w: int, h: int, k: int, rng: random.Random, budget: int) -> List[Tuple[int,int]]:
    """Generate candidate positions for machine placement."""
    n = grid.n
    cands: List[Tuple[int,int]] = []

    # 1) biased random samples
    tries = max(30, budget // 2)
    for _ in range(tries):
        x = rng.randint(0, max(0, n - w))
        y = rng.randint(0, max(0, n - h))
        if grid.rect_free(x - k, y - k, w + 2*k, h + 2*k):
            cands.append((x,y))
            if len(cands) >= budget:
                return cands

    # 2) scan a coarse grid
    step = max(1, int(math.sqrt(n)))
    for y in range(0, n - h + 1, max(1, step // 2)):
        for x in range(0, n - w + 1, max(1, step // 2)):
            if grid.rect_free(x - k, y - k, w + 2*k, h + 2*k):
                cands.append((x,y))
                if len(cands) >= budget:
                    return cands

    return cands


def place_all(
    expanded: List[Tuple[Machine,str]],
    flows: List[Tuple[str,str]],
    n: int,
    seed: int = 7,
) -> Tuple[OccupancyGrid, List[Placed]]:
    """Greedy placement of all machines."""
    rng = random.Random(seed)
    grid = OccupancyGrid(n)

    g = build_graph(flows)

    # order machines: area desc then degree desc
    tmp = []
    for m, uid in expanded:
        w, h = quantize_footprint(m)
        deg = len(g.get(uid, set()))
        tmp.append((w*h, deg, m, uid))
    tmp.sort(key=lambda t: (t[0], t[1]), reverse=True)

    placed: List[Placed] = []
    placed_by_id: Dict[str, Placed] = {}

    for _, _, m, uid in tmp:
        base_w, base_h = quantize_footprint(m)
        # allow rotation (swap)
        variants = [(base_w, base_h, 0)]
        if base_w != base_h:
            variants.append((base_h, base_w, 1))

        best: Optional[Placed] = None
        best_score = 1e18

        for vw, vh, rot in variants:
            cands = candidate_positions(grid, vw, vh, KEEP_OUT, rng, CANDIDATES_PER_MACHINE)
            for (x, y) in cands:
                # Prefer nobg version if it exists
                img_path = download_image_to_png(m.image)
                if img_path:
                    nobg_path = img_path.replace(".png", "_nobg.png")
                    if os.path.exists(nobg_path):
                        img_path = nobg_path
                
                cand = Placed(m=m, uid=uid, x=x, y=y, w=vw, h=vh, rot=rot, img_path=img_path)
                # score
                flow_est = estimate_flow_cost(placed_by_id, uid, cand, flows)
                test_list = placed + [cand]
                bb = bbox_area(test_list)
                score = FLOW_LEN_W * flow_est + BBOX_AREA_W * bb * 0.05
                if score < best_score:
                    if grid.rect_free(x - KEEP_OUT, y - KEEP_OUT, vw + 2*KEEP_OUT, vh + 2*KEEP_OUT):
                        best_score = score
                        best = cand

        if best is None:
            raise RuntimeError(f"Failed to place machine {uid}. Increase N or reduce footprints/keepout.")

        ok = grid.place_machine(best)
        if not ok:
            raise RuntimeError(f"Internal placement error for {uid}.")

        placed.append(best)
        placed_by_id[uid] = best

    return grid, placed


def compute_grid_size(expanded: List[Tuple[Machine,str]]) -> int:
    """Compute required grid size based on machine footprints."""
    total = 0
    for m, _ in expanded:
        w, h = quantize_footprint(m)
        total += (w + 2*KEEP_OUT) * (h + 2*KEEP_OUT)
    # fill factor provides room for belts and less holes
    fill_factor = 1.9
    n = int(math.ceil(math.sqrt(total * fill_factor)))
    # pad
    n = max(n, 12)
    return n
