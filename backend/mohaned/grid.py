"""
Grid occupancy management for placement.
"""

from typing import Optional, Tuple, List
from models import Placed
from config import KEEP_OUT


class OccupancyGrid:
    """
    Cell occupancy for machines + keepout.
    Belts are routed on EDGES (separate structure).
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

    def place_machine(self, p: Placed) -> bool:
        """Place machine area + keepout ring as blocked."""
        x, y, w, h = p.x, p.y, p.w, p.h
        k = KEEP_OUT
        # machine area must be free; keepout can also be free (we block it too)
        if not self.rect_free(x - k, y - k, w + 2 * k, h + 2 * k):
            return False
        # mark keepout
        self._mark(x - k, y - k, w + 2 * k, h + 2 * k, 1, None)
        # mark machine cells with id (kept blocked too)
        self._mark(x, y, w, h, 1, p.uid)
        return True

    def remove_machine(self, p: Placed, placed_all: List[Placed]) -> None:
        """
        Slow but safe: rebuild block grid from scratch (used in local search).
        For speed, you can implement incremental undo later.
        """
        self.block = [[0] * self.n for _ in range(self.n)]
        self.machine_id = [[None] * self.n for _ in range(self.n)]
        for q in placed_all:
            if q.uid == p.uid:
                continue
            self.place_machine(q)

    def hole_metric(self) -> int:
        """
        Simple hole penalty: count enclosed free components not touching boundary.
        """
        n = self.n
        seen = [[False]*n for _ in range(n)]
        dirs = [(1,0),(-1,0),(0,1),(0,-1)]

        def bfs(sx, sy) -> Tuple[int, bool]:
            stack = [(sx, sy)]
            seen[sy][sx] = True
            size = 0
            touches_border = False
            while stack:
                x, y = stack.pop()
                size += 1
                if x == 0 or y == 0 or x == n-1 or y == n-1:
                    touches_border = True
                for dx, dy in dirs:
                    nx, ny = x+dx, y+dy
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
