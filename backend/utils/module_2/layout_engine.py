"""
Core layout logic: placement, routing, and optimization.
All math is done in grid coordinates (integers).
"""
from __future__ import annotations

import heapq
import math
import random
import unicodedata
from typing import Dict, List, Optional, Set, Tuple, TypedDict

try:
    from .config import (
        CELL_MM,
        INPUT_DIMENSIONS_IN_METERS,
        MIN_FOOTPRINT,
        MAX_FOOTPRINT,
        KEEP_OUT,
        PORT_OFFSET,
        EDGE_CAPACITY_DEFAULT,
        EDGE_CAPACITY_TRUNK,
        BEND_PENALTY,
        CONGESTION_PENALTY,
        MAX_ASTAR_ITERS,
        CANDIDATES_PER_MACHINE,
        RIPUP_PASSES,
        LOCAL_ITERS,
        LOCAL_MAX_SHIFT,
        ANNEAL_START_T,
        ANNEAL_END_T,
        BBOX_AREA_W,
        HOLE_W,
        FLOW_LEN_W,
        CONGESTION_W,
        DIRECTIONAL_FLOW_W,
        BACKTRACK_W,
        BEND_W,
        STORAGE_EDGE_W,
        FAMILY_CLUSTER_W,
        ALIGNMENT_W,
        STORAGE_KEYWORDS,
        PROCESS_FAMILY_KEYWORDS,
    )
except ImportError:  # Fallback for running as a script.
    from config import (
        CELL_MM,
        INPUT_DIMENSIONS_IN_METERS,
        MIN_FOOTPRINT,
        MAX_FOOTPRINT,
        KEEP_OUT,
        PORT_OFFSET,
        EDGE_CAPACITY_DEFAULT,
        EDGE_CAPACITY_TRUNK,
        BEND_PENALTY,
        CONGESTION_PENALTY,
        MAX_ASTAR_ITERS,
        CANDIDATES_PER_MACHINE,
        RIPUP_PASSES,
        LOCAL_ITERS,
        LOCAL_MAX_SHIFT,
        ANNEAL_START_T,
        ANNEAL_END_T,
        BBOX_AREA_W,
        HOLE_W,
        FLOW_LEN_W,
        CONGESTION_W,
        DIRECTIONAL_FLOW_W,
        BACKTRACK_W,
        BEND_W,
        STORAGE_EDGE_W,
        FAMILY_CLUSTER_W,
        ALIGNMENT_W,
        STORAGE_KEYWORDS,
        PROCESS_FAMILY_KEYWORDS,
    )

Flow = Tuple[str, str]
Node = Tuple[int, int]
Path = List[Node]
EdgeKey = Tuple[str, int, int]


class MachineDict(TypedDict, total=False):
    model: str
    name: str
    width: float
    height: float
    count: int
    image: str
    use: str
    image_path: str
    image_nobg_path: str


class PlacedDict(TypedDict):
    machine: MachineDict
    uid: str
    x: int
    y: int
    w: int
    h: int
    rot: int
    img_path: Optional[str]


# =========================
# Grid / Occupancy
# =========================
class OccupancyGrid:
    """
    Cell occupancy for machines + keepout.
    Belts are routed on edges (separate structure).
    """

    def __init__(self, n: int):
        self.n = n
        # 0: free, 1: blocked (machine or keepout)
        self.block = [[0] * n for _ in range(n)]
        self.machine_id = [[None] * n for _ in range(n)]

    def inside(self, x: int, y: int) -> bool:
        return 0 <= x < self.n and 0 <= y < self.n

    def rect_free(self, x: int, y: int, w: int, h: int) -> bool:
        if x < 0 or y < 0 or x + w > self.n or y + h > self.n:
            return False
        for yy in range(y, y + h):
            row = self.block[yy]
            for xx in range(x, x + w):
                if row[xx] != 0:
                    return False
        return True

    def _mark(self, x: int, y: int, w: int, h: int, val: int, mid: Optional[str]):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                if 0 <= xx < self.n and 0 <= yy < self.n:
                    self.block[yy][xx] = val
                    self.machine_id[yy][xx] = mid

    def place_machine(self, p: PlacedDict) -> bool:
        """Place machine area + keepout ring as blocked."""
        x, y, w, h = p["x"], p["y"], p["w"], p["h"]
        k = KEEP_OUT
        # machine area must be free; keepout can also be free (we block it too)
        if not self.rect_free(x - k, y - k, w + 2 * k, h + 2 * k):
            return False
        # mark keepout
        self._mark(x - k, y - k, w + 2 * k, h + 2 * k, 1, None)
        # mark machine cells with id (kept blocked too)
        self._mark(x, y, w, h, 1, p["uid"])
        return True

    def remove_machine(self, p: PlacedDict, placed_all: List[PlacedDict]) -> None:
        """
        Slow but safe: rebuild block grid from scratch (used in local search).
        """
        self.block = [[0] * self.n for _ in range(self.n)]
        self.machine_id = [[None] * self.n for _ in range(self.n)]
        for q in placed_all:
            if q["uid"] == p["uid"]:
                continue
            self.place_machine(q)

    def hole_metric(self) -> int:
        """Simple hole penalty: count enclosed free components not touching boundary."""
        n = self.n
        seen = [[False] * n for _ in range(n)]
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]

        def bfs(sx, sy) -> Tuple[int, bool]:
            stack = [(sx, sy)]
            seen[sy][sx] = True
            size = 0
            touches_border = False
            while stack:
                x, y = stack.pop()
                size += 1
                if x == 0 or y == 0 or x == n - 1 or y == n - 1:
                    touches_border = True
                for dx, dy in dirs:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < n and 0 <= ny < n and not seen[ny][nx] and self.block[ny][nx] == 0:
                        seen[ny][nx] = True
                        stack.append((nx, ny))
            return size, touches_border

        holes = 0
        for y in range(n):
            for x in range(n):
                if self.block[y][x] == 0 and not seen[y][x]:
                    size, touches = bfs(x, y)
                    if not touches:
                        holes += size
        return holes


# =========================
# Placement
# =========================
def _dim_to_cells(v: float) -> int:
    """Convert input dimension directly to grid cells."""
    mm = v * 1000.0 if INPUT_DIMENSIONS_IN_METERS else v
    cells = int(round(mm / CELL_MM))
    return max(MIN_FOOTPRINT, min(MAX_FOOTPRINT, cells))


def quantize_footprint(m: MachineDict) -> Tuple[int, int]:
    w = _dim_to_cells(float(m.get("width", 1.0)))
    h = _dim_to_cells(float(m.get("height", 1.0)))
    return w, h


def expand_machines(machines: List[MachineDict]) -> List[Tuple[MachineDict, str]]:
    """Expand machines with count > 1 into individual instances."""
    out: List[Tuple[MachineDict, str]] = []
    for m in machines:
        model = str(m.get("model") or m.get("name") or "Machine")
        count = int(m.get("count", 1) or 1)
        if count <= 1:
            out.append((m, model))
        else:
            for i in range(count):
                out.append((m, f"{model}_{i+1}"))
    return out


def build_graph(flows: List[Flow]) -> Dict[str, Set[str]]:
    g: Dict[str, Set[str]] = {}
    for a, b in flows:
        g.setdefault(a, set()).add(b)
        g.setdefault(b, set()).add(a)
    return g


def _center(p: PlacedDict) -> Tuple[float, float]:
    return (p["x"] + p["w"] / 2.0, p["y"] + p["h"] / 2.0)


def bbox_of(placed: List[PlacedDict]) -> Tuple[int, int, int, int]:
    if not placed:
        return (0, 0, 0, 0)
    minx = min(p["x"] for p in placed)
    miny = min(p["y"] for p in placed)
    maxx = max(p["x"] + p["w"] for p in placed)
    maxy = max(p["y"] + p["h"] for p in placed)
    return (minx, miny, maxx, maxy)


def bbox_area(placed: List[PlacedDict]) -> int:
    minx, miny, maxx, maxy = bbox_of(placed)
    return max(0, (maxx - minx) * (maxy - miny))


def estimate_flow_cost(
    placed_by_id: Dict[str, PlacedDict], uid: str, cand: PlacedDict, flows: List[Flow]
) -> float:
    cost = 0.0
    cx, cy = _center(cand)
    for a, b in flows:
        if a == uid and b in placed_by_id:
            px, py = _center(placed_by_id[b])
            cost += abs(cx - px) + abs(cy - py)
        elif b == uid and a in placed_by_id:
            px, py = _center(placed_by_id[a])
            cost += abs(cx - px) + abs(cy - py)
    return cost


def candidate_positions(
    grid: OccupancyGrid, w: int, h: int, k: int, rng: random.Random, budget: int
) -> List[Tuple[int, int]]:
    n = grid.n
    cands: List[Tuple[int, int]] = []

    # 1) biased random samples
    tries = max(30, budget // 2)
    for _ in range(tries):
        x = rng.randint(0, max(0, n - w))
        y = rng.randint(0, max(0, n - h))
        if grid.rect_free(x - k, y - k, w + 2 * k, h + 2 * k):
            cands.append((x, y))
            if len(cands) >= budget:
                return cands

    # 2) scan a coarse grid
    step = max(1, int(math.sqrt(n)))
    for y in range(0, n - h + 1, max(1, step // 2)):
        for x in range(0, n - w + 1, max(1, step // 2)):
            if grid.rect_free(x - k, y - k, w + 2 * k, h + 2 * k):
                cands.append((x, y))
                if len(cands) >= budget:
                    return cands

    return cands


def _select_img_path(m: MachineDict) -> Optional[str]:
    return m.get("image_nobg_path") or m.get("image_path") or m.get("image") or None


def place_all(
    expanded: List[Tuple[MachineDict, str]],
    flows: List[Flow],
    n: int,
    seed: int = 7,
) -> Tuple[OccupancyGrid, List[PlacedDict]]:
    """Greedy placement of all machines."""
    rng = random.Random(seed)
    grid = OccupancyGrid(n)

    g = build_graph(flows)

    # order machines: area desc then degree desc
    tmp = []
    for m, uid in expanded:
        w, h = quantize_footprint(m)
        deg = len(g.get(uid, set()))
        tmp.append((w * h, deg, m, uid))
    tmp.sort(key=lambda t: (t[0], t[1]), reverse=True)

    placed: List[PlacedDict] = []
    placed_by_id: Dict[str, PlacedDict] = {}

    for _, _, m, uid in tmp:
        base_w, base_h = quantize_footprint(m)
        # allow rotation (swap)
        variants = [(base_w, base_h, 0)]
        if base_w != base_h:
            variants.append((base_h, base_w, 1))

        best: Optional[PlacedDict] = None
        best_score = 1e18
        img_path = _select_img_path(m)

        for vw, vh, rot in variants:
            cands = candidate_positions(grid, vw, vh, KEEP_OUT, rng, CANDIDATES_PER_MACHINE)
            for (x, y) in cands:
                cand: PlacedDict = {
                    "machine": m,
                    "uid": uid,
                    "x": x,
                    "y": y,
                    "w": vw,
                    "h": vh,
                    "rot": rot,
                    "img_path": img_path,
                }
                flow_est = estimate_flow_cost(placed_by_id, uid, cand, flows)
                test_list = placed + [cand]
                bb = bbox_area(test_list)
                score = FLOW_LEN_W * flow_est + BBOX_AREA_W * bb * 0.05
                if score < best_score:
                    if grid.rect_free(x - KEEP_OUT, y - KEEP_OUT, vw + 2 * KEEP_OUT, vh + 2 * KEEP_OUT):
                        best_score = score
                        best = cand

        if best is None:
            raise RuntimeError(f"Failed to place machine {uid}. Increase grid size or reduce footprints.")

        ok = grid.place_machine(best)
        if not ok:
            raise RuntimeError(f"Internal placement error for {uid}.")

        placed.append(best)
        placed_by_id[uid] = best

    return grid, placed


def compute_grid_size(expanded: List[Tuple[MachineDict, str]]) -> int:
    total = 0
    for m, _ in expanded:
        w, h = quantize_footprint(m)
        total += (w + 2 * KEEP_OUT) * (h + 2 * KEEP_OUT)
    # fill factor provides room for belts and fewer holes
    fill_factor = 1.9
    n = int(math.ceil(math.sqrt(total * fill_factor)))
    n = max(n, 12)
    return n


# =========================
# Routing
# =========================
class EdgeReservation:
    def __init__(self):
        self.use: Dict[EdgeKey, int] = {}
        self.cap: Dict[EdgeKey, int] = {}

    def capacity(self, e: EdgeKey) -> int:
        return self.cap.get(e, EDGE_CAPACITY_DEFAULT)

    def set_capacity_rect_trunk(self, x1: int, y1: int, x2: int, y2: int) -> None:
        """Mark a trunk corridor rectangle edges with higher capacity to allow merges."""
        for y in range(y1, y2 + 1):
            for x in range(x1, x2):
                self.cap[("H", x, y)] = EDGE_CAPACITY_TRUNK
        for x in range(x1, x2 + 1):
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
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


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
    dir_from: Dict[Node, Optional[Tuple[int, int]]] = {start: None}

    heapq.heappush(openh, (manhattan(start, goal), 0.0, start))
    iters = 0

    while openh:
        iters += 1
        if iters > MAX_ASTAR_ITERS:
            return None
        _, gc, cur = heapq.heappop(openh)
        if cur == goal:
            path = [cur]
            while cur in parent:
                cur = parent[cur]
                path.append(cur)
            path.reverse()
            return path

        for nb in [
            (cur[0] + 1, cur[1]),
            (cur[0] - 1, cur[1]),
            (cur[0], cur[1] + 1),
            (cur[0], cur[1] - 1),
        ]:
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
            dcur = (nb[0] - cur[0], nb[1] - cur[1])
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


def pick_port(src: PlacedDict, dst: PlacedDict) -> Node:
    """Choose a start cell near src facing dst."""
    sx, sy = _center(src)
    dx, dy = _center(dst)
    if abs(dx - sx) > abs(dy - sy):
        if dx > sx:
            px = min(src["x"] + src["w"] + PORT_OFFSET, src["x"] + src["w"] - 1)
            py = int(round(src["y"] + src["h"] / 2))
            return (min(px, src["x"] + src["w"] - 1), min(max(py, src["y"]), src["y"] + src["h"] - 1))
        px = max(src["x"] - 1 - PORT_OFFSET, src["x"])
        py = int(round(src["y"] + src["h"] / 2))
        return (max(px, src["x"]), min(max(py, src["y"]), src["y"] + src["h"] - 1))
    if dy > sy:
        px = int(round(src["x"] + src["w"] / 2))
        py = min(src["y"] + src["h"] + PORT_OFFSET, src["y"] + src["h"] - 1)
        return (min(max(px, src["x"]), src["x"] + src["w"] - 1), min(py, src["y"] + src["h"] - 1))
    px = int(round(src["x"] + src["w"] / 2))
    py = max(src["y"] - 1 - PORT_OFFSET, src["y"])
    return (min(max(px, src["x"]), src["x"] + src["w"] - 1), max(py, src["y"]))


def port_outside_cell(p: PlacedDict, towards: Node, grid: OccupancyGrid) -> Node:
    """Move from inside machine to nearest free cell adjacent to its boundary."""
    cx, cy = _center(p)
    tx, ty = towards
    best = None
    bestd = 1e18
    for y in range(max(0, p["y"] - (KEEP_OUT + 2)), min(grid.n, p["y"] + p["h"] + (KEEP_OUT + 2))):
        for x in range(max(0, p["x"] - (KEEP_OUT + 2)), min(grid.n, p["x"] + p["w"] + (KEEP_OUT + 2))):
            if grid.block[y][x] == 0:
                d = abs(x - tx) + abs(y - ty) + 0.2 * (abs(x - cx) + abs(y - cy))
                if d < bestd:
                    bestd = d
                    best = (x, y)
    return best if best else (int(cx), int(cy))


def route_all_flows(
    grid: OccupancyGrid,
    placed: List[PlacedDict],
    flows: List[Flow],
) -> Tuple[EdgeReservation, Dict[Flow, Path], Dict[Flow, List[EdgeKey]]]:
    by_id = {p["uid"]: p for p in placed}
    res = EdgeReservation()

    # optional trunk corridor
    n = grid.n
    mid = n // 2
    res.set_capacity_rect_trunk(max(0, mid - 2), 0, min(n - 1, mid + 2), n - 1)

    paths: Dict[Flow, Path] = {}
    edges_for: Dict[Flow, List[EdgeKey]] = {}

    scored = []
    for a, b in flows:
        if a not in by_id or b not in by_id:
            continue
        da = manhattan(
            (int(_center(by_id[a])[0]), int(_center(by_id[a])[1])),
            (int(_center(by_id[b])[0]), int(_center(by_id[b])[1])),
        )
        scored.append((da, a, b))
    scored.sort(reverse=True)

    for _, a, b in scored:
        pa, pb = by_id[a], by_id[b]
        approx = (int(_center(pb)[0]), int(_center(pb)[1]))
        sa = port_outside_cell(pa, approx, grid)
        sb = port_outside_cell(pb, (int(_center(pa)[0]), int(_center(pa)[1])), grid)

        path = astar_route(grid, res, sa, sb)
        if path is None:
            return res, paths, edges_for  # partial
        edges = res.add_path(path)
        paths[(a, b)] = path
        edges_for[(a, b)] = edges

    return res, paths, edges_for


def ripup_reroute(
    grid: OccupancyGrid,
    placed: List[PlacedDict],
    flows: List[Flow],
) -> Tuple[EdgeReservation, Dict[Flow, Path]]:
    by_id = {p["uid"]: p for p in placed}

    # initial attempt
    res, paths, edges_for = route_all_flows(grid, placed, flows)
    if len(paths) == len([f for f in flows if f[0] in by_id and f[1] in by_id]):
        return res, paths

    # iterative ripup
    for _pass in range(RIPUP_PASSES):
        target_flows = [(a, b) for (a, b) in flows if a in by_id and b in by_id]
        if len(paths) == len(target_flows):
            return res, paths

        unrouted = [f for f in target_flows if f not in paths]
        if not unrouted:
            return res, paths

        routed = list(paths.keys())
        routed.sort(key=lambda k: len(paths[k]), reverse=True)
        k_remove = min(6, max(2, len(routed) // 6))
        to_remove = routed[:k_remove]

        for key in to_remove:
            res.remove_edges(edges_for[key])
            del edges_for[key]
            del paths[key]

        # fresh reroute
        fresh = EdgeReservation()
        n = grid.n
        mid = n // 2
        fresh.set_capacity_rect_trunk(max(0, mid - 2), 0, min(n - 1, mid + 2), n - 1)

        res = fresh
        paths = {}
        edges_for = {}

        scored = []
        for x, y in target_flows:
            da = manhattan(
                (int(_center(by_id[x])[0]), int(_center(by_id[x])[1])),
                (int(_center(by_id[y])[0]), int(_center(by_id[y])[1])),
            )
            scored.append((da, x, y))
        scored.sort(reverse=True)

        ok_all = True
        for _, x, y in scored:
            px, py = by_id[x], by_id[y]
            sa = port_outside_cell(px, (int(_center(py)[0]), int(_center(py)[1])), grid)
            sb = port_outside_cell(py, (int(_center(px)[0]), int(_center(px)[1])), grid)
            path = astar_route(grid, res, sa, sb)
            if path is None:
                ok_all = False
                break
            edges = res.add_path(path)
            paths[(x, y)] = path
            edges_for[(x, y)] = edges

        if ok_all:
            return res, paths

    return res, paths


# =========================
# Optimization (Simulated Annealing)
# =========================
def total_congestion(res: EdgeReservation) -> int:
    return sum(max(0, u - 1) for u in res.use.values())


def total_flow_len(paths: Dict[Flow, Path]) -> int:
    return sum(len(p) for p in paths.values())


def _strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def _machine_text(m: MachineDict) -> str:
    raw = f"{m.get('name','')} {m.get('model','')} {m.get('use','')}".lower()
    return _strip_accents(raw)


def _family_for_machine(m: MachineDict) -> Optional[str]:
    text = _machine_text(m)
    for family, keywords in PROCESS_FAMILY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return family
    return None


def _is_storage(m: MachineDict) -> bool:
    text = _machine_text(m)
    return any(kw in text for kw in STORAGE_KEYWORDS)


def _count_bends(path: Path) -> int:
    if len(path) < 3:
        return 0
    bends = 0
    prev = (path[1][0] - path[0][0], path[1][1] - path[0][1])
    for i in range(2, len(path)):
        cur = (path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1])
        if cur != prev:
            bends += 1
        prev = cur
    return bends


def _direction_penalties(placed: List[PlacedDict], flows: List[Flow]) -> Tuple[float, int]:
    by_id = {p["uid"]: p for p in placed}
    vectors: List[Tuple[float, float]] = []
    for a, b in flows:
        if a not in by_id or b not in by_id:
            continue
        ax, ay = _center(by_id[a])
        bx, by = _center(by_id[b])
        dx, dy = bx - ax, by - ay
        if dx == 0 and dy == 0:
            continue
        vectors.append((dx, dy))

    if not vectors:
        return 0.0, 0

    # dominant direction = sum of vectors
    sum_x = sum(v[0] for v in vectors)
    sum_y = sum(v[1] for v in vectors)
    if sum_x == 0 and sum_y == 0:
        sum_x, sum_y = 1.0, 0.0
    dom_len = math.hypot(sum_x, sum_y)
    dom = (sum_x / dom_len, sum_y / dom_len)

    penalty = 0.0
    backtracks = 0
    for dx, dy in vectors:
        vlen = math.hypot(dx, dy)
        if vlen == 0:
            continue
        cos = (dx / vlen) * dom[0] + (dy / vlen) * dom[1]
        penalty += (1.0 - cos)
        if cos < 0:
            backtracks += 1
    return penalty, backtracks


def _family_cluster_penalty(placed: List[PlacedDict]) -> float:
    groups: Dict[str, List[PlacedDict]] = {}
    for p in placed:
        fam = _family_for_machine(p["machine"])
        if not fam:
            continue
        groups.setdefault(fam, []).append(p)

    penalty = 0.0
    for members in groups.values():
        if len(members) < 2:
            continue
        dsum = 0.0
        count = 0
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                ax, ay = _center(members[i])
                bx, by = _center(members[j])
                dsum += abs(ax - bx) + abs(ay - by)
                count += 1
        if count:
            penalty += dsum / count
    return penalty


def _storage_edge_penalty(grid: OccupancyGrid, placed: List[PlacedDict]) -> float:
    penalty = 0.0
    for p in placed:
        if not _is_storage(p["machine"]):
            continue
        x, y, w, h = p["x"], p["y"], p["w"], p["h"]
        dist = min(x, y, grid.n - (x + w), grid.n - (y + h))
        penalty += max(0.0, float(dist))
    return penalty


def _alignment_penalty(placed: List[PlacedDict]) -> float:
    if len(placed) < 2:
        return 0.0
    centers = [(_center(p)[0], _center(p)[1]) for p in placed]
    penalty = 0.0
    for i in range(len(centers)):
        cx, cy = centers[i]
        best = None
        for j in range(len(centers)):
            if i == j:
                continue
            ox, oy = centers[j]
            align = min(abs(cx - ox), abs(cy - oy))
            if best is None or align < best:
                best = align
        if best is not None:
            penalty += best
    return penalty


def layout_score(grid: OccupancyGrid, placed: List[PlacedDict], res: EdgeReservation, paths: Dict[Flow, Path], flows: List[Flow]) -> float:
    bb = bbox_area(placed)
    holes = grid.hole_metric()
    fl = total_flow_len(paths)
    cong = total_congestion(res)
    bends = sum(_count_bends(p) for p in paths.values())
    dir_penalty, backtracks = _direction_penalties(placed, flows)
    storage_penalty = _storage_edge_penalty(grid, placed)
    family_penalty = _family_cluster_penalty(placed)
    align_penalty = _alignment_penalty(placed)
    return (
        BBOX_AREA_W * bb
        + HOLE_W * holes * 40.0
        + FLOW_LEN_W * fl * 120.0
        + CONGESTION_W * cong * 400.0
        + BEND_W * bends
        + DIRECTIONAL_FLOW_W * dir_penalty
        + BACKTRACK_W * backtracks
        + STORAGE_EDGE_W * storage_penalty
        + FAMILY_CLUSTER_W * family_penalty
        + ALIGNMENT_W * align_penalty
    )


def rebuild_grid(n: int, placed: List[PlacedDict]) -> OccupancyGrid:
    g = OccupancyGrid(n)
    for p in placed:
        if not g.place_machine(p):
            raise RuntimeError("Rebuild failed (overlap).")
    return g


def _clone_placed(p: PlacedDict) -> PlacedDict:
    return {
        "machine": p["machine"],
        "uid": p["uid"],
        "x": p["x"],
        "y": p["y"],
        "w": p["w"],
        "h": p["h"],
        "rot": p["rot"],
        "img_path": p.get("img_path"),
    }


def local_improve(
    placed: List[PlacedDict],
    flows: List[Flow],
    n: int,
    seed: int = 9,
) -> Tuple[List[PlacedDict], EdgeReservation, Dict[Flow, Path]]:
    rng = random.Random(seed)

    # Working copy to mutate
    placed = [_clone_placed(p) for p in placed]

    grid = rebuild_grid(n, placed)
    res, paths = ripup_reroute(grid, placed, flows)
    best_score = layout_score(grid, placed, res, paths, flows)

    best = [_clone_placed(p) for p in placed]
    best_res, best_paths = res, paths

    def temperature(t: int) -> float:
        if LOCAL_ITERS <= 1:
            return ANNEAL_END_T
        alpha = t / (LOCAL_ITERS - 1)
        return ANNEAL_START_T * (1 - alpha) + ANNEAL_END_T * alpha

    uid_set = {p["uid"] for p in placed}

    for it in range(LOCAL_ITERS):
        T = temperature(it)

        # propose move
        idx = rng.randrange(len(placed))
        p = placed[idx]
        old = _clone_placed(p)

        if rng.random() < 0.15 and p["w"] != p["h"]:
            p["w"], p["h"] = p["h"], p["w"]
            p["rot"] ^= 1
        else:
            dx = rng.randint(-LOCAL_MAX_SHIFT, LOCAL_MAX_SHIFT)
            dy = rng.randint(-LOCAL_MAX_SHIFT, LOCAL_MAX_SHIFT)
            p["x"] = max(0, min(n - p["w"], p["x"] + dx))
            p["y"] = max(0, min(n - p["h"], p["y"] + dy))

        # Quick validation: check if new position would cause overlap
        temp_grid = OccupancyGrid(n)
        valid_move = True
        for q in placed:
            if q["uid"] == p["uid"]:
                continue
            if not temp_grid.place_machine(q):
                valid_move = False
                break
        if valid_move:
            valid_move = temp_grid.place_machine(p)

        if not valid_move:
            placed[idx] = old
            continue

        try:
            grid2 = rebuild_grid(n, placed)
            res2, paths2 = ripup_reroute(grid2, placed, flows)
        except RuntimeError:
            placed[idx] = old
            continue

        target_count = len([f for f in flows if f[0] in uid_set and f[1] in uid_set])
        routed = len(paths2)
        if routed < max(1, int(0.95 * target_count)):
            placed[idx] = old
            continue

        s2 = layout_score(grid2, placed, res2, paths2, flows)
        delta = s2 - best_score

        accept = False
        if s2 <= best_score:
            accept = True
        else:
            prob = math.exp(-delta / max(1e-9, T * 5000.0))
            if rng.random() < prob:
                accept = True

        if accept:
            grid, res, paths = grid2, res2, paths2
            if s2 < best_score:
                best_score = s2
                best = [_clone_placed(q) for q in placed]
                best_res, best_paths = res2, paths2
        else:
            placed[idx] = old

    return best, best_res, best_paths


def generate_layout(
    machines: List[MachineDict],
    flows: List[Flow],
    seed: int = 7,
) -> Tuple[Dict[str, object], Dict[Flow, Path]]:
    """End-to-end layout generation (placement + annealing + final routing)."""
    expanded = expand_machines(machines)
    n = compute_grid_size(expanded)
    grid, placed = place_all(expanded, flows, n, seed=seed)
    best, _, _ = local_improve(placed, flows, n, seed=seed + 1)
    grid_final = rebuild_grid(n, best)
    _, paths_final = ripup_reroute(grid_final, best, flows)
    layout_data = {"grid_size": n, "placed": best}
    return layout_data, paths_final
