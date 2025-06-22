#!/usr/bin/env python3
"""Simple test to track a video file with the Artifact Management System."""

import sys
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

from pipeline.artifacts import ArtifactManager, ArtifactType, ArtifactStatus

try:
    import cv2
except ImportError:
    print("OpenCV not installed. Install with: pip install opencv-python")
    sys.exit(1)


def get_video_metadata_opencv(video_path: Path) -> dict:
    """Extract metadata from video using OpenCV."""
    metadata = {
        'filename': video_path.name,
        'size_bytes': video_path.stat().st_size,
        'size_mb': video_path.stat().st_size / (1024 * 1024),
        'modified': datetime.fromtimestamp(video_path.stat().st_mtime).isoformat()
    }
    
    # Open video with OpenCV
    cap = cv2.VideoCapture(str(video_path))
    
    if cap.isOpened():
        # Get video properties
        metadata.update({
            'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'fps': cap.get(cv2.CAP_PROP_FPS),
            'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            'format': cap.get(cv2.CAP_PROP_FORMAT),
            'fourcc': int(cap.get(cv2.CAP_PROP_FOURCC)),
            'backend': cap.get(cv2.CAP_PROP_BACKEND)
        })
        
        # Calculate duration
        if metadata['fps'] > 0:
            metadata['duration_seconds'] = metadata['frame_count'] / metadata['fps']
            metadata['duration_formatted'] = str(datetime.utcfromtimestamp(metadata['duration_seconds']).strftime('%H:%M:%S'))
        
        # Convert fourcc to string
        fourcc = metadata['fourcc']
        if fourcc > 0:
            metadata['codec'] = "".join([chr((int(fourcc) >> 8 * i) & 0xFF) for i in range(4)])
        
        # Check if video has audio (OpenCV doesn't directly support audio metadata)
        metadata['has_audio'] = "Unknown (OpenCV doesn't read audio)"
        
        # Get first frame for additional info
        ret, frame = cap.read()
        if ret and frame is not None:
            metadata['first_frame_shape'] = frame.shape
            metadata['channels'] = frame.shape[2] if len(frame.shape) > 2 else 1
            metadata['color_format'] = 'Color' if metadata['channels'] == 3 else 'Grayscale'
        
        cap.release()
    else:
        print(f"Warning: Could not open video with OpenCV")
    
    return metadata


def test_video_tracking(video_path: Path):
    """Test artifact tracking with a real video file."""
    
    # Initialize manager
    manager = ArtifactManager(
        base_path="./artifact_test",
        enable_audit=True
    )
    
    print(f"=== Testing Artifact System with Real Video ===")
    print(f"Video: {video_path}\n")
    
    # Extract video metadata using OpenCV
    print("Extracting video metadata with OpenCV...")
    video_metadata = get_video_metadata_opencv(video_path)
    
    # Display metadata
    print("\nVideo Properties:")
    print(f"  - File size: {video_metadata['size_mb']:.2f} MB")
    print(f"  - Resolution: {video_metadata.get('width', 'N/A')}x{video_metadata.get('height', 'N/A')}")
    print(f"  - Frame rate: {video_metadata.get('fps', 'N/A'):.2f} fps")
    print(f"  - Total frames: {video_metadata.get('frame_count', 'N/A')}")
    print(f"  - Duration: {video_metadata.get('duration_formatted', 'N/A')}")
    print(f"  - Codec: {video_metadata.get('codec', 'N/A')}")
    print(f"  - Color format: {video_metadata.get('color_format', 'N/A')}")
    print()
    
    # Start processing run
    run = manager.start_processing_run({
        "test": "video_tracking",
        "video": str(video_path)
    })
    
    # Create video artifact with extracted metadata
    print("\n1. Creating video artifact with metadata...")
    video_artifact = manager.create_artifact(
        artifact_type=ArtifactType.VIDEO_RAW,
        source_path=video_path,
        processing_module="test",
        metadata=video_metadata  # Use the extracted metadata
    )
    
    print(f"   ✓ Artifact ID: {video_artifact.artifact_id}")
    print(f"   ✓ Status: {video_artifact.status.value}")
    print(f"   ✓ Stored at: {video_artifact.file_path}")
    print(f"   ✓ Checksum: {video_artifact.checksum[:32]}...")
    
    # Simulate creating a keypoints artifact (without actual processing)
    print("\n2. Creating mock keypoints artifact...")
    keypoints_artifact = manager.create_artifact(
        artifact_type=ArtifactType.VIDEO_KEYPOINTS,
        source_artifacts=[video_artifact.artifact_id],
        processing_module="test.keypoints",
        metadata={
            "mock": True,
            "description": "Simulated keypoints for testing"
        }
    )
    print(f"   ✓ Keypoints artifact: {keypoints_artifact.artifact_id}")
    
    # Get statistics
    print("\n3. Artifact Statistics:")
    stats = manager.get_statistics()
    print(f"   - Total artifacts: {stats['artifacts']['total']}")
    print(f"   - Storage size: {stats['storage']['total_size_mb']:.2f} MB")
    print(f"   - By type: {stats['artifacts']['by_type']}")
    
    # Query artifacts
    print("\n4. Querying artifacts:")
    videos = manager.list_artifacts(artifact_type=ArtifactType.VIDEO_RAW)
    for v in videos:
        print(f"   - {v.artifact_id[:8]}... created at {v.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check audit trail
    print("\n5. Recent audit entries:")
    entries = manager.audit.query_audit_trail(limit=5)
    for entry in entries:
        print(f"   - {entry['timestamp']}: {entry['operation']}.{entry['action']}")
    
    # End run
    manager.end_processing_run(ArtifactStatus.COMPLETED)
    
    print(f"\n✓ Test completed. Artifacts stored in: ./artifact_test/")
    print(f"  - View metadata: ls ./artifact_test/storage/metadata/")
    print(f"  - View audit log: cat ./artifact_test/audit/*.jsonl | jq .")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_video_tracking.py <video_path>")
        print("\nThis will:")
        print("- Create an artifact entry for your video")
        print("- Calculate and store its checksum")
        print("- Track it in the system")
        print("- Show how the artifact management works")
        sys.exit(1)
    
    video_path = Path(sys.argv[1])
    if not video_path.exists():
        print(f"Error: Video not found: {video_path}")
        sys.exit(1)
    
    test_video_tracking(video_path)