"""
Local optimization with simulated annealing.
"""

import math
import random
from typing import List, Tuple, Dict

from models import Placed
from grid import OccupancyGrid
from routing import EdgeReservation, ripup_reroute, Path
from config import (
    LOCAL_ITERS, LOCAL_MAX_SHIFT, ANNEAL_START_T, ANNEAL_END_T,
    BBOX_AREA_W, HOLE_W, FLOW_LEN_W, CONGESTION_W
)


def total_congestion(res: EdgeReservation) -> int:
    """Calculate total edge congestion."""
    return sum(max(0, u - 1) for u in res.use.values())


def total_flow_len(paths: Dict[Tuple[str,str], Path]) -> int:
    """Calculate total flow path length."""
    return sum(len(p) for p in paths.values())


def layout_score(grid: OccupancyGrid, placed: List[Placed], res: EdgeReservation, paths: Dict[Tuple[str,str], Path]) -> float:
    """Calculate overall layout quality score."""
    from placement import bbox_area
    
    bb = bbox_area(placed)
    holes = grid.hole_metric()
    fl = total_flow_len(paths)
    cong = total_congestion(res)
    return (
        BBOX_AREA_W * bb
        + HOLE_W * holes * 40.0
        + FLOW_LEN_W * fl * 120.0
        + CONGESTION_W * cong * 400.0
    )


def rebuild_grid(n: int, placed: List[Placed]) -> OccupancyGrid:
    """Rebuild occupancy grid from scratch."""
    g = OccupancyGrid(n)
    for p in placed:
        if not g.place_machine(p):
            raise RuntimeError("Rebuild failed (overlap).")
    return g


def local_improve(
    placed: List[Placed],
    flows: List[Tuple[str,str]],
    n: int,
    seed: int = 9
) -> Tuple[List[Placed], EdgeReservation, Dict[Tuple[str,str], Path]]:
    """Local improvement with simulated annealing."""
    rng = random.Random(seed)

    # Make a working copy to mutate
    placed = [Placed(p.m, p.uid, p.x, p.y, p.w, p.h, p.rot, p.img_path) for p in placed]

    grid = rebuild_grid(n, placed)
    res, paths = ripup_reroute(grid, placed, flows)
    best_score = layout_score(grid, placed, res, paths)
    # Deep copy for best
    best = [Placed(p.m, p.uid, p.x, p.y, p.w, p.h, p.rot, p.img_path) for p in placed]
    best_res, best_paths = res, paths

    def temperature(t: int) -> float:
        if LOCAL_ITERS <= 1:
            return ANNEAL_END_T
        alpha = t / (LOCAL_ITERS - 1)
        return ANNEAL_START_T * (1 - alpha) + ANNEAL_END_T * alpha

    for it in range(LOCAL_ITERS):
        T = temperature(it)

        # propose move
        idx = rng.randrange(len(placed))
        p = placed[idx]
        old = Placed(p.m, p.uid, p.x, p.y, p.w, p.h, p.rot, p.img_path)

        # random move or rotate
        if rng.random() < 0.15 and p.w != p.h:
            # rotate
            p.w, p.h = p.h, p.w
            p.rot ^= 1
        else:
            dx = rng.randint(-LOCAL_MAX_SHIFT, LOCAL_MAX_SHIFT)
            dy = rng.randint(-LOCAL_MAX_SHIFT, LOCAL_MAX_SHIFT)
            p.x = max(0, min(n - p.w, p.x + dx))
            p.y = max(0, min(n - p.h, p.y + dy))

        # Quick validation: check if new position would cause overlap
        # Build a temporary grid without this machine to test
        temp_grid = OccupancyGrid(n)
        valid_move = True
        for q in placed:
            if q.uid == p.uid:
                continue
            if not temp_grid.place_machine(q):
                # This shouldn't happen with current placement, but check anyway
                valid_move = False
                break
        
        # Now try to place the moved machine
        if valid_move:
            valid_move = temp_grid.place_machine(p)
        
        if not valid_move:
            # Revert and skip this iteration
            placed[idx] = old
            continue

        # rebuild occupancy with validated placement
        try:
            grid2 = rebuild_grid(n, placed)
            res2, paths2 = ripup_reroute(grid2, placed, flows)
        except RuntimeError:
            # Rebuild failed (shouldn't happen now, but safety check)
            placed[idx] = old
            continue

        # require most flows routed (hard constraint)
        target_count = len([f for f in flows if f[0] in {q.uid for q in placed} and f[1] in {q.uid for q in placed}])
        routed = len(paths2)
        if routed < max(1, int(0.95 * target_count)):
            placed[idx] = old
            continue

        s2 = layout_score(grid2, placed, res2, paths2)
        delta = s2 - best_score

        accept = False
        if s2 <= best_score:
            accept = True
        else:
            # anneal
            prob = math.exp(-delta / max(1e-9, T * 5000.0))
            if rng.random() < prob:
                accept = True

        if accept:
            grid, res, paths = grid2, res2, paths2
            if s2 < best_score:
                best_score = s2
                best = [Placed(q.m, q.uid, q.x, q.y, q.w, q.h, q.rot, q.img_path) for q in placed]
                best_res, best_paths = res2, paths2
        else:
            placed[idx] = old

    return best, best_res, best_paths
