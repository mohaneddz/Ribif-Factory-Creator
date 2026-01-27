"""
Configuration constants for factory grid layout generator.
"""

import os

# =========================
# DIRECTORIES
# =========================
OUTPUT_DIR = "output"
ASSETS_DIR = "assets_cache"

OUTPUT_DXF = os.path.join(OUTPUT_DIR, "layout_square.dxf")
OUTPUT_PNG = os.path.join(OUTPUT_DIR, "layout_square.png")

# =========================
# UNITS
# =========================
# If your input width/height are in meters (like your old code), set True.
INPUT_DIMENSIONS_IN_METERS = True

# =========================
# GRID RESOLUTION
# =========================
# cell_mm controls how big a grid cell is in real mm for export.
# You want average machine footprint to land around 2-3 cells.
CELL_MM = 1500  # 1.5m per cell is a decent starting point for factory machines

# Machine footprint quantization (cells)
MIN_FOOTPRINT = 2
MAX_FOOTPRINT = 3  # allow 3 by default; bump to 4 if you have very large machines
KEEP_OUT = 1       # 1-cell clearance ring
PORT_OFFSET = 0    # additional offset in cells for port positioning

# =========================
# ROUTING
# =========================
EDGE_CAPACITY_DEFAULT = 1
EDGE_CAPACITY_TRUNK = 2  # allow merges on trunks
BEND_PENALTY = 3.0
CONGESTION_PENALTY = 0.8
MAX_ASTAR_ITERS = 500_000

# =========================
# PLACEMENT / OPTIMIZATION
# =========================
CANDIDATES_PER_MACHINE = 120
RIPUP_PASSES = 10
LOCAL_ITERS = 1200
LOCAL_MAX_SHIFT = 2
ANNEAL_START_T = 2.5
ANNEAL_END_T = 0.2

# =========================
# SPACE FILLING
# =========================
BBOX_AREA_W = 1.0
HOLE_W = 6.0
FLOW_LEN_W = 1.0
CONGESTION_W = 1.2
