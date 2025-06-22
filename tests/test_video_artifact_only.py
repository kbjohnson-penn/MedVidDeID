#!/usr/bin/env python3
"""Test the Artifact Management System with a real video - artifact tracking only."""

import sys
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

from pipeline.artifacts import ArtifactManager, ArtifactType, ArtifactStatus

try:
    import cv2
    has_opencv = True
except ImportError:
    has_opencv = False
    print("Warning: OpenCV not installed. Video metadata will be limited.")


def extract_video_metadata(video_path: Path) -> dict:
    """Extract comprehensive video metadata."""
    metadata = {
        "filename": video_path.name,
        "file_path": str(video_path),
        "size_bytes": video_path.stat().st_size,
        "size_mb": video_path.stat().st_size / (1024 * 1024),
        "modified": datetime.fromtimestamp(video_path.stat().st_mtime).isoformat()
    }
    
    if has_opencv:
        cap = cv2.VideoCapture(str(video_path))
        if cap.isOpened():
            # Extract all available properties
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
            
            metadata.update({
                "width": width,
                "height": height,
                "resolution": f"{width}x{height}",
                "fps": fps,
                "frame_count": frame_count,
                "fourcc": fourcc,
                "format": cap.get(cv2.CAP_PROP_FORMAT),
                "brightness": cap.get(cv2.CAP_PROP_BRIGHTNESS),
                "contrast": cap.get(cv2.CAP_PROP_CONTRAST),
                "saturation": cap.get(cv2.CAP_PROP_SATURATION),
                "hue": cap.get(cv2.CAP_PROP_HUE),
            })
            
            # Calculate duration
            if fps > 0:
                duration_seconds = frame_count / fps
                metadata["duration_seconds"] = duration_seconds
                metadata["duration_formatted"] = str(datetime.utcfromtimestamp(duration_seconds).strftime('%H:%M:%S'))
            
            # Convert fourcc to codec string
            if fourcc > 0:
                metadata["codec"] = "".join([chr((int(fourcc) >> 8 * i) & 0xFF) for i in range(4)])
            
            # Get backend info
            backend = int(cap.get(cv2.CAP_PROP_BACKEND))
            backend_names = {
                0: "Auto",
                200: "VFW",
                300: "V4L/V4L2", 
                700: "Firewire",
                800: "QT",
                900: "Unicap",
                1100: "DirectShow",
                1200: "AVFoundation",
                1400: "FFMPEG",
                1500: "OpenNI",
                1600: "GStreamer",
            }
            metadata["backend"] = backend_names.get(backend, f"Unknown ({backend})")
            
            # Read first frame for color analysis
            ret, frame = cap.read()
            if ret and frame is not None:
                metadata["frame_shape"] = frame.shape
                metadata["color_channels"] = frame.shape[2] if len(frame.shape) > 2 else 1
                metadata["color_format"] = "BGR" if metadata["color_channels"] == 3 else "Grayscale"
                metadata["bit_depth"] = frame.dtype
            
            cap.release()
    
    return metadata


def test_video_artifact_management(video_path: Path):
    """Test artifact management with a real video file."""
    
    # Create output directory
    output_dir = Path("./video_artifact_test") / datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize artifact manager
    manager = ArtifactManager(
        base_path=output_dir / "artifacts",
        enable_audit=True,
        auto_cleanup=False
    )
    
    print(f"=== Video Artifact Management Test ===")
    print(f"Video: {video_path}")
    print(f"Output: {output_dir}\n")
    
    # Start processing run
    run = manager.start_processing_run({
        "test": "video_artifact_management",
        "video": str(video_path),
        "timestamp": datetime.now().isoformat()
    })
    
    # Extract video metadata
    print("1. Extracting video metadata...")
    metadata = extract_video_metadata(video_path)
    
    # Display metadata
    print("\nVideo Properties:")
    print(f"  - Size: {metadata['size_mb']:.2f} MB")
    if 'resolution' in metadata:
        print(f"  - Resolution: {metadata['resolution']}")
        print(f"  - Frame rate: {metadata['fps']:.2f} fps")
        print(f"  - Total frames: {metadata['frame_count']:,}")
        print(f"  - Duration: {metadata.get('duration_formatted', 'N/A')}")
        print(f"  - Codec: {metadata.get('codec', 'N/A')}")
        print(f"  - Color format: {metadata.get('color_format', 'N/A')}")
        print(f"  - Backend: {metadata.get('backend', 'N/A')}")
    
    # Create video artifact
    print("\n2. Creating video artifact...")
    video_artifact = manager.create_artifact(
        artifact_type=ArtifactType.VIDEO_RAW,
        source_path=video_path,
        processing_module="video_input",
        processing_version="1.0.0",
        metadata=metadata
    )
    
    print(f"   ✓ Artifact ID: {video_artifact.artifact_id}")
    print(f"   ✓ Status: {video_artifact.status.value}")
    print(f"   ✓ Checksum: {video_artifact.checksum[:32]}...")
    print(f"   ✓ Stored at: {video_artifact.file_path}")
    
    # Simulate processing stages
    print("\n3. Simulating processing pipeline...")
    
    # Simulate keypoint extraction
    print("   - Creating keypoints artifact (simulated)...")
    keypoints_artifact = manager.create_artifact(
        artifact_type=ArtifactType.VIDEO_KEYPOINTS,
        source_artifacts=[video_artifact.artifact_id],
        processing_module="keypoint_extractor",
        metadata={
            "simulated": True,
            "model": "yolo-pose",
            "confidence_threshold": 0.8,
            "extracted_frames": metadata.get('frame_count', 0)
        }
    )
    manager.link_artifacts(
        source_artifact_ids=[video_artifact.artifact_id],
        output_artifact_id=keypoints_artifact.artifact_id,
        relationship="extracted_from"
    )
    
    # Simulate de-identification
    print("   - Creating de-identified video artifact (simulated)...")
    deid_artifact = manager.create_artifact(
        artifact_type=ArtifactType.VIDEO_DEID,
        source_artifacts=[video_artifact.artifact_id, keypoints_artifact.artifact_id],
        processing_module="video_deidentifier",
        metadata={
            "simulated": True,
            "blur_method": "gaussian",
            "blur_intensity": "medium",
            "original_resolution": metadata.get('resolution', 'unknown')
        }
    )
    
    # Show lineage
    print("\n4. Artifact Lineage:")
    lineage = manager.get_artifact_lineage(deid_artifact.artifact_id)
    print_lineage(lineage)
    
    # Get statistics
    print("\n5. Pipeline Statistics:")
    stats = manager.get_statistics()
    print(f"   - Total artifacts: {stats['artifacts']['total']}")
    print(f"   - Storage used: {stats['storage']['total_size_mb']:.2f} MB")
    print(f"   - Artifacts by type:")
    for atype, count in stats['artifacts']['by_type'].items():
        print(f"     • {atype}: {count}")
    
    # Query audit trail
    print("\n6. Recent Audit Entries:")
    entries = manager.audit.query_audit_trail(limit=10)
    for entry in entries[-5:]:
        print(f"   - {entry['timestamp']}: {entry['operation']}.{entry['action']}")
    
    # End processing run
    manager.end_processing_run(ArtifactStatus.COMPLETED)
    
    print(f"\n✓ Test completed successfully!")
    print(f"\nArtifacts and audit logs stored in: {output_dir}")
    print(f"To inspect:")
    print(f"  - Metadata: cat {output_dir}/artifacts/storage/metadata/*.json | jq .")
    print(f"  - Audit log: cat {output_dir}/artifacts/audit/*.jsonl | jq .")


def print_lineage(lineage: dict, indent: int = 0):
    """Pretty print artifact lineage."""
    prefix = "   " + "  " * indent
    artifact_type = lineage.get('type', 'unknown')
    print(f"{prefix}├─ {lineage['artifact_id'][:8]}... ({artifact_type})")
    for source in lineage.get('sources', []):
        print_lineage(source, indent + 1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_video_artifact_only.py <video_path>")
        print("\nThis will test the artifact management system with a real video file.")
        print("It extracts metadata and simulates the pipeline stages without requiring")
        print("the video_deid module to be installed.")
        sys.exit(1)
    
    video_path = Path(sys.argv[1])
    if not video_path.exists():
        print(f"Error: Video file not found: {video_path}")
        sys.exit(1)
    
    test_video_artifact_management(video_path)