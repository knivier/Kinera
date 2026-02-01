# Workout Tracker - Python Qt Application

Clean, minimal workout tracking app built with PySide6 and MediaPipe.

## Architecture

```
QMainWindow
└── QStackedWidget
    ├── WorkoutSelectPage  (no CV, fast load)
    └── LiveSessionPage     (CV thread, real-time tracking)
```

## Features

- **Two screens only**: Selection → Live tracking
- **Zero navigation complexity**: QStackedWidget handles page switching
- **CV runs in background thread**: Non-blocking UI
- **Real-time feedback**: Angle tracking, rep detection, form guidance
- **Exercise-specific rules**: Each workout has custom thresholds and targets

## File Structure

```
app/
├── main.py              # Entry point, QMainWindow, AppState
├── workout_select.py    # Workout selection screen
├── live_session.py      # Live tracking screen with video feed
├── cv_thread.py         # Background CV processing (QThread)
├── exercise_rules.py    # Exercise configs (angles, thresholds, feedback)
└── README.md           # This file
```

## State Management

```python
class AppState:
    workout: str | None = None
    running: bool = False
```

That's it. One global state object. No store, no reducers, no dispatch.

## Running the App

```bash
# Install dependencies
pip install -r requirements.txt

# Test camera first (optional but recommended)
cd app
python test_camera.py

# Run the app
python main.py

# Or use launcher
./run.sh
```

## Troubleshooting

### Camera Not Working?

Run the camera test utility:
```bash
python app/test_camera.py
```

Common fixes:
- Close other apps using camera (Chrome, Firefox, Zoom, Skype, etc.)
- Check camera permissions
- Try different camera: The app will auto-try indices 0, 1, 2
- Check available cameras: `ls -l /dev/video*`

### App Won't Start?

Make sure dependencies are installed:
```bash
pip install -r requirements.txt
```

Check for errors in terminal output.

## How It Works

### Workout Selection
1. User picks exercise from dropdown
2. Taps "Start Workout"
3. Signal emitted: `workout_selected.emit(workout_id)`
4. MainWindow switches to LiveSessionPage

### Live Session
1. CV thread starts on entry
2. MediaPipe processes camera frames
3. RepDetector tracks angles and counts reps
4. Frame + feedback emitted to UI thread via signals
5. User sees: video feed, current angle, rep count, feedback
6. Tap "End Workout" → CV thread stops → back to selection

### Rep Detection
- State machine in `RepTracker.SimpleRepDetector`
- Tracks min/max angle thresholds
- Emits rep when full ROM detected
- Exercise-specific rules define what counts

## Exercise Rules

Each exercise has:
- `joints`: Which joints to track (e.g., elbows for pushups)
- `min_threshold`: Bottom angle for rep
- `max_threshold`: Top angle for rep
- `target_range`: Good form range
- `get_feedback()`: Generate real-time text feedback

## Why This Design

**No routing**: QStackedWidget is simpler than any router

**No IPC**: Everything in one process

**No serialization**: Direct Python objects between threads via Qt signals

**No webview**: Native Qt widgets are faster and simpler

**One language**: Python all the way down

**One debugger**: Standard Python debugging tools work

## Extending

Add a new exercise:
1. Add entry to `EXERCISES` dict in `exercise_rules.py`
2. Define joints, thresholds, target range
3. Add to combo box in `workout_select.py`
4. Done.

No routing config. No API endpoints. Just data.
