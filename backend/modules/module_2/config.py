"""
Central configuration for EliteHack layout pipeline.
Merges config/constants/prompts.
Pure configuration only (no logic imports).
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
ASSETS_DIR = os.path.join(BASE_DIR, "assets_cache")
LOCAL_IMAGES_DIR = os.path.join(BASE_DIR, "images")

OUTPUT_DXF = os.path.join(OUTPUT_DIR, "layout_square.dxf")
OUTPUT_PNG = os.path.join(OUTPUT_DIR, "layout_square.png")
REALISTIC_PNG = os.path.join(OUTPUT_DIR, "realistic_layout.png")
REALISTIC_CLEAN_PNG = os.path.join(OUTPUT_DIR, "realistic_clean.png")

PUBLIC_MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(BASE_DIR)), "public", "models")
FINAL_GLB_PATH = os.path.join(PUBLIC_MODELS_DIR, "sample.glb")

CACHE_FILE = os.path.join(ASSETS_DIR, "cache.json")

# =========================
# API KEYS / MODEL IDS
# =========================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
IMAGE_API_KEY = os.getenv("IMAGE_API_KEY", "")
VIDEO_API_KEY = os.getenv("VIDEO_API_KEY", "")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
BASE_IMAGE_URL = os.getenv("BASE_IMAGE_URL", "")

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "gemini-3-pro-image-preview")
VIDEO_MODEL = os.getenv("VIDEO_MODEL", "veo-2.0-generate-001")
REPLICATE_MODEL = os.getenv(
    "REPLICATE_MODEL",
    "firtoz/trellis:e8f6c45206993f297372f5436b90350817bd9b4a0d52d2a76df50c1c8afa2b3c",
)

# =========================
# UNITS / GRID
# =========================
INPUT_DIMENSIONS_IN_METERS = True
CELL_MM = 1500

# Machine footprint quantization (cells)
MIN_FOOTPRINT = 2
MAX_FOOTPRINT = 3
KEEP_OUT = 1
PORT_OFFSET = 0

# =========================
# ROUTING
# =========================
EDGE_CAPACITY_DEFAULT = 1
EDGE_CAPACITY_TRUNK = 2
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
# SCORING
# =========================
BBOX_AREA_W = 1.0
HOLE_W = 6.0
FLOW_LEN_W = 1.0
CONGESTION_W = 1.2

# =========================
# ROUTING ASSESSMENT HEURISTICS
# =========================
DIRECTIONAL_FLOW_W = 120.0
BACKTRACK_W = 80.0
BEND_W = 12.0
STORAGE_EDGE_W = 6.0
FAMILY_CLUSTER_W = 8.0
ALIGNMENT_W = 4.0

STORAGE_KEYWORDS = [
    "storage", "stockage", "silo", "warehouse", "asrs", "inventory", "stock", "stockage en vrac"
]

PROCESS_FAMILY_KEYWORDS = {
    "preparation": ["preparation", "melange", "dosage", "resine", "mix"],
    "forming": ["extrusion", "injection", "moulage", "thermoform", "cintrage", "lamination", "trempe", "formage"],
    "finishing": ["peinture", "vernis", "finishing", "revetement", "coating", "polish"],
    "assembly": ["assemblage", "assembly"],
    "recycling": ["recyclage", "granulation", "broyage"],
}

# =========================
# DXF / RENDER CONSTANTS
# =========================
DXF_BLACK = 7
DXF_BLUE = 5

GRID_MM = 500
AISLE_MM = 1500
MARGIN_MM = 1000
MIN_MACHINE_SIZE_MM = 3500

WALL_THICK_MM = 300
WALL_HATCH_STEP = 450
PILLAR_SIZE_MM = 600

DOOR_WIDTH_MM = 2500
DOOR_DEPTH_MM = 1100

FLOW_OFFSET_MM = 100
BELT_HALF_WIDTH_MM = 400
BELT_COLOR_MAIN = "#505050"
BELT_COLOR_EDGE = "#000000"

TEXT_H_MM = 240
LEGEND_TEXT_H_MM = 180

PIPE_GAP_MM = 220
PIPE_LINE_WIDTH_MM = 150

EMBED_IMAGES_IN_CAD = False
PNG_IMAGE_FILL = 1.0
PNG_MACHINE_SCALE = 1.35

# =========================
# PROMPTS
# =========================
TOP_VIEW_PROMPT_1 = """
PHASE 1 - GEOMETRY UNLOCK
... (legacy placeholder)
""".strip()

TOP_VIEW_REALISTIC_BELTS = """
Transform this 2D factory layout into a photorealistic, high-detail top-down view.

