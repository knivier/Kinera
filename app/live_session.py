"""
Live workout session screen.
Camera feed + real-time feedback + rep counting.
"""

import time
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QGridLayout
)
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QFont, QImage, QPixmap
import cv2
import numpy as np

from cv_thread import CVThread
from exercise_rules import get_exercise_rules


class LiveSessionPage(QWidget):
    """Live workout tracking page."""
    
    session_stopped = Signal()
    
    def __init__(self):
        super().__init__()
        
        # State
        self.workout_id = None
        self.rep_count = 0
        self.session_start_time = None
        self.is_running = False
        
        # CV thread
        self.cv_thread = CVThread()
        self.cv_thread.frame_ready.connect(self._on_frame_ready)
        self.cv_thread.rep_detected.connect(self._on_rep_detected)
        self.cv_thread.error_occurred.connect(self._on_error)
        
        # UI timer for elapsed time
        self.ui_timer = QTimer()
        self.ui_timer.timeout.connect(self._update_elapsed_time)
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Build the UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # Header
        header = QHBoxLayout()
        
        self.title_label = QLabel("Live Session")
        title_font = QFont()
        title_font.setPointSize(28)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        header.addWidget(self.title_label)
        
        header.addStretch()
        
        # Stop button in header
        self.stop_btn = QPushButton("End Workout")
        stop_font = QFont()
        stop_font.setPointSize(12)
        stop_font.setBold(True)
        self.stop_btn.setFont(stop_font)
        self.stop_btn.setMinimumWidth(150)
        self.stop_btn.setMinimumHeight(45)
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
            QPushButton:pressed {
                background-color: #b91c1c;
            }
        """)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        header.addWidget(self.stop_btn)
        
        layout.addLayout(header)
        
        # Main content area
        content = QHBoxLayout()
        content.setSpacing(20)
        
        # Left: Video feed
        video_container = QFrame()
        video_container.setStyleSheet("""
            QFrame {
                background-color: #1a1a1a;
                border: 1px solid #2d2d2d;
                border-radius: 12px;
            }
        """)
        video_layout = QVBoxLayout(video_container)
        video_layout.setContentsMargins(0, 0, 0, 0)
        
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(800, 600)
        self.video_label.setStyleSheet("background-color: #1a1a1a;")
        self.video_label.setText("Camera initializing...")
        video_layout.addWidget(self.video_label)
        
        content.addWidget(video_container, 2)
        
        # Right: Stats and feedback
        sidebar = QVBoxLayout()
        sidebar.setSpacing(15)
        
        # Rep counter card
        rep_card = self._create_card()
        rep_card_layout = QVBoxLayout(rep_card)
        
        rep_title = QLabel("Current Reps")
        rep_title_font = QFont()
        rep_title_font.setPointSize(12)
        rep_title_font.setBold(True)
        rep_title.setFont(rep_title_font)
        rep_card_layout.addWidget(rep_title)
        
        self.rep_label = QLabel("0")
        rep_font = QFont()
        rep_font.setPointSize(72)
        rep_font.setBold(True)
        self.rep_label.setFont(rep_font)
        self.rep_label.setAlignment(Qt.AlignCenter)
        self.rep_label.setStyleSheet("color: #10b981; padding: 20px;")
        rep_card_layout.addWidget(self.rep_label)
        
        sidebar.addWidget(rep_card)
        
        # Angle display card
        angle_card = self._create_card()
        angle_card_layout = QVBoxLayout(angle_card)
        
        angle_title = QLabel("Current Angle")
        angle_title_font = QFont()
        angle_title_font.setPointSize(12)
        angle_title_font.setBold(True)
        angle_title.setFont(angle_title_font)
        angle_card_layout.addWidget(angle_title)
        
        self.angle_label = QLabel("--°")
        angle_font = QFont()
        angle_font.setPointSize(48)
        angle_font.setBold(True)
        self.angle_label.setFont(angle_font)
        self.angle_label.setAlignment(Qt.AlignCenter)
        self.angle_label.setStyleSheet("color: #3b82f6; padding: 20px;")
        angle_card_layout.addWidget(self.angle_label)
        
        sidebar.addWidget(angle_card)
        
        # Feedback card
        feedback_card = self._create_card()
        feedback_card_layout = QVBoxLayout(feedback_card)
        
        feedback_title = QLabel("Form Feedback")
        feedback_title_font = QFont()
        feedback_title_font.setPointSize(12)
        feedback_title_font.setBold(True)
        feedback_title.setFont(feedback_title_font)
        feedback_card_layout.addWidget(feedback_title)
        
        self.feedback_label = QLabel("Start moving to get feedback")
        feedback_font = QFont()
        feedback_font.setPointSize(14)
        self.feedback_label.setFont(feedback_font)
        self.feedback_label.setWordWrap(True)
        self.feedback_label.setAlignment(Qt.AlignCenter)
        self.feedback_label.setStyleSheet("""
            color: #1f2937;
            padding: 20px;
            background-color: #f0fdf4;
            border: 2px solid #86efac;
            border-radius: 8px;
        """)
        feedback_card_layout.addWidget(self.feedback_label)
        
        sidebar.addWidget(feedback_card)
        
        # Elapsed time card
        time_card = self._create_card()
        time_card_layout = QVBoxLayout(time_card)
        
        time_title = QLabel("Elapsed Time")
        time_title_font = QFont()
        time_title_font.setPointSize(12)
        time_title_font.setBold(True)
        time_title.setFont(time_title_font)
        time_card_layout.addWidget(time_title)
        
        self.time_label = QLabel("00:00")
        time_font = QFont()
        time_font.setPointSize(32)
        time_font.setBold(True)
        self.time_label.setFont(time_font)
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet("color: #6b7280; padding: 10px;")
        time_card_layout.addWidget(self.time_label)
        
        sidebar.addWidget(time_card)
        
        sidebar.addStretch()
        
        content.addLayout(sidebar, 1)
        
        layout.addLayout(content)
        
        self.setLayout(layout)
        self.setStyleSheet("background-color: #f9fafb;")
        
    def _create_card(self) -> QFrame:
        """Create a styled card container."""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 12px;
                padding: 20px;
            }
        """)
        return card
        
    def start(self, workout_id: str):
        """Start the workout session."""
        self.workout_id = workout_id
        self.rep_count = 0
        self.session_start_time = time.time()
        self.is_running = True
        
        # Update UI
        rules = get_exercise_rules(workout_id)
        self.title_label.setText(f"Live Session - {rules.display_name}")
        self.rep_label.setText("0")
        self.angle_label.setText("--°")
        self.feedback_label.setText("Initializing camera...")
        
        # Start CV thread
        self.cv_thread.start_workout(workout_id)
        
        # Start UI timer
        self.ui_timer.start(100)  # Update every 100ms
        
    def stop(self):
        """Stop the workout session."""
        self.is_running = False
        
        # Stop timers
        self.ui_timer.stop()
        
        # Stop CV thread
        if self.cv_thread.isRunning():
            self.cv_thread.stop_workout()
        
        # Clear video
        self.video_label.clear()
        self.video_label.setText("Session ended")
        
    def _on_frame_ready(self, frame_data):
        """Handle new frame from CV thread."""
        if not self.is_running:
            return
            
        # Get frame
        frame = frame_data["frame"]
        current_angle = frame_data.get("current_angle")
        feedback = frame_data.get("feedback", "")
        
        # Convert frame to QPixmap
        height, width, channel = frame.shape
        bytes_per_line = 3 * width
        q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_BGR888)
        pixmap = QPixmap.fromImage(q_image)
        
        # Scale to fit video label
        scaled_pixmap = pixmap.scaled(
            self.video_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.video_label.setPixmap(scaled_pixmap)
        
        # Update angle
        if current_angle is not None:
            self.angle_label.setText(f"{current_angle:.1f}°")
        else:
            self.angle_label.setText("--°")
        
        # Update feedback
        self.feedback_label.setText(feedback)
        
    def _on_rep_detected(self, rep_summary):
        """Handle rep detection."""
        self.rep_count += 1
        self.rep_label.setText(str(self.rep_count))
        
        # Flash the rep label
        self.rep_label.setStyleSheet("color: #10b981; padding: 20px; background-color: #d1fae5;")
        QTimer.singleShot(300, lambda: self.rep_label.setStyleSheet("color: #10b981; padding: 20px;"))
        
    def _on_error(self, error_msg):
        """Handle CV error."""
        # Show error in feedback and video area
        self.feedback_label.setText(f"Error: {error_msg}")
        self.feedback_label.setStyleSheet("""
            color: #991b1b;
            padding: 20px;
            background-color: #fee2e2;
            border: 2px solid #fca5a5;
            border-radius: 8px;
        """)
        
        # Also show in video area
        self.video_label.setText(f"Camera Error\n\n{error_msg}")
        self.video_label.setStyleSheet("""
            background-color: #1a1a1a;
            color: #fca5a5;
            font-size: 14px;
            padding: 40px;
        """)
        
    def _update_elapsed_time(self):
        """Update elapsed time display."""
        if not self.is_running or self.session_start_time is None:
            return
            
        elapsed = time.time() - self.session_start_time
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        self.time_label.setText(f"{minutes:02d}:{seconds:02d}")
        
    def _on_stop_clicked(self):
        """Handle stop button click."""
        self.session_stopped.emit()
