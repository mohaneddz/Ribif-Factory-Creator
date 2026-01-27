"""
Edge-based routing with A* pathfinding (no crossings by construction).
"""

import heapq
from typing import Dict, List, Optional, Tuple, Set

from models import Placed
from grid import OccupancyGrid
from config import (
    EDGE_CAPACITY_DEFAULT, EDGE_CAPACITY_TRUNK, BEND_PENALTY,
    CONGESTION_PENALTY, MAX_ASTAR_ITERS, KEEP_OUT, PORT_OFFSET
)

# Edge keys:
# H edge between (x,y)-(x+1,y): ("H", x, y)
# V edge between (x,y)-(x,y+1): ("V", x, y)

EdgeKey = Tuple[str, int, int]
Node = Tuple[int, int]
Path = List[Node]


class EdgeReservation:
    def __init__(self):
        self.use: Dict[EdgeKey, int] = {}
        self.cap: Dict[EdgeKey, int] = {}

    def capacity(self, e: EdgeKey) -> int:
        return self.cap.get(e, EDGE_CAPACITY_DEFAULT)

    def set_capacity_rect_trunk(self, x1: int, y1: int, x2: int, y2: int) -> None:
        """Mark a trunk corridor rectangle edges with higher capacity to allow merges."""
        for y in range(y1, y2+1):
            for x in range(x1, x2):
                self.cap[("H", x, y)] = EDGE_CAPACITY_TRUNK
        for x in range(x1, x2+1):
            for y in range(y1, y2):
                self.cap[("V", x, y)] = EDGE_CAPACITY_TRUNK

    def can_use(self, e: EdgeKey) -> bool:
        return self.use.get(e, 0) < self.capacity(e)

    def add_path(self, path: Path) -> List[EdgeKey]:
        edges = nodes_to_edges(path)
        for e in edges:
            self.use[e] = self.use.get(e, 0) + 1
        return edges

    def remove_edges(self, edges: List[EdgeKey]) -> None:
        for e in edges:
            if e in self.use:
                self.use[e] -= 1
                if self.use[e] <= 0:
                    del self.use[e]


def nodes_to_edges(path: Path) -> List[EdgeKey]:
    out: List[EdgeKey] = []
    for (x1, y1), (x2, y2) in zip(path, path[1:]):
        if x2 == x1 + 1 and y2 == y1:
            out.append(("H", x1, y1))
        elif x2 == x1 - 1 and y2 == y1:
            out.append(("H", x2, y1))
        elif y2 == y1 + 1 and x2 == x1:
            out.append(("V", x1, y1))
        elif y2 == y1 - 1 and x2 == x1:
            out.append(("V", x1, y2))
        else:
            raise ValueError("Non-grid step in path")
    return out


def edge_between(a: Node, b: Node) -> EdgeKey:
    x1, y1 = a
    x2, y2 = b
    if x2 == x1 + 1 and y2 == y1:
        return ("H", x1, y1)
    if x2 == x1 - 1 and y2 == y1:
        return ("H", x2, y1)
    if y2 == y1 + 1 and x2 == x1:
        return ("V", x1, y1)
    if y2 == y1 - 1 and x2 == x1:
        return ("V", x1, y2)
    raise ValueError("Not adjacent")


def manhattan(a: Node, b: Node) -> int:
    return abs(a[0]-b[0]) + abs(a[1]-b[1])


