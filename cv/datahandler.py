import json
import numpy as np
from scipy.signal import find_peaks
from scipy.interpolate import UnivariateSpline
from matplotlib import pyplot as plt
import torch
import torch.nn as nn
from time import sleep

WORKOUT_TO_PARAMETERS = {"pushups": {"min_threshold": 120, "max_threshold": 145, "joints": ("left_elbow", "right_elbow")}}
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
def to_fixed_length(points, target_len=50):
    points = np.asarray(points, dtype=float)

    if len(points) == 0:
        return np.zeros(target_len)

    x_old = np.linspace(0, 1, len(points))
    x_new = np.linspace(0, 1, target_len)

    return np.interp(x_new, x_old, points)

def workout_init():
    global detector
    with open("../workout_id.json", "r") as f:
        data = json.load(f)
        workout_type = data.get("workout_id", "pushups")
        detector = SimpleRepDetector(
            min_threshold=WORKOUT_TO_PARAMETERS[workout_type]["min_threshold"],
            max_threshold=WORKOUT_TO_PARAMETERS[workout_type]["max_threshold"],
            joints=WORKOUT_TO_PARAMETERS[workout_type]["joints"]
        )
        
detector = None
def run_workout(joint_angles, timestamp):
    global reps, detector
    if detector is None:
        workout_init()
    rep = detector.feed(joint_angles, timestamp)
    if rep is not None:
        print(rep)
        reps.append(rep)
        summary = rep_summary(rep)
        
        return summary
    return None
readLines = 0
def store_reps():
    global reps
    with open("pose_log.json", "r") as f:
        readingLine = 0
        for line in f:
            readingLine += 1
            if readingLine > readLines:
                summary = run_workout(json.loads(line).get("angles", {}), json.loads(line).get("timestamp_utc", 0))
                if summary is not None:
                    print(f"Rep detected: {summary}")
                readLines += 1
            
    with open("reps_summary.json", "w") as f:
        json.dump([rep_summary(rep) for rep in reps], f, indent=4)
while True:
    print("Checking workout_id.json...")
    with open("workout_id.jsonl", "r") as f:
        data = json.load(f)
        if data.get("workout_id", "pushups") == "OFF":
            print("Hey, workout is OFF. Sleeping...")
            sleep(0.1)
        else:
            print("Workout is ON. Processing...")
            store_reps()
            sleep(1)
        