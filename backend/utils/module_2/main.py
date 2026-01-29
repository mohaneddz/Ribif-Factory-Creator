"""
Main orchestration pipeline for factory layout generation.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Tuple

import requests

from config import (
    OUTPUT_DIR,
    OUTPUT_DXF,
    OUTPUT_PNG,
    REALISTIC_PNG,
    REALISTIC_CLEAN_PNG,
    FINAL_GLB_PATH,
    PUBLIC_MODELS_DIR,
    TOP_VIEW_REALISTIC_BELTS,
    MACHINE_PIPELINE_PROMPT,
    format_machine_list,
)
from ai_manager import (
    load_data,
    load_pipeline,
    normalize_flows,
    should_regenerate_links,
    expand_flows_to_instances,
    process_machine_images,
    generate_message,
    generate_image,
    remove_background,
    generate_3d_model,
)
from layout_engine import generate_layout
from renderer import FactoryRenderer
from log_utils import section, info, warn, error, success, kv


class PipelineAbort(RuntimeError):
    pass


def _ensure_dirs() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(PUBLIC_MODELS_DIR, exist_ok=True)


def _parse_pipeline_response(text: str) -> Dict[str, Any]:
    # Try to extract JSON payload even if wrapped in fences
    if "```" in text:
        # prefer ```json block
        if "```json" in text:
            body = text.split("```json", 1)[1].split("```", 1)[0]
        else:
            body = text.split("```", 1)[1].split("```", 1)[0]
    else:
        body = text
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise ValueError("Pipeline response is not valid JSON. Check model output or prompt.") from exc


def _build_flows(machines: List[Dict[str, Any]], links_path: str, force_regen: bool) -> List[Tuple[str, str]]:
    pipeline = None
    if should_regenerate_links(links_path, force_regen):
        m_list_str = format_machine_list(machines)
        prompt = MACHINE_PIPELINE_PROMPT.replace("{machines_list}", m_list_str)
        resp = generate_message(
            prompt=prompt,
            system_instruction="You are a factory systems engineer.",
        )
        pipeline = _parse_pipeline_response(resp)
        with open(links_path, "w", encoding="utf-8") as f:
            json.dump(pipeline, f, indent=2)
    else:
        pipeline = load_pipeline(links_path)

    if pipeline and "flows" in pipeline:
        model_flows = normalize_flows(pipeline["flows"])
        flows = expand_flows_to_instances(model_flows, machines)
        return flows

    # Fallback: linear chain
    expanded = []
    for m in machines:
        model = str(m.get("model") or m.get("name") or "Machine")
        count = int(m.get("count", 1) or 1)
        if count <= 1:
            expanded.append(model)
        else:
            for i in range(count):
                expanded.append(f"{model}_{i+1}")
    return [(expanded[i], expanded[i + 1]) for i in range(len(expanded) - 1)]


def _ask_stop_step() -> int:
    while True:
        section("Interactive Mode")
        info("Stop at which step?")
        info("1) After pipeline/flows")
        info("2) After layout generation")
        info("3) After base DXF+PNG export")
        info("4) After enhanced images (base + realistic)")
        info("5) After background removal (rembg)")
        info("6) After 3D model")
        choice = input("Choose (1-6): ").strip()
        if choice in ("1", "2", "3", "4", "5", "6"):
            return int(choice)


class Timer:
    def __init__(self) -> None:
        self.t0 = time.time()
        self.start_total = self.t0
        self.steps: List[Tuple[str, float]] = []

    def log(self, name: str) -> None:
        now = time.time()
        duration = now - self.t0
        self.steps.append((name, duration))
        info(f"Time: {name} = {duration:.2f}s")
        self.t0 = now

    def log_custom(self, name: str, duration: float) -> None:
        self.steps.append((name, duration))
        info(f"Time: {name} = {duration:.2f}s")

    def reset(self) -> None:
        self.t0 = time.time()

    def print_summary(self) -> None:
        section("Timing Summary")
        total = 0.0
        for name, duration in self.steps:
            info(f"{name:<30}: {duration:.2f}s")
            total += duration
        info("-" * 30)
        info(f"{'TOTAL':<30}: {total:.2f}s")
        wall = time.time() - self.start_total
        if wall > 0.01:
            info(f"{'WALL':<30}: {wall:.2f}s")
        if total > wall + 0.05:
            info("Note: some steps ran in parallel; TOTAL may exceed WALL.")


def _run_step(timer: Timer, title: str, fn):
    section(title)
    try:
        result = fn()
        timer.log(title)
        success("Done")
        return result
    except Exception as exc:
        error(f"{title} failed")
        kv("error_type", type(exc).__name__)
        kv("message", str(exc))
        raise PipelineAbort(str(exc)) from exc


def run_pipeline(
    data_path: str,
    links_path: str,
    seed: int,
    force_links: bool = False,
    stop_at: int | None = None,
) -> None:
    _ensure_dirs()
    timer = Timer()

    try:
        # 1) Load data
        machines = _run_step(timer, "Load data", lambda: load_data(data_path))

        # 2+3) Parallel: download/clean images and generate flows
        section("Parallel: images + flows")
        img_start = time.time()
        flows_start = time.time()
        executor = ThreadPoolExecutor(max_workers=2)
        img_future = executor.submit(process_machine_images, machines, None)
        flows_future = executor.submit(_build_flows, machines, links_path, force_links)

        try:
            try:
                flows = flows_future.result()
                timer.log_custom("Generate flows", time.time() - flows_start)
            except Exception as exc:
                error("Generate flows failed")
                kv("error_type", type(exc).__name__)
                kv("message", str(exc))
                raise PipelineAbort(str(exc)) from exc

            if stop_at == 1:
                img_future.result()
                timer.log_custom("Download + clean images", time.time() - img_start)
                info("Stopped after step 1")
                timer.print_summary()
                return

            # 4) Generate layout + routes
            timer.reset()
            layout_data, paths = _run_step(timer, "Generate layout + routes", lambda: generate_layout(machines, flows, seed=seed))

            if stop_at == 2:
                img_future.result()
                timer.log_custom("Download + clean images", time.time() - img_start)
                info("Stopped after step 2")
                timer.print_summary()
                return

            # 5) Render DXF
            renderer = FactoryRenderer()
            _run_step(timer, "Render DXF", lambda: renderer.render_dxf(layout_data, paths, OUTPUT_DXF))

            img_future.result()
            timer.log_custom("Download + clean images", time.time() - img_start)

            for placed in layout_data.get("placed", []):
                machine = placed.get("machine", {})
                if isinstance(machine, dict):
                    placed["img_path"] = (
                        machine.get("image_nobg_path") or machine.get("image_path") or machine.get("image")
                    )
        finally:
            executor.shutdown(wait=True)

        # 6) Render base PNG
        _run_step(timer, "Render base PNG", lambda: renderer.render_png(layout_data, paths, images_map=None, output_path=OUTPUT_PNG))

        if stop_at == 3:
            info("Stopped after step 3")
            timer.print_summary()
            return

        # 7) Gemini: realistic render
        def _render_realistic():
            with open(OUTPUT_PNG, "rb") as f:
                layout_bytes = f.read()
            images = generate_image(prompt=TOP_VIEW_REALISTIC_BELTS, images=[layout_bytes])
            if not images:
                raise RuntimeError("No image returned from image generation.")
            with open(REALISTIC_PNG, "wb") as f:
                f.write(images[0])
        _run_step(timer, "Gemini realistic render", _render_realistic)

        if stop_at == 4:
            info("Stopped after step 4")
            timer.print_summary()
            return

        # 8) Remove background
        def _bg_remove():
            with open(REALISTIC_PNG, "rb") as f:
                src = f.read()
            clean = remove_background(src)
            with open(REALISTIC_CLEAN_PNG, "wb") as f:
                f.write(clean)
        _run_step(timer, "Background removal", _bg_remove)

        if stop_at == 5:
            info("Stopped after step 5")
            timer.print_summary()
            return

        # 9) Replicate: 3D model
        def _gen_3d():
            result = generate_3d_model(REALISTIC_CLEAN_PNG)
            model_url = None
            if isinstance(result, dict):
                model_url = result.get("model_file")
            if not model_url and isinstance(result, str):
                model_url = result

            if not model_url:
                raise RuntimeError("3D generation output did not include model_file.")

            r = requests.get(model_url, timeout=120)
            r.raise_for_status()
            with open(FINAL_GLB_PATH, "wb") as f:
                f.write(r.content)
        _run_step(timer, "Replicate 3D + download", _gen_3d)

        success(f"Saved GLB: {FINAL_GLB_PATH}")
        timer.print_summary()

        if stop_at == 6:
            info("Stopped after step 6")
            return
    except PipelineAbort:
        warn("Pipeline stopped due to an error.")
        timer.print_summary()
        return


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data.json")
    ap.add_argument("--links", default=os.path.join(OUTPUT_DIR, "links.json"))
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--force-links", action="store_true", help="Force regenerate Gemini pipeline links")
    ap.add_argument("--i", "--interactive", action="store_true", help="Prompt for stop-at step")
    args = ap.parse_args()

    stop_at = _ask_stop_step() if args.i else None
    run_pipeline(args.data, args.links, seed=args.seed, force_links=args.force_links, stop_at=stop_at)


if __name__ == "__main__":
    main()