CRITICAL CONSTRAINTS (must follow):
- DO NOT move, rotate, scale, reorder, crop, or relabel any machine or belt. Max position drift <= 2 px, scale drift <= 5%.
- DO NOT add or remove machines, belts, ports, or connections. Machine count and connectivity must be identical.
- Belts must follow the EXACT original path geometry and endpoints. No rerouting, smoothing, or curvature changes.
- Strict 90-degree orthographic top-down view. No tilt, no perspective.
- No shadows, AO, or lighting gradients that alter geometry edges.
- Background must be flat #00FF00 (pure green), no texture, no noise, no vignette.
- Crisp hard edges, no feathering, no translucency, no green spill.

VISUAL UPGRADES (allowed):
- Enhance material realism on machines and belts without changing geometry.
- Add surface detail that stays within existing silhouettes.

Output a single PNG.
""".strip()

MACHINE_PIPELINE_PROMPT = """
INPUT: A list of factory items.

{machines_list}

RULE (critical): Only include REAL MACHINES (equipment). Exclude materials/consumables/packaging stock.

EXCLUDE examples:
- film rolls / shrink film / PE film
- PET preforms / bottle blanks / empty bottles
- caps / labels / cartons / boxes / pallets
- ink / glue / adhesive
- storage-only items

INCLUDE examples:
- blow molder, rinser, filler, capper, labeler
- conveyors, elevators, feeders, sorters
- shrink wrapper machine, case packer/cartoner, palletizer
- inspection/vision, printer/date coder

TASK:
Return a JSON plan:
- groups: logical stages/areas
- flows: machine-to-machine links (type="conveyor")
- layout_suggestion: linear/u_shape/parallel + short reasoning
- width_m: conveyor width in meters (typical 0.6-1.0)

OUTPUT JSON ONLY:
{
  "groups": [
    { "name": "Group Name", "machines": ["MachineID1", "MachineID2"], "purpose": "short purpose" }
  ],
  "flows": [
    { "from": "MachineID", "to": "MachineID", "type": "conveyor", "material": "what moves", "width_m": 0.8 }
  ],
  "layout_suggestion": { "arrangement": "linear|u_shape|parallel", "reasoning": "short reason" }
}
""".strip()

PASS1_PROMPT = """
You are given ONE industrial machine image (PNG).

TASK:
Re-render this machine as a PERFECT 90 degree TOP-DOWN VIEW (plan view).
It must look highly detailed and realistic.

CRITICAL CONSTRAINTS (must follow):
- DO NOT move, rotate, scale, reorder, or crop the machine. Scale change <= 5%.
- Preserve the exact footprint proportions and silhouette.
- No added/removed parts that change topology or overall shape.
- Strict 90-degree orthographic top-down view only (no tilt).
- No shadows, AO, glow, gradients, or reflections that affect edges.
- Background must be flat #00FF00 (pure green), no texture, no noise.
- Crisp hard edges, no feathering, no translucency, no green spill.

DETAIL (allowed):
- Add surface detail on the top only: panels, bolts, vents, rails, motors, guards.

BACKGROUND RULES:
- Background MUST be exactly #00FF00, flat.
- NO shadows, NO AO, NO gradients, NO vignette on the green.

OUTPUT:
Return ONE PNG of the machine in true TOP VIEW on #00FF00. Do not add any text or labels.
""".strip()


def format_machine_list(machines):
    lines = []
    for m in machines:
        count = int(m.get("count", 1) or 1)
        name = str(m.get("name") or m.get("model") or "")
        model = str(m.get("model") or m.get("name") or "Machine")
        use = str(m.get("use") or "")
        width = float(m.get("width", 1.0))
        height = float(m.get("height", 1.0))
        if count <= 1:
            lines.append(f"- {name} (ID: {model}): {use} | Size: {width}m x {height}m")
        else:
            for i in range(count):
                uid = f"{model}_{i+1}"
                lines.append(f"- {name} #{i+1} (ID: {uid}): {use} | Size: {width}m x {height}m")
    return "\n".join(lines)
