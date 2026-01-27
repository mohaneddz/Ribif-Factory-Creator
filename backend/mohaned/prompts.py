# =========================
# IMAGE GENERATION PROMPTS
# =========================

# PHASE 1: Topology enforcement ONLY (no realism upgrade)
TOP_VIEW_PROMPT_1 = """
INPUT: A factory layout image on solid chroma green (#00FF00).

TASK (PHASE 1 = TOPOLOGY ONLY):
Fix connectivity by turning every drawn link into a conveyor that follows the SAME path.
Keep every machine in the SAME position. you can scale up machines a bit so they fit the conveyor path, or add extensions to link them.

- Replace drawn lines/links with conveyors (belt or roller) that follow the exact same paths.
- Ensure conveyor ends touch machine edges (infeed/outfeed) with NO gaps, you can update the machines to link their infeed/outfeed to the conveyor. 
- If a connection is unclear, use the closest plausible machine edge, but DO NOT move the machine.
- Do NOT add new objects, arrows, text, or icons.
- Perfect 90° top-down, orthographic.
- Keep background EXACTLY #00FF00, flat, no gradients.
- NO shadows or AO on the green background.
- Only allow subtle self-shading on the conveyors themselves.

MUST KEEP (locked):
- Machine count: unchanged.
- Layout geometry: unchanged (no shifting, scaling, mirroring, or re-spacing).

OUTPUT:
One top-down image with identical layout, but conveyors are real and fully connected.
""".strip()


# PHASE 2: Material/detail upgrade ONLY (no geometry change)
TOP_VIEW_PROMPT_2 = """
INPUT: The PHASE-1 output image on solid chroma green (#00FF00).

TASK (PHASE 2 = APPEARANCE ONLY):
Upgrade machines and conveyors to ultra-realistic 3D industrial look WITHOUT changing geometry.

LOCKED (must not change):
- Positions identical.
- Conveyor paths identical.
- No adding/removing machines.

DO:
- Upgrade materials and surface detail only (stainless steel, painted frames, motors, guards, rollers).
- You can increase the size of the machines a bit to fit the conveyor path or look clearer.
- Add small details INSIDE existing silhouettes (panels, rails, fasteners), without changing outline.

DO NOT:
- Do NOT move, resize, rotate, mirror, or reroute anything.
- Do NOT add bases/platforms/pads/floors.
- Do NOT add text, labels, branding, decals.

CAMERA:
- Perfect 90° top-down. Orthographic or near-orthographic with minimal perspective.

BACKGROUND + SHADOWS (critical):
- Background must remain EXACTLY #00FF00, flat, no gradients.
- Absolutely NO shadows/AO/vignette on the green background.
- Apply internal/self shading on machines and conveyors ONLY.

OUTPUT:
One ultra-realistic top-down render with the exact same geometry, on pure green.
""".strip()


# PHASE 3: Tilted view (add height perception, keep XY locked)
TOP_VIEW_TILTED_PROMPT = """
INPUT: The PHASE-2 (or PHASE-1) layout image on solid chroma green (#00FF00).

TASK (PHASE 3 = TILT VIEW, XY LOCKED):
Create a slightly tilted high-angle view that shows 3D volume while keeping the layout geometry.

LOCKED (must not change):
- XY positions, spacing, and conveyor routing: identical to input.
- Machine count and stage order: unchanged.
- No new machines, no removed machines.

DO:
- Add realistic height/volume and perspective from a high angle.
- Preserve the same connectivity and relative placement.

DO NOT:
- Do NOT rearrange, reroute, or re-space.
- Do NOT add floors, studio backgrounds, bases, or platforms.
- Do NOT add text/labels/branding.

CAMERA:
- High-angle tilt ~75° from horizontal (mostly top-down), mild natural perspective.

BACKGROUND + SHADOWS (critical):
- Background must remain EXACTLY #00FF00, flat, no gradients.
- NO shadows/AO on the green background.
- Only object self-shading is allowed.

OUTPUT:
One tilted photoreal render with identical topology and pure green background.
""".strip()


# =========================
# MACHINE FILTERING PROMPTS
# =========================

MACHINE_FILTER_PROMPT = """
TASK: Decide if the item is a real production MACHINE (equipment) or NOT.

ITEM:
- Name: {machine_name}
- Model: {machine_model}
- Description: {machine_use}

MACHINE if it:
- Processes product/material (mold, fill, seal, cut, label, pack, palletize)
- Moves/transports (conveyor, elevator, feeder, sorter)
- Inspects/tests (vision, QC)
- Marks product (printer/coder)

NOT a machine if it is:
- Raw material (preforms, caps, labels, film rolls, cartons, pallets)
- Consumables (ink, glue, adhesive)
- Software/digital-only tools
- Storage/furniture/accessories/hand tools
- Finished goods

OUTPUT JSON ONLY:
If machine:
{{
  "is_machine": true,
  "confidence": "high|medium|low",
  "reasoning": "short reason"
}}

If not machine:
{{
  "is_machine": false,
  "confidence": "high|medium|low",
  "reasoning": "short reason",
  "item_type": "material|consumable|software|storage|other"
}}
""".strip()


# =========================
# PIPELINE ANALYSIS PROMPTS
# =========================

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
- width_m: conveyor width in meters (typical 0.6–1.0)

OUTPUT JSON ONLY:
{{
  "groups": [
    {{ "name": "Group Name", "machines": ["MachineID1", "MachineID2"], "purpose": "short purpose" }}
  ],
  "flows": [
    {{ "from": "MachineID", "to": "MachineID", "type": "conveyor", "material": "what moves", "width_m": 0.8 }}
  ],
  "layout_suggestion": {{ "arrangement": "linear|u_shape|parallel", "reasoning": "short reason" }}
}}
""".strip()


MACHINE_CLASSIFICATION_PROMPT = """
Classify this machine in a production pipeline.

MACHINE: {machine_name}
MODEL: {machine_model}
USE: {machine_use}

OUTPUT JSON ONLY:
{{
  "machine": "{machine_name}",
  "stage": "short stage name",
  "inputs": [],
  "outputs": [],
  "typical_upstream": [],
  "typical_downstream": []
}}
""".strip()


# =========================
# LAYOUT OPTIMIZATION PROMPTS
# =========================

LAYOUT_OPTIMIZATION_PROMPT = """
Optimize this factory layout into areas/rooms.

MACHINES (JSON):
{machines_json}

FLOWS (JSON):
{flows_json}

OUTPUT JSON ONLY:
{{
  "rooms": [
    {{
      "name": "Area",
      "machines": ["MachineID1", "MachineID2"],
      "suggested_dimensions_m": {{ "width": 20, "height": 15 }}
    }}
  ],
  "layout_notes": "short notes",
  "estimated_total_area_m2": 500
}}
""".strip()


# =========================
# 3D ASSET GENERATION PROMPTS
# =========================

MACHINE_3D_PROMPT = """
Generate a realistic industrial 3D machine model.

MACHINE: {machine_name}
TYPE/ROLE: {machine_use}
FOOTPRINT: {width}m x {height}m
ESTIMATED HEIGHT: {estimated_height}m

OUTPUT:
- GLB
- clean topology
- PBR materials
- no branding/text
""".strip()


CONVEYOR_3D_PROMPT = """
Generate a modular industrial conveyor section.

LENGTH: {length}m
WIDTH: {width}m

OUTPUT:
- GLB
- modular segments
- PBR materials
""".strip()


# =========================
# VALIDATION PROMPTS
# =========================

PIPELINE_VALIDATION_PROMPT = """
Validate this factory pipeline JSON.

PIPELINE:
{pipeline_json}

Return JSON ONLY:
{{
  "valid": true,
  "errors": [],
  "warnings": [],
  "suggestions": []
}}
""".strip()


# =========================
# HELPER FUNCTIONS
# =========================

def format_machine_list(machines):
    lines = []
    for m in machines:
        c = getattr(m, "count", 1)
        if c == 1:
            lines.append(
                f"- {m.name} (ID: {m.model}): {m.use} | Size: {m.width}m x {m.height}m"
            )
        else:
            for i in range(c):
                uid = f"{m.model}_{i+1}"
                lines.append(
                    f"- {m.name} #{i+1} (ID: {uid}): {m.use} | Size: {m.width}m x {m.height}m"
                )
    return "\\n".join(lines)


def format_flows_list(flows):
    out = []
    for f in flows:
        if isinstance(f, (tuple, list)) and len(f) >= 2:
            out.append(f"- {f[0]} -> {f[1]}")
        elif isinstance(f, dict) and "from" in f and "to" in f:
            out.append(f"- {f['from']} -> {f['to']}")
        else:
            out.append(f"- {str(f)}")
    return "\\n".join(out)


def create_machine_prompt(template, machine, **kwargs):
    return template.format(
        machine_name=getattr(machine, "name", ""),
        machine_model=getattr(machine, "model", ""),
        machine_use=getattr(machine, "use", ""),
        width=getattr(machine, "width", ""),
        height=getattr(machine, "height", ""),
        **kwargs
    )
