"""
Constants for factory layout generation
"""

# DXF Colors
DXF_BLACK = 7
DXF_BLUE = 5

# Layout dimensions (mm)
GRID_MM = 500

# --- CRITICAL FIXES FOR VISUAL DENSITY ---
# Reduced from 8000 to 1500. 
# This pulls machines closer together so they fill the frame.
AISLE_MM = 1500  

# Reduced from 4000 to 1000.
# Less empty border around the edges.
MARGIN_MM = 1000

# Increased from 2500 to 3500.
# Ensures even small machines look chunky and visible.
MIN_MACHINE_SIZE_MM = 3500  
# -----------------------------------------


# Wall specifications
WALL_THICK_MM = 300          # Thicker walls for better visibility
WALL_HATCH_STEP = 450
PILLAR_SIZE_MM = 600         # Thicker pillars

# Door specifications
DOOR_WIDTH_MM = 2500         
DOOR_DEPTH_MM = 1100

# Flow/conveyor specifications
# Increased sizes to make connections look like solid infrastructure, not thin wires
FLOW_OFFSET_MM = 100         # Tighter connections
BELT_HALF_WIDTH_MM = 400     # Much wider conveyors (visual width ~800mm)
BELT_COLOR_MAIN = "#505050"  # Darker grey for contrast
BELT_COLOR_EDGE = "#000000"  

# Text specifications
TEXT_H_MM = 600              # Larger text
LEGEND_TEXT_H_MM = 400

# Flow/pipe drawing defaults
PIPE_GAP_MM = 220            
PIPE_LINE_WIDTH_MM = 150     # Thicker flow lines for DXF

# Asset directory
ASSETS_DIR = "assets_cache"

# Image embedding settings
EMBED_IMAGES_IN_CAD = False  
PNG_IMAGE_FILL = 1.0         # Maximize image size within its bounding box