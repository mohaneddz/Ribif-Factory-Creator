"""
Data models for factory grid layout.
"""

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class Machine:
    """Machine definition from data.json"""
    model: str
    name: str = ""
    width: float = 1.0
    height: float = 1.0
    count: int = 1
    image: str = ""
    use: str = ""


@dataclass
class Placed:
    """Placed machine instance on grid"""
    m: Machine
    uid: str
    x: int
    y: int
    w: int
    h: int
    rot: int = 0  # 0: normal, 1: swapped
    img_path: Optional[str] = None

    def rect(self) -> Tuple[int, int, int, int]:
        return (self.x, self.y, self.w, self.h)

    def center(self) -> Tuple[float, float]:
        return (self.x + self.w / 2.0, self.y + self.h / 2.0)
