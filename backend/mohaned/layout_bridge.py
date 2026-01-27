"""
Bridge module connecting grid layout system to existing drawing utilities.

This module converts grid-based layout data (Placed objects) into the format
expected by plot_utils and dwg_utils for visualization.
"""

import os
from typing import List, Tuple, Optional, Dict, Callable
from models import Placed
from dwg_utils import Room, PlacedMachine
from data import Machine
from config import CELL_MM


def grid_to_placed_machines(placed: List[Placed], cell_mm: float = CELL_MM) -> List[PlacedMachine]:
    """
    Convert grid Placed objects to dwg_utils PlacedMachine objects.
    
    Args:
        placed: List of Placed objects from grid layout
        cell_mm: Millimeters per grid cell
        
    Returns:
        List of PlacedMachine objects with mm coordinates
    """
    machines = []
    for p in placed:
        # Prefer background-removed image if available (base_nobg.png)
        chosen_img = p.img_path
        try:
            if p.img_path:
                base, ext = os.path.splitext(p.img_path)
                nobg_candidate = f"{base}_nobg.png"
                if os.path.exists(nobg_candidate):
                    chosen_img = nobg_candidate

        except Exception:
            chosen_img = p.img_path

        pm = PlacedMachine(
            m=p.m,
            x=int(p.x * cell_mm),
            y=int(p.y * cell_mm),
            w=int(p.w * cell_mm),
            h=int(p.h * cell_mm),
            img_path=chosen_img
        )
        # Store UID for matching in find_machine
        pm.uid = p.uid
        machines.append(pm)
    return machines


def grid_to_rooms(placed: List[Placed], n: int, cell_mm: float = CELL_MM) -> List[Room]:
    """
    Convert grid layout to Room structure.
    
    Creates a single "Factory" room containing all machines.
    
    Args:
        placed: List of Placed objects from grid layout
        n: Grid size (n x n cells)
        cell_mm: Millimeters per grid cell
        
    Returns:
        List containing single Room with all machines
    """
    machines = grid_to_placed_machines(placed, cell_mm)
    
    # Calculate room bounds from grid size
    room_size_mm = int(n * cell_mm)
    
    room = Room(
        name="Factory",
        x=0,
        y=0,
        w=room_size_mm,
        h=room_size_mm,
        machines=machines
    )
    
    return [room]


def find_machine(rooms: List[Room], uid: str) -> Optional[PlacedMachine]:
    """
    Find a machine by UID across all rooms.
    
    Args:
        rooms: List of Room objects
        uid: Machine unique identifier
        
    Returns:
        PlacedMachine if found, None otherwise
    """
    for room in rooms:
        for machine in room.machines:
            # Check the uid attribute we set during conversion
            if hasattr(machine, 'uid') and machine.uid == uid:
                return machine
            # Fallback to model name for single-instance machines
            if machine.m.model == uid:
                return machine
    return None


def route_machines(a: PlacedMachine, b: PlacedMachine) -> List[Tuple[float, float]]:
    """
    Create a simple routing path between two machines.
    
    For now, uses direct routing from center to center.
    Can be enhanced later with A* pathfinding.
    
    Args:
        a: Source machine
        b: Destination machine
        
    Returns:
        List of (x_mm, y_mm) waypoints
    """
    # Calculate centers
    ax = a.x + a.w / 2.0
    ay = a.y + a.h / 2.0
    bx = b.x + b.w / 2.0
    by = b.y + b.h / 2.0
    
    # Simple L-shaped routing (horizontal then vertical)
    # This avoids diagonal lines which look less industrial
    return [
        (ax, ay),
        (bx, ay),  # Horizontal segment
        (bx, by)   # Vertical segment
    ]


def export_layout_with_existing_utils(
    placed: List[Placed],
    paths: Dict[Tuple[str, str], List[Tuple[int, int]]],
    n: int,
    cell_mm: float,
    flows: List[Tuple[str, str]],
    output_png: str,
    output_dxf: str
) -> None:
    """
    Export grid layout using existing plot_utils and dwg_utils.
    
    This is the main entry point that bridges grid layout to visualization.
    
    Args:
        placed: List of Placed objects from grid optimization
        paths: Dict of flow paths (currently unused, routing is direct)
        n: Grid size
        cell_mm: Millimeters per grid cell
        flows: List of (src_uid, dst_uid) flow tuples
        output_png: Output PNG file path
        output_dxf: Output DXF file path
    """
    from plot_utils import save_design_plot_png
    from dwg_utils import generate_dxf
    
    # Convert grid data to Room structure
    rooms = grid_to_rooms(placed, n, cell_mm)
    
    print(f"[*] Exporting layout with {len(rooms[0].machines)} machines and {len(flows)} flows")
    
    # Export PNG using plot_utils
    save_design_plot_png(
        rooms=rooms,
        flows=flows,
        find_machine_func=find_machine,
        routing_func=route_machines,
        out_png=output_png,
        use_processed_images=True  # Prefer background-removed images if available
    )
    
    # Export DXF using dwg_utils
    generate_dxf(
        rooms=rooms,
        flows=flows,
        find_machine_func=find_machine,
        routing_func=route_machines,
        out_dxf=output_dxf
    )
