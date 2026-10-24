"""
Module 2 layout, run locally.

Placement, annealing, conveyor routing and the PNG/DXF renderers need no
service. In production the flows come from Gemini and the machine pictures from
image generation; here the flows are given and machines have no images.
"""

import ezdxf
import pytest
from PIL import Image

from utils.module_2 import layout_engine
from utils.module_2.renderer import FactoryRenderer

MACHINES = [
    {"model": "Silo", "width": 3, "height": 3, "count": 1},
    {"model": "Extrudeuse", "width": 9, "height": 3, "count": 2},
    {"model": "Presse", "width": 4.5, "height": 3, "count": 1},
    {"model": "Robot", "width": 3, "height": 3, "count": 1},
]
FLOWS = [
    ("Silo", "Extrudeuse_1"),
    ("Silo", "Extrudeuse_2"),
    ("Extrudeuse_1", "Presse"),
    ("Extrudeuse_2", "Presse"),
    ("Presse", "Robot"),
]


@pytest.fixture(scope="module")
def layout():
    # Production annealing length: shorter runs can leave a flow unrouted
    return layout_engine.generate_layout(MACHINES, FLOWS, seed=7)


def test_machine_counts_expand_into_instances():
    uids = [uid for _, uid in layout_engine.expand_machines(MACHINES)]
    assert uids == ["Silo", "Extrudeuse_1", "Extrudeuse_2", "Presse", "Robot"]


def test_every_instance_is_placed_inside_the_grid_without_overlap(layout):
    layout_data, _ = layout
    n = layout_data["grid_size"]
    placed = layout_data["placed"]

    assert sorted(p["uid"] for p in placed) == sorted(["Silo", "Extrudeuse_1", "Extrudeuse_2", "Presse", "Robot"])
    for p in placed:
        assert 0 <= p["x"] and p["x"] + p["w"] <= n
        assert 0 <= p["y"] and p["y"] + p["h"] <= n
    layout_engine.rebuild_grid(n, placed)  # raises on overlap


def test_every_flow_is_routed(layout):
    _, paths = layout
    assert set(paths) == set(FLOWS)
    # Adjacent machines can share a port, so a route may be a single cell
    assert all(len(path) >= 1 for path in paths.values())


def test_png_and_dxf_are_written(layout, tmp_path):
    layout_data, paths = layout
    renderer = FactoryRenderer()

    png = tmp_path / "layout.png"
    dxf = tmp_path / "layout.dxf"
    renderer.render_png(layout_data, paths, None, str(png))
    renderer.render_dxf(layout_data, paths, str(dxf))

    with Image.open(png) as im:
        assert im.width >= 900
        # machines without images are drawn as grey footprints, not left invisible
        assert (217, 217, 217) in {c for _, c in im.convert("RGB").getcolors(maxcolors=1 << 20)}
    doc = ezdxf.readfile(str(dxf))
    assert len(doc.modelspace()) > 0
