#!/usr/bin/env python3
"""
2D GUI viewer: camera + skeleton overlay + text panel.
Builds entirely on cv.py.
"""
import argparse
import cv2
import numpy as np
# from RepTracker import SimpleRepDetector
class SimpleRepDetector:
    WAITING_TOP = 0
    DESCENDING = 1
    BOTTOM_REACHED = 2
    ASCENDING = 3

    def __init__(self, min_threshold, max_threshold, joints):
        self.min_threshold = min_threshold
        self.max_threshold = max_threshold
        self.joints = joints

        self.state = self.WAITING_TOP
        self.prev_angle = None
        self.current_rep = []

    def _get_angle(self, joint_angles):
        a = joint_angles.get(self.joints[0])
        b = joint_angles.get(self.joints[1])
        if a is None or b is None:
            return None
        return (a + b) / 2.0

    def feed(self, joint_angles, timestamp):
        angle = self._get_angle(joint_angles)
        if angle is None:
            return None

        if self.prev_angle is None:
            self.prev_angle = angle
            return None

        decreasing = angle < self.prev_angle
        increasing = angle > self.prev_angle

        # -------------------------
        # STATE MACHINE
        # -------------------------
        if self.state == self.WAITING_TOP:
            if angle >= self.max_threshold:
                self.state = self.DESCENDING
                self.current_rep = [{"angle": angle, "timestamp": timestamp}]

        elif self.state == self.DESCENDING:
            self.current_rep.append({"angle": angle, "timestamp": timestamp})
            if angle <= self.min_threshold:
                self.state = self.BOTTOM_REACHED

        elif self.state == self.BOTTOM_REACHED:
            self.current_rep.append({"angle": angle, "timestamp": timestamp})
            if increasing:
                self.state = self.ASCENDING

        elif self.state == self.ASCENDING:
            self.current_rep.append({"angle": angle, "timestamp": timestamp})
            if angle >= self.max_threshold:
                rep = self.current_rep
                self.current_rep = []
                self.state = self.DESCENDING  # allow next rep immediately
                self.prev_angle = angle
                return rep  # full rep collected

        self.prev_angle = angle
        return None

from cv import (
    PoseCore,
    build_text_panel,
    draw_skeleton,
    flip_landmarks_x,
    install_ctrl_c,
    ELBOW_ALERT_RED_ALPHA,
)

detector = SimpleRepDetector(
    min_threshold=120,
    max_threshold=145,
    joints=("left_elbow", "right_elbow")
)

rep_indexes = []

def rep_summary(rep):
    angles = [p["angle"] for p in rep]
    times = [p["timestamp"] for p in rep]

    min_angle = min(angles)
    max_angle = max(angles)
    duration = (times[-1] - times[0]) / 1000.0  # seconds
    range_of_motion = max_angle - min_angle

    return {
        "min_angle": min_angle,
        "max_angle": max_angle,
        "duration": duration,
        "range_of_motion": range_of_motion,
        "num_frames": len(rep)
    }

reps = []

def run_view(camera_id=0):
    """All options (including resolutions) come from cv.py config."""
    try:
        core = PoseCore(camera_id=camera_id)
    except RuntimeError as exc:
        print(exc)
        return

    TEXT_PANEL_WIDTH = 520
    WIN_HEIGHT = core.height
    WIN_WIDTH = core.width + TEXT_PANEL_WIDTH
    cv2.namedWindow("Skeleton Overlay", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Skeleton Overlay", WIN_WIDTH, WIN_HEIGHT)

    exit_requested = False

    def _on_sigint(*_):
        nonlocal exit_requested
        exit_requested = True

    install_ctrl_c(_on_sigint)

    try:
        while not exit_requested:
            data = core.step()
            if data is None:
                break

            frame = data["frame"]
            frame = cv2.flip(frame, 1)  # mirror view so it looks natural to the user
            lm_mirrored = flip_landmarks_x(data["landmarks"])  # align skeleton with mirrored frame
            draw_skeleton(frame, lm_mirrored, data["connection_spec"])
            if data.get("alert_red"):
                red = np.full_like(frame, (0, 0, 255))
                frame = cv2.addWeighted(frame, 1.0 - ELBOW_ALERT_RED_ALPHA, red, ELBOW_ALERT_RED_ALPHA, 0)

            cam_display = cv2.resize(frame, (core.width, WIN_HEIGHT))
            text_panel = build_text_panel(data["text_lines"], width=TEXT_PANEL_WIDTH, height=WIN_HEIGHT)
            if (data.get("frame_json") is not None):
                rep = detector.feed(data.get("frame_json")["angles"], data.get("frame_json")["timestamp_utc"])
                if rep is not None:
                    summary = rep_summary(rep)
                    print("Rep detected:", summary)
                    reps.append(rep)
            if text_panel.shape[0] != WIN_HEIGHT:
                text_panel = cv2.resize(text_panel, (TEXT_PANEL_WIDTH, WIN_HEIGHT))
            combined = np.hstack([cam_display, text_panel])
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
    parser.add_argument("--camera", type=int, default=0, help="Camera device id")
    args = parser.parse_args()
    run_view(camera_id=args.camera)
