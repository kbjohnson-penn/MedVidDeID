#!/usr/bin/env python3
"""
Simple example using the MedVidDeID pipeline integration.
"""

import sys
from pathlib import Path

# Add project root to Python path
sys.path.append(str(Path(__file__).parent))

from pipeline.simple_integration import process_video_pipeline


def main():
    if len(sys.argv) < 2:
        print("Usage: python simple_example.py <video_path>")
        return
    
    video_path = Path(sys.argv[1])
    if not video_path.exists():
        print(f"Error: Video not found: {video_path}")
        return
    
    output_dir = Path("./output") / video_path.stem
    
    print(f"Processing: {video_path}")
    print(f"Output: {output_dir}")
    
    result = process_video_pipeline(video_path, output_dir)
    
    if result["success"]:
        print(f"\n✓ Success!")
        print(f"Output video: {result['output_video']}")
    else:
        print(f"\n✗ Failed: {result['error']}")


if __name__ == "__main__":
    main()