import os
import time
import argparse
import base64
import requests
import shutil
from concurrent.futures import ThreadPoolExecutor

from config import OUTPUT_DIR, OUTPUT_DXF, OUTPUT_PNG
from io_utils import load_data, load_pipeline, normalize_flows, should_regenerate_links, expand_flows_to_instances
from placement import expand_machines, compute_grid_size, place_all
from optimization import local_improve, rebuild_grid
from routing import ripup_reroute
from layout_bridge import export_layout_with_existing_utils

from vertex_utils import generate_image, remove_background, generate_3d, generate_message
from prompts import (
    TOP_VIEW_PROMPT_1,
    TOP_VIEW_PROMPT_2,
    TOP_VIEW_TILTED_PROMPT
)

class Timer:
    def __init__(self):
        self.t0 = time.time()
        self.steps = []

    def log(self, name):
        now = time.time()
        duration = now - self.t0
        self.steps.append((name, duration))
        print(f"[{name}] took {duration:.2f}s")
        self.t0 = now

    def print_summary(self):
        print("\n" + "="*30)
        print("TIMING SUMMARY")
        print("="*30)
        total = 0
        for name, duration in self.steps:
            print(f"{name:<30}: {duration:.2f}s")
            total += duration
        print("-" * 30)
        print(f"{'TOTAL':<30}: {total:.2f}s")
        print("="*30)

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def main():
    # Get the script's directory for relative paths
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    
    ap = argparse.ArgumentParser(description="Factory Grid Layout Generator")
    ap.add_argument("--data", default=os.path.join(SCRIPT_DIR, "data.json"), help="path to data.json")
    ap.add_argument("--links", default=os.path.join(OUTPUT_DIR, "links.json"), help="path to links.json")
    ap.add_argument("--seed", type=int, default=7, help="random seed")
    ap.add_argument("--i", action="store_true", help="interactive mode - choose where to stop")
    ap.add_argument("--regen_links", action="store_true", help="force regeneration of links.json via LLM")
    args = ap.parse_args()

    # Interactive mode
    stop_point = 4  # default: full run
    
    # Check if run with --i flag for interactive mode
    if args.i:
        print("\n" + "=" * 60)
        print("Interactive Mode - Choose where to stop:")
        print("=" * 60)
        print("  1) DXF + PNG plots only (layout packing finished)")
        print("  2) AI enhanced renders generated (raw renders: Phase 1 -> Phase 2/3)")
        print("  3) Background-removed AI renders (clean via rembg/chroma)")
        print("  4) Full run including 3D model generation (.glb)")
        print("=" * 60)
        try:
            choice = input("\nEnter choice (1-4): ").strip()
            if choice in {"1", "2", "3", "4"}:
                stop_point = int(choice)
            else:
                print("Invalid choice, using default (4)")
        except Exception:
            print("Invalid input, using default (4)")
        print()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    clean_dir = os.path.join(OUTPUT_DIR, "clean")
    os.makedirs(clean_dir, exist_ok=True)

    timer = Timer()

    print("=" * 60)
    print("Factory Grid Layout Generator - 1:1 Square")
    print("=" * 60)

    # Load data
    print("\n[*] Loading data...")
    machines = load_data(args.data)
    
    # Remove backgrounds from machine images FIRST
    print("\n[*] Processing machine images (removing backgrounds)...")
    from image_processor import remove_all_machine_backgrounds
    nobg_map = remove_all_machine_backgrounds(machines)
    print(f"[+] Processed {len(nobg_map)} machine images")
    
    expanded = expand_machines(machines)
    print(f"[+] Loaded {len(machines)} machine types ({len(expanded)} instances)")
    
    # Load or generate pipeline
    links_path = args.links
    # Try root if default output path doesn't exist
    if not os.path.exists(links_path) and os.path.exists("links.json"):
        links_path = "links.json"
    
    # Check if we need to regenerate links
    if should_regenerate_links(links_path, args.regen_links):
        print("[*] Generating pipeline via LLM...")
        try:
            from prompts import MACHINE_PIPELINE_PROMPT, format_machine_list
            import json

            # Use original machine types for planning (not expanded)
            m_list_str = format_machine_list(machines)
            prompt = MACHINE_PIPELINE_PROMPT.format(machines_list=m_list_str)

            # Use vertex_utils.generate_message (Gemini) instead of utils.ask_llm_json
            resp_text = generate_message(prompt=prompt, system_instruction="You are a factory systems engineer.")

            # Try to extract JSON from code fences if present
            if "```json" in resp_text:
                start = resp_text.find("```json") + 7
                end = resp_text.find("```", start)
                body = resp_text[start:end].strip()
            elif "```" in resp_text:
                start = resp_text.find("```") + 3
                end = resp_text.find("```", start)
                body = resp_text[start:end].strip()
            else:
                body = resp_text

            pipeline = json.loads(body)

            # Save it for future use - preferably in root
            save_path = "links.json"
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(pipeline, f, indent=2)
            print(f"[+] Generated and saved pipeline to {save_path}")

        except Exception as e:
            print(f"[!] Pipeline generation failed: {e}")
            pipeline = None
    else:
        print(f"[*] Reading pipeline from: {links_path}")
        pipeline = load_pipeline(links_path)

    # Extract and normalize flows at MODEL level
    if pipeline and "flows" in pipeline:
        model_flows = normalize_flows(pipeline["flows"])
        print(f"[+] Loaded {len(model_flows)} model-level flows from pipeline")
        
        # EXPAND model-level flows to instance-level flows
        flows = expand_flows_to_instances(model_flows, machines)
        print(f"[+] Expanded to {len(flows)} instance-level flows")
    else:
        # sequential fallback at instance level
        ids = [uid for _, uid in expanded]
        flows = [(ids[i], ids[i+1]) for i in range(len(ids)-1)]
        print(f"[!] Falling back to sequential flows ({len(flows)})")

    # Ensure all flow endpoints exist
    ids_set = {uid for _, uid in expanded}
    flows = [(a,b) for (a,b) in flows if a in ids_set and b in ids_set]
    print(f"[+] Final flows after validation: {len(flows)}")

    # Compute grid size
    n = compute_grid_size(expanded)
    print(f"\n[*] Grid size: {n}x{n} cells (cell size: {1.5}m)")

    # Placement
    print("\n[*] Placing machines...")
    grid, placed = place_all(expanded, flows, n, seed=args.seed)
    timer.log("Placement")

    # Optimization
    print("\n[*] Optimizing layout...")
    best, best_res, best_paths = local_improve(placed, flows, n, seed=args.seed + 1)
    timer.log("Optimization")

    # Final routing
    print("\n[*] Final routing...")
    grid_final = rebuild_grid(n, best)
    res_final, paths_final = ripup_reroute(grid_final, best, flows)
    print(f"[+] Routed flows: {len(paths_final)}/{len(flows)}")
    timer.log("Routing")

    # Export using existing utilities via bridge
    print("\n[*] Exporting Initial Layout (DXF + PNG)...")
    from config import CELL_MM
    export_layout_with_existing_utils(
        placed=best,
        paths=paths_final,
        n=n,
        cell_mm=CELL_MM,
        flows=flows,
        output_png=OUTPUT_PNG,
        output_dxf=OUTPUT_DXF
    )
    timer.log("Export Layout")

    if stop_point == 1:
        print("\n[STOP] Stopped after layout export (1).")
        timer.print_summary()
        return

    # Phase 1: AI Topology
    print("\n[*] Generating Phase 1: Machine Topology...")
    
    # Read the layout PNG
    try:
        layout_b64 = encode_image(OUTPUT_PNG)
        
        # Generate Phase 1
        p1_bytes_list = generate_image(prompt=TOP_VIEW_PROMPT_1, images=[layout_b64], candidate_count=1)
        if not p1_bytes_list:
             raise Exception("Phase 1 generation failed - no images returned.")
        p1_bytes = p1_bytes_list[0]
        
        p1_path = os.path.join(OUTPUT_DIR, "phase1_topology.png")
        with open(p1_path, "wb") as f:
            f.write(p1_bytes)
        print(f"[+] Saved {p1_path}")
        timer.log("AI Phase 1 (Topology)")
        
    except Exception as e:
        print(f"[!] Error in Phase 1: {e}")
        return

    # Phase 2 & 3: Parallel Execution
    print("\n[*] Generating Phase 2 (Realistic) & Phase 3 (Tilted) in PARALLEL...")
    
    if stop_point >= 2:
        try:
            p1_b64 = encode_image(p1_path)
            
            with ThreadPoolExecutor(max_workers=2) as executor:
                # Launch both tasks
                f2 = executor.submit(generate_image, TOP_VIEW_PROMPT_2, [p1_b64], 1)
                f3 = executor.submit(generate_image, TOP_VIEW_TILTED_PROMPT, [p1_b64], 1)
                
                # Wait for results
                p2_bytes_list = f2.result()
                p3_bytes_list = f3.result()
            
            if not p2_bytes_list or not p3_bytes_list:
                raise Exception("Phase 2 or 3 generation failed.")
                
            p2_bytes = p2_bytes_list[0]
            p3_bytes = p3_bytes_list[0]
            
            p2_path = os.path.join(OUTPUT_DIR, "phase2_realistic.png")
            p3_path = os.path.join(OUTPUT_DIR, "phase3_tilted.png")
            
            with open(p2_path, "wb") as f:
                f.write(p2_bytes)
            with open(p3_path, "wb") as f:
                f.write(p3_bytes)
                
            print(f"[+] Saved {p2_path}")
            print(f"[+] Saved {p3_path}")
            timer.log("AI Phase 2 & 3 (Parallel)")
            
        except Exception as e:
            print(f"[!] Error in Phase 2/3: {e}")
            return

    if stop_point == 2:
        print("\n[STOP] Stopped after AI renders (2).")
        timer.print_summary()
        return

    # Clean backgrounds
    print("\n[*] Processing Background Removal...")
    
    p2_clean_path = os.path.join(clean_dir, "phase2_clean.png")
    p3_clean_path = os.path.join(clean_dir, "phase3_clean.png")

    try:
        # Load raw bytes again from file to safely pass to clean
        # Or just use the bytes we have in p2_bytes/p3_bytes if they are in scope
        # Let's read afresh to be safe in case of restart or logic flow changes
        with open(p2_path, "rb") as f:
            p2_bytes_in = f.read()
        with open(p3_path, "rb") as f:
            p3_bytes_in = f.read()
            
        with ThreadPoolExecutor(max_workers=2) as executor:
            c2_future = executor.submit(remove_background, p2_bytes_in)
            c3_future = executor.submit(remove_background, p3_bytes_in)
            
            p2_clean = c2_future.result()
            p3_clean = c3_future.result()
            
        with open(p2_clean_path, "wb") as f:
            f.write(p2_clean)
        with open(p3_clean_path, "wb") as f:
            f.write(p3_clean)

        print(f"[+] Saved Clean Images to {clean_dir}")
        timer.log("Background Removal")

    except Exception as e:
        print(f"[!] Error in Background Removal: {e}")
        return

    if stop_point == 3:
        print("\n[STOP] Stopped after background removal (3).")
        timer.print_summary()
        return

    # Generate 3D
    print("\n[*] Generating 3D Model (GLB)...")
    output_glb = os.path.join(OUTPUT_DIR, "factory_model.glb")
    
    try:
        # We need open file handles for the generate_3d call (replicate wrapper expectation)
        with open(p2_clean_path, "rb") as f2_clean, open(p3_clean_path, "rb") as f3_clean:
            # Replicate python client handles file objects
            result = generate_3d(images=[f2_clean, f3_clean])
            
        model_url = result.get("model_file") if isinstance(result, dict) else None
        
        if not model_url:
             print("[!] No model_file url returned.")
             print("Result:", result)
        else:
            print(f"[+] Downloading model from {model_url}...")
            r = requests.get(model_url, timeout=120)
            r.raise_for_status()
            with open(output_glb, "wb") as f:
                f.write(r.content)
            print(f"[+] Saved {output_glb}")
            
        timer.log("3D Generation")

    except Exception as e:
         print(f"[!] Error in 3D Generation: {e}")
         import traceback
         traceback.print_exc()

    print("\n" + "=" * 60)
    print("[SUCCESS] Full Layout & Asset Generation Complete!")
    print("=" * 60)
    timer.print_summary()

if __name__ == "__main__":
    main()