def astar_route(
    grid: OccupancyGrid,
    res: EdgeReservation,
    start: Node,
    goal: Node,
) -> Optional[Path]:
    """A* on node graph with edge capacity constraints."""
    n_cells = grid.n
    if not (0 <= start[0] < n_cells and 0 <= start[1] < n_cells):
        return None
    if not (0 <= goal[0] < n_cells and 0 <= goal[1] < n_cells):
        return None
    if grid.block[start[1]][start[0]] != 0:
        return None
    if grid.block[goal[1]][goal[0]] != 0:
        return None

    openh = []
    gscore: Dict[Node, float] = {start: 0.0}
    parent: Dict[Node, Node] = {}
    dir_from: Dict[Node, Optional[Tuple[int,int]]] = {start: None}

    heapq.heappush(openh, (manhattan(start, goal), 0.0, start))
    iters = 0

    while openh:
        iters += 1
        if iters > MAX_ASTAR_ITERS:
            return None
        _, gc, cur = heapq.heappop(openh)
        if cur == goal:
            # reconstruct
            path = [cur]
            while cur in parent:
                cur = parent[cur]
                path.append(cur)
            path.reverse()
            return path

        for nb in [(cur[0]+1, cur[1]), (cur[0]-1, cur[1]), (cur[0], cur[1]+1), (cur[0], cur[1]-1)]:
            x, y = nb
            if x < 0 or y < 0 or x >= n_cells or y >= n_cells:
                continue
            if grid.block[y][x] != 0:
                continue

            # edge capacity check
            e = edge_between(cur, nb)
            if not res.can_use(e):
                continue

            # cost: step + bend + congestion
            step = 1.0
            dcur = (nb[0]-cur[0], nb[1]-cur[1])
            dprev = dir_from.get(cur)
            bend = 0.0 if (dprev is None or dprev == dcur) else BEND_PENALTY
            cong = CONGESTION_PENALTY * res.use.get(e, 0)

            ng = gc + step + bend + cong
            if ng < gscore.get(nb, 1e18):
                gscore[nb] = ng
                parent[nb] = cur
                dir_from[nb] = dcur
                f = ng + manhattan(nb, goal)
                heapq.heappush(openh, (f, ng, nb))

    return None


def pick_port(src: Placed, dst: Placed) -> Node:
    """Choose a start cell near src facing dst."""
    sx, sy = src.center()
    dx, dy = dst.center()
    # direction preference
    if abs(dx - sx) > abs(dy - sy):
        # go left/right
        if dx > sx:
            px = min(src.x + src.w + PORT_OFFSET, src.x + src.w - 1)
            py = int(round(src.y + src.h / 2))
            return (min(px, src.x + src.w - 1), min(max(py, src.y), src.y + src.h - 1))
        else:
            px = max(src.x - 1 - PORT_OFFSET, src.x)
            py = int(round(src.y + src.h / 2))
            return (max(px, src.x), min(max(py, src.y), src.y + src.h - 1))
    else:
        # go up/down
        if dy > sy:
            px = int(round(src.x + src.w / 2))
            py = min(src.y + src.h + PORT_OFFSET, src.y + src.h - 1)
            return (min(max(px, src.x), src.x + src.w - 1), min(py, src.y + src.h - 1))
        else:
            px = int(round(src.x + src.w / 2))
            py = max(src.y - 1 - PORT_OFFSET, src.y)
            return (min(max(px, src.x), src.x + src.w - 1), max(py, src.y))


def port_outside_cell(p: Placed, towards: Node, grid: OccupancyGrid) -> Node:
    """Move from inside machine to nearest free cell adjacent to its boundary."""
    cx, cy = p.center()
    tx, ty = towards
    best = None
    bestd = 1e18
    for y in range(max(0, p.y - (KEEP_OUT+2)), min(grid.n, p.y + p.h + (KEEP_OUT+2))):
        for x in range(max(0, p.x - (KEEP_OUT+2)), min(grid.n, p.x + p.w + (KEEP_OUT+2))):
            if grid.block[y][x] == 0:
                d = abs(x - tx) + abs(y - ty) + 0.2*(abs(x - cx) + abs(y - cy))
                if d < bestd:
                    bestd = d
                    best = (x, y)
    return best if best else (int(cx), int(cy))


