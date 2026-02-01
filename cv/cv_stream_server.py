#!/usr/bin/env python3
"""
Serves cv-view (camera + skeleton + text panel) as MJPEG over HTTP.
Run from repo root: python cv/cv_stream_server.py
Then open in frontend: img src="http://localhost:8765/cv-stream"
"""
import argparse
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from threading import Thread

# Ensure cv package is importable (repo root) so "cv" is the package, not cv.py when CWD is cv/
from pathlib import Path
import importlib.util

_CV_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _CV_DIR.parent
sys.path.insert(0, str(_REPO_ROOT))

import cv2

# Explicitly use cv-view systems: same camera selection and skeleton preview pipeline.
from cv import CAMERA_ID

# Load cv_view from cv_view.py or cv-view.py so it works from any CWD (cv/ or repo root).
_cv_view_file = _CV_DIR / "cv_view.py" if (_CV_DIR / "cv_view.py").exists() else _CV_DIR / "cv-view.py"
_spec = importlib.util.spec_from_file_location("cv_view", _cv_view_file)
_cv_view = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cv_view)
create_view_core = _cv_view.create_view_core
produce_combined_frame = _cv_view.produce_combined_frame

HOST = "127.0.0.1"
PORT = 8765
MJPEG_BOUNDARY = b"frame"


class CVStreamHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # quiet

    def do_GET(self):
        if self.path != "/cv-stream":
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", f"multipart/x-mixed-replace; boundary={MJPEG_BOUNDARY.decode()}")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        try:
            while True:
                jpeg = self.server.get_latest_jpeg()
                if jpeg:
                    self.wfile.write(b"--" + MJPEG_BOUNDARY + b"\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\nContent-Length: %d\r\n\r\n" % len(jpeg))
                    self.wfile.write(jpeg)
                    self.wfile.write(b"\r\n")
                time.sleep(0.033)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()


class CVStreamServer(HTTPServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._latest_jpeg = None
        self._lock = threading.Lock()

    def set_latest_jpeg(self, data):
        with self._lock:
            self._latest_jpeg = data

    def get_latest_jpeg(self):
        with self._lock:
            return self._latest_jpeg


def run_cv_loop(server, camera_id):
    """Use cv-view systems: create_view_core (same camera selection) and produce_combined_frame (skeleton preview)."""
    try:
        core = create_view_core(camera_id)
    except RuntimeError as e:
        print("CV init failed:", e)
        print("Set camera_id in cv/config.yaml or run with: python cv/cv_stream_server.py --camera 1")
        return
    try:
        while True:
            combined, cont = produce_combined_frame(core)
            if not cont:
                break
            _, jpeg = cv2.imencode(".jpg", combined)
            server.set_latest_jpeg(jpeg.tobytes())
    finally:
        core.close()


def main():
    parser = argparse.ArgumentParser(description="Serve cv-view (skeleton + text) as MJPEG. Camera from cv/config.yaml, same as cv-view.py.")
    parser.add_argument("--camera", type=int, default=CAMERA_ID, help="Camera device id (default: from cv/config.yaml)")
    parser.add_argument("--port", type=int, default=PORT, help="HTTP port")
    args = parser.parse_args()
    camera_id = args.camera

    server = CVStreamServer((HOST, args.port), CVStreamHandler)
    t = Thread(target=run_cv_loop, args=(server, camera_id), daemon=True)
    t.start()
    print(f"CV stream at http://{HOST}:{args.port}/cv-stream (camera_id={camera_id} from config)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.shutdown()


if __name__ == "__main__":
    main()
