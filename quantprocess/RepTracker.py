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
