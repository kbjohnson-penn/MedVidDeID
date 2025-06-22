#!/usr/bin/env python3
"""Test the Artifact Management System with actual video processing."""

import sys
import subprocess
from pathlib import Path
from datetime import datetime

# Add paths for both pipeline and video_deid
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent / "video_deid" / "src"))

from pipeline.artifacts import ArtifactManager, ArtifactType, ArtifactStatus

# Check if video_deid CLI is available
video_deid_cli = Path("video_deid/src/video_deid/cli.py")
if not video_deid_cli.exists():
    print("=" * 60)
    print("ERROR: video_deid/src/video_deid/cli.py not found!")
    print("Make sure you're running from the MedVidDeID root directory")
    print("=" * 60)
    sys.exit(1)

# Test if we can run the CLI
try:
    result = subprocess.run([sys.executable, "-m", "video_deid.cli", "--help"], 
                          capture_output=True, text=True)
    if result.returncode != 0:
        print("=" * 60)
        print("WARNING: video_deid CLI failed to run!")
        print("Error:", result.stderr)
        print("To install video_deid:")
        print("  cd video_deid")
        print("  pip install -r requirements.txt")
        print("  pip install -e .")
        print("  cd ..")
        print("=" * 60)
        print("\nFor now, use test_video_artifact_only.py instead:")
        print("  python test_video_artifact_only.py <video_path>")
        print("=" * 60)
except Exception as e:
    print(f"Error testing video_deid: {e}")

try:
    import cv2
    has_opencv = True
except ImportError:
    has_opencv = False
    print("Warning: OpenCV not installed. Video metadata will be limited.")


