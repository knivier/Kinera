#!/usr/bin/env python3
"""
2D GUI viewer: camera + skeleton overlay + text panel.
Builds entirely on cv.py.
"""
import argparse
import cv2
import numpy as np

from cv import (
    CAMERA_ID,
    PoseCore,
    build_text_panel,
    draw_skeleton,
    flip_landmarks_x,
    install_ctrl_c,
    ELBOW_ALERT_RED_ALPHA,
)

# Same layout for GUI and for MJPEG stream (cv_stream_server). Single source of truth for camera + skeleton preview.
TEXT_PANEL_WIDTH = 520


def create_view_core(camera_id=None):
    """Create PoseCore with cv-view config. Uses CAMERA_ID from config if camera_id is None."""
    if camera_id is None:
        camera_id = CAMERA_ID
    return PoseCore(camera_id=camera_id)


def produce_combined_frame(core):
    """Run one step: flip, skeleton overlay, text panel, hstack. Returns (combined BGR frame, True) or (None, False)."""
    data = core.step()
    if data is None:
        return None, False
    frame = data["frame"]
    frame = cv2.flip(frame, 1)
    lm_mirrored = flip_landmarks_x(data["landmarks"])
    draw_skeleton(frame, lm_mirrored, data["connection_spec"])
    if data.get("alert_red"):
        red = np.full_like(frame, (0, 0, 255))
        frame = cv2.addWeighted(frame, 1.0 - ELBOW_ALERT_RED_ALPHA, red, ELBOW_ALERT_RED_ALPHA, 0)
    win_height = core.height
    cam_display = cv2.resize(frame, (core.width, win_height))
    text_panel = build_text_panel(data["text_lines"], width=TEXT_PANEL_WIDTH, height=win_height)
    if text_panel.shape[0] != win_height:
        text_panel = cv2.resize(text_panel, (TEXT_PANEL_WIDTH, win_height))
    combined = np.hstack([cam_display, text_panel])
    return combined, True


def run_view(camera_id=None):
    """All options (including resolutions) come from cv.py config. Uses create_view_core + produce_combined_frame."""
    try:
        core = create_view_core(camera_id)
    except RuntimeError as exc:
        print(exc)
        return

    win_height = core.height
    win_width = core.width + TEXT_PANEL_WIDTH
    cv2.namedWindow("Skeleton Overlay", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Skeleton Overlay", win_width, win_height)

    exit_requested = False

    def _on_sigint(*_):
        nonlocal exit_requested
        exit_requested = True

    install_ctrl_c(_on_sigint)

    try:
        while not exit_requested:
            combined, cont = produce_combined_frame(core)
            if not cont:
                break
            cv2.imshow("Skeleton Overlay", combined)
            if cv2.waitKey(1) & 0xFF == 27:  # ESC
                break
    except KeyboardInterrupt:
        pass
    finally:
        core.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pose GUI (all options from cv.py / config.yaml).")
    parser.add_argument("--camera", type=int, default=CAMERA_ID, help="Camera device id (default from config.yaml)")
    args = parser.parse_args()
    run_view(camera_id=args.camera)