def route_all_flows(
    grid: OccupancyGrid,
    placed: List[Placed],
    flows: List[Tuple[str,str]],
) -> Tuple[EdgeReservation, Dict[Tuple[str,str], Path], Dict[Tuple[str,str], List[EdgeKey]]]:
    """Route all flows with A*."""
    by_id = {p.uid: p for p in placed}
    res = EdgeReservation()

    # optional: create a central trunk corridor to encourage merges
    n = grid.n
    mid = n // 2
    res.set_capacity_rect_trunk(max(0, mid-2), 0, min(n-1, mid+2), n-1)

    paths: Dict[Tuple[str,str], Path] = {}
    edges_for: Dict[Tuple[str,str], List[EdgeKey]] = {}

    # route in hardest-first: longer estimated dist first
    scored = []
    for a, b in flows:
        if a not in by_id or b not in by_id:
            continue
        da = manhattan((int(by_id[a].center()[0]), int(by_id[a].center()[1])),
                       (int(by_id[b].center()[0]), int(by_id[b].center()[1])))
        scored.append((da, a, b))
    scored.sort(reverse=True)

    for _, a, b in scored:
        pa, pb = by_id[a], by_id[b]
        approx = (int(pb.center()[0]), int(pb.center()[1]))
        sa = port_outside_cell(pa, approx, grid)
        sb = port_outside_cell(pb, (int(pa.center()[0]), int(pa.center()[1])), grid)

        path = astar_route(grid, res, sa, sb)
        if path is None:
            return res, paths, edges_for  # partial
        edges = res.add_path(path)
        paths[(a,b)] = path
        edges_for[(a,b)] = edges

    return res, paths, edges_for


def ripup_reroute(
    grid: OccupancyGrid,
    placed: List[Placed],
    flows: List[Tuple[str,str]],
) -> Tuple[EdgeReservation, Dict[Tuple[str,str], Path]]:
    """Iterative ripup and reroute to handle congestion."""
    from config import RIPUP_PASSES
    
    by_id = {p.uid: p for p in placed}

    # initial attempt
    res, paths, edges_for = route_all_flows(grid, placed, flows)
    if len(paths) == len([f for f in flows if f[0] in by_id and f[1] in by_id]):
        return res, paths

    # iterative ripup
    for _pass in range(RIPUP_PASSES):
        target_flows = [(a,b) for (a,b) in flows if a in by_id and b in by_id]
        if len(paths) == len(target_flows):
            return res, paths

        unrouted = [f for f in target_flows if f not in paths]
        if not unrouted:
            return res, paths

        # rip up longest routes
        routed = list(paths.keys())
        routed.sort(key=lambda k: len(paths[k]), reverse=True)
        k_remove = min(6, max(2, len(routed)//6))
        to_remove = routed[:k_remove]

        for key in to_remove:
            res.remove_edges(edges_for[key])
            del edges_for[key]
            del paths[key]

        # fresh reroute
        fresh = EdgeReservation()
        n = grid.n
        mid = n // 2
        fresh.set_capacity_rect_trunk(max(0, mid-2), 0, min(n-1, mid+2), n-1)

        res = fresh
        paths = {}
        edges_for = {}

        scored = []
        for x, y in target_flows:
            da = manhattan((int(by_id[x].center()[0]), int(by_id[x].center()[1])),
                           (int(by_id[y].center()[0]), int(by_id[y].center()[1])))
            scored.append((da, x, y))
        scored.sort(reverse=True)

        ok_all = True
        for _, x, y in scored:
            px, py = by_id[x], by_id[y]
            sa = port_outside_cell(px, (int(py.center()[0]), int(py.center()[1])), grid)
            sb = port_outside_cell(py, (int(px.center()[0]), int(px.center()[1])), grid)
            path = astar_route(grid, res, sa, sb)
            if path is None:
                ok_all = False
                break
            edges = res.add_path(path)
            paths[(x,y)] = path
            edges_for[(x,y)] = edges

        if ok_all:
            return res, paths

    return res, paths
