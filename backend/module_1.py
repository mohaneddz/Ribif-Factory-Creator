from utils.module_1.core import *

if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="Input PDF/DOCX")
    ap.add_argument("--out_dir", dest="out_dir", default="data/extracted_data")
    ap.add_argument("--workers", dest="workers", type=int, default=7)
    ap.add_argument("--pages", dest="pages", type=int, default=4)
    ap.add_argument("--excerpt_chars", dest="excerpt_chars", type=int, default=18000)
    ap.add_argument("--timeout", dest="timeout", type=int, default=60)
    args = ap.parse_args()

    extractor = RIBIFExtractor()
    extractor.process_document(
        args.inp,
        output_dir=args.out_dir,
        max_workers=args.workers,
        max_pages_per_stage=args.pages,
        excerpt_chars=args.excerpt_chars,
        timeout_s=args.timeout,
    )
