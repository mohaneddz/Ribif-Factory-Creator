"""
Simple HTTP server for running the EliteHack pipeline and returning outputs as a zip.
"""
from __future__ import annotations

import cgi
import io
import json
import os
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

try:
    from .config import (
        BASE_DIR,
        OUTPUT_DIR,
        OUTPUT_DXF,
        OUTPUT_PNG,
        REALISTIC_PNG,
        REALISTIC_CLEAN_PNG,
        FINAL_GLB_PATH,
        PUBLIC_MODELS_DIR,
    )
    from .main import run_pipeline
except ImportError:  # Fallback for running as a script.
    from config import (
        BASE_DIR,
        OUTPUT_DIR,
        OUTPUT_DXF,
        OUTPUT_PNG,
        REALISTIC_PNG,
        REALISTIC_CLEAN_PNG,
        FINAL_GLB_PATH,
        PUBLIC_MODELS_DIR,
    )
    from main import run_pipeline

DATA_PATH = os.path.join(BASE_DIR, "data.json")
LINKS_PATH = os.path.join(OUTPUT_DIR, "links.json")
PIPELINE_LOCK = threading.Lock()


def _bool_param(value: str) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes", "y", "on")


def _is_under(path: str, root: str) -> bool:
    try:
        return os.path.commonpath([os.path.abspath(path), os.path.abspath(root)]) == os.path.abspath(root)
    except ValueError:
        return False


def _arcname(path: str) -> str:
    if _is_under(path, OUTPUT_DIR):
        return os.path.join("output", os.path.basename(path))
    if _is_under(path, PUBLIC_MODELS_DIR):
        return os.path.join("models", os.path.basename(path))
    return os.path.basename(path)


def _expected_outputs() -> list[str]:
    return [
        OUTPUT_DXF,
        OUTPUT_PNG,
        REALISTIC_PNG,
        REALISTIC_CLEAN_PNG,
        LINKS_PATH,
        FINAL_GLB_PATH,
    ]


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/health"):
            payload = {
                "status": "ok",
                "endpoints": {
                    "POST /": "Run pipeline (send JSON body or multipart data.json)",
                    "POST /generate": "Same as /",
                },
            }
            self._send_json(200, payload)
            return
        self._send_json(404, {"error": "Not found"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path not in ("/", "/generate"):
            self._send_json(404, {"error": "Not found"})
            return

        if not PIPELINE_LOCK.acquire(blocking=False):
            self._send_json(429, {"error": "Pipeline busy. Try again shortly."})
            return

        try:
            data = self._parse_request_json()
            if not isinstance(data, (dict, list)):
                raise ValueError("data.json must be a JSON object or array.")

            with open(DATA_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            qs = parse_qs(parsed.query or "")
            seed_raw = (qs.get("seed") or ["7"])[0]
            force_raw = (qs.get("force_links") or qs.get("force-links") or ["0"])[0]
            try:
                seed = int(seed_raw)
            except ValueError:
                seed = 7
            force_links = _bool_param(force_raw)

            run_pipeline(DATA_PATH, LINKS_PATH, seed=seed, force_links=force_links, stop_at=None)

            outputs = _expected_outputs()
            missing = [p for p in outputs if not os.path.exists(p)]
            if missing:
                self._send_json(
                    500,
                    {
                        "error": "Pipeline finished but some outputs are missing.",
                        "missing": [os.path.basename(p) for p in missing],
                    },
                )
                return

            zip_bytes = self._build_zip(outputs)
            self._send_zip(zip_bytes, filename="elitehack_outputs.zip")
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})
        finally:
            PIPELINE_LOCK.release()

    def _read_body(self) -> bytes:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0:
            return b""
        return self.rfile.read(length)

    def _parse_request_json(self):
        ctype = self.headers.get("Content-Type", "")
        if "multipart/form-data" in ctype:
            environ = {
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": ctype,
                "CONTENT_LENGTH": self.headers.get("Content-Length", "0"),
            }
            fs = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ=environ)
            item = None
            if "data" in fs:
                item = fs["data"]
            elif "file" in fs:
                item = fs["file"]
            else:
                for part in fs.list or []:
                    if getattr(part, "filename", "") == "data.json":
                        item = part
                        break

            if item is None:
                raise ValueError("Missing data.json in multipart form.")

            if getattr(item, "file", None):
                raw = item.file.read()
            else:
                raw = str(item.value).encode("utf-8")
            return json.loads(raw.decode("utf-8"))

        raw = self._read_body()
        if not raw:
            raise ValueError("Empty request body.")
        return json.loads(raw.decode("utf-8"))

    def _build_zip(self, paths: list[str]) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in paths:
                if os.path.exists(path):
                    zf.write(path, arcname=_arcname(path))
        return buf.getvalue()

    def _send_json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_zip(self, body: bytes, filename: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        # Quiet default logging; uncomment if you need verbose logs.
        return


def run(host: str = "0.0.0.0", port: int = 6767) -> None:
    os.chdir(BASE_DIR)
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"Listening on http://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    run()
