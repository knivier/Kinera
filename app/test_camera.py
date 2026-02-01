#!/usr/bin/env python3
"""
Quick camera test utility.
Run this to check which cameras are available.
"""

import cv2

def test_cameras():
    """Test which camera indices work."""
    print("Testing camera indices...")
    print("-" * 50)
    
    working_cameras = []
    
    for i in range(5):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                height, width = frame.shape[:2]
                print(f"✓ Camera {i}: Working ({width}x{height})")
                working_cameras.append(i)
            else:
                print(f"✗ Camera {i}: Opens but can't read frames")
            cap.release()
        else:
            print(f"✗ Camera {i}: Not available")
    
    print("-" * 50)
    
    if working_cameras:
        print(f"\n✓ Found {len(working_cameras)} working camera(s): {working_cameras}")
        print(f"  App will use camera {working_cameras[0]}")
    else:
        print("\n✗ No working cameras found!")
        print("\nTroubleshooting:")
        print("  1. Check if camera is connected")
        print("  2. Close other apps using the camera (browsers, Zoom, etc.)")
        print("  3. Check camera permissions")
        print("  4. Try: ls -l /dev/video*")
    
    return working_cameras

if __name__ == "__main__":
    test_cameras()