def process_video_with_artifacts(video_path: Path, output_dir: Path):
    """Process a real video through the pipeline with artifact tracking."""
    
    # Initialize artifact manager
    manager = ArtifactManager(
        base_path=output_dir / "artifacts",
        enable_audit=True,
        auto_cleanup=False
    )
    
    # Start processing run
    run = manager.start_processing_run({
        "pipeline": "video_deid",
        "input_video": str(video_path),
        "timestamp": datetime.now().isoformat()
    })
    
    print(f"=== Processing Video with Artifact Tracking ===")
    print(f"Input: {video_path}")
    print(f"Run ID: {run.run_id}\n")
    
    # Initialize deid_path to avoid UnboundLocalError
    deid_path = output_dir / "deid_video.mp4"
    
    try:
        # Step 1: Register input video with metadata
        print("1. Registering input video...")
        
        # Extract video metadata if OpenCV is available
        video_metadata = {
            "filename": video_path.name,
            "size_mb": video_path.stat().st_size / (1024 * 1024)
        }
        
        if has_opencv:
            cap = cv2.VideoCapture(str(video_path))
            if cap.isOpened():
                video_metadata.update({
                    "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                    "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                    "fps": cap.get(cv2.CAP_PROP_FPS),
                    "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
                    "duration_seconds": int(cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS))
                })
                cap.release()
                print(f"   Video: {video_metadata['width']}x{video_metadata['height']} @ {video_metadata['fps']:.1f}fps")
        
        video_artifact = manager.create_artifact(
            artifact_type=ArtifactType.VIDEO_RAW,
            source_path=video_path,
            processing_module="input_handler",
            metadata=video_metadata
        )
        print(f"   ✓ Created artifact: {video_artifact.artifact_id[:8]}...")
        
        # Step 2: Extract keypoints
        print("\n2. Extracting keypoints...")
        keypoints_path = output_dir / f"keypoints_{video_artifact.artifact_id[:8]}.csv"
        
        # Update status
        manager.update_artifact_status(video_artifact.artifact_id, ArtifactStatus.IN_PROGRESS)
        
        # Run actual keypoint extraction
        cmd = [
            sys.executable, "-m", "video_deid.cli",
            "--operation_type", "extract",
            "--video", str(video_path),
            "--keypoints_csv", str(keypoints_path),
            "--progress"
        ]
        
        print(f"   Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Create keypoints artifact
            keypoints_artifact = manager.create_artifact(
                artifact_type=ArtifactType.VIDEO_KEYPOINTS,
                source_path=keypoints_path,
                source_artifacts=[video_artifact.artifact_id],
                processing_module="video_deid.keypoints",
                processing_version="2.0.0",
                metadata={
                    "extraction_time": datetime.now().isoformat(),
                    "file_size": keypoints_path.stat().st_size if keypoints_path.exists() else 0
                }
            )
            print(f"   ✓ Keypoints extracted: {keypoints_artifact.artifact_id[:8]}...")
            manager.update_artifact_status(video_artifact.artifact_id, ArtifactStatus.COMPLETED)
        else:
            print(f"   ✗ Extraction failed: {result.stderr}")
            manager.update_artifact_status(
                video_artifact.artifact_id, 
                ArtifactStatus.FAILED,
                error_message=result.stderr
            )
            return
        
        # Step 3: Create de-identified video
        print("\n3. Creating de-identified video...")
        deid_path = output_dir / f"deid_{video_artifact.artifact_id[:8]}.mp4"
        
        # Run de-identification
        cmd = [
            sys.executable, "-m", "video_deid.cli",
            "--operation_type", "deid",
            "--video", str(video_path),
            "--keypoints_csv", str(keypoints_path),
            "--output", str(deid_path),
            "--progress"
        ]
        
        print(f"   Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and deid_path.exists():
            # Create de-identified video artifact
            deid_artifact = manager.create_artifact(
                artifact_type=ArtifactType.VIDEO_DEID,
                source_path=deid_path,
                source_artifacts=[video_artifact.artifact_id, keypoints_artifact.artifact_id],
                processing_module="video_deid.blur",
                metadata={
                    "blur_method": "gaussian",
                    "processing_time": datetime.now().isoformat(),
                    "output_size_mb": deid_path.stat().st_size / (1024 * 1024)
                }
            )
            print(f"   ✓ De-identified video created: {deid_artifact.artifact_id[:8]}...")
            
            # Show lineage
            print("\n4. Artifact Lineage:")
            lineage = manager.get_artifact_lineage(deid_artifact.artifact_id)
            print_lineage(lineage)
            
        else:
            print(f"   ✗ De-identification failed: {result.stderr}")
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # End processing run
        manager.end_processing_run(
            ArtifactStatus.COMPLETED if deid_path.exists() else ArtifactStatus.FAILED
        )
        
        # Show statistics
        print("\n=== Processing Statistics ===")
        stats = manager.get_statistics()
        print(f"Total artifacts: {stats['artifacts']['total']}")
        print(f"Storage used: {stats['storage']['total_size_mb']:.2f} MB")
        print(f"Artifacts by type: {stats['artifacts']['by_type']}")
        
        # Show output locations
        print(f"\n=== Output Locations ===")
        print(f"Artifacts stored in: {output_dir / 'artifacts'}")
        print(f"Audit trail: {output_dir / 'artifacts' / 'audit'}")
        if keypoints_path.exists():
            print(f"Keypoints CSV: {keypoints_path}")
        if deid_path.exists():
            print(f"De-identified video: {deid_path}")


def print_lineage(lineage: dict, indent: int = 0):
    """Pretty print artifact lineage."""
    prefix = "   " + "  " * indent
    artifact_type = lineage.get('type', 'unknown')
    print(f"{prefix}├─ {lineage['artifact_id'][:8]}... ({artifact_type})")
    for source in lineage.get('sources', []):
        print_lineage(source, indent + 1)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python test_with_real_video.py <video_path>")
        print("\nExample:")
        print("  python test_with_real_video.py sample_video.mp4")
        sys.exit(1)
    
    video_path = Path(sys.argv[1])
    if not video_path.exists():
        print(f"Error: Video file not found: {video_path}")
        sys.exit(1)
    
    # Create output directory
    output_dir = Path("./test_output") / datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process the video
    process_video_with_artifacts(video_path, output_dir)


if __name__ == "__main__":
    main()