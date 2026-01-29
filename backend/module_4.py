from utils.module_4.core import *

if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Path to module_1.json (extraction)")
    ap.add_argument("--output", default="data/extracted_data/module_4.json", help="Output JSON path")
    ap.add_argument("--workers", type=int, default=DEFAULT_MAX_WORKERS, help="Parallel workers")
    ap.add_argument("--timeout", type=int, default=DEFAULT_PER_MACHINE_TIMEOUT_S, help="Per-machine timeout (seconds)")
    ap.add_argument("--domain_gap", type=float, default=DEFAULT_DOMAIN_GAP_S, help="Min delay between requests per domain")
    ap.add_argument("--llm_timeout", type=int, default=DEFAULT_LLM_CALL_TIMEOUT_S, help="Hard timeout per LLM call (seconds)")
    ap.add_argument("--budget", type=int, default=DEFAULT_TOTAL_MACHINE_BUDGET_S, help="Total per-item budget seconds (give up after)")
    ap.add_argument("--images_dir", default=DEFAULT_GENERATED_IMAGES_DIR, help="Dir to save Nano Banana best images")
    args = ap.parse_args()

    build_machines_enriched(
        input_path=args.input,
        output_path=args.output,
        max_workers=args.workers,
        per_machine_timeout_s=args.timeout,
        domain_gap_s=args.domain_gap,
        llm_call_timeout_s=args.llm_timeout,
        total_machine_budget_s=args.budget,
        generated_images_dir=args.images_dir,
    )
