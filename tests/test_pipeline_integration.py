#!/usr/bin/env python3
"""Test integration with MedVidDeID pipeline components."""

import sys
from pathlib import Path
from datetime import datetime
sys.path.append(str(Path(__file__).parent.parent))

from pipeline.artifacts import ArtifactManager, ArtifactType, ArtifactStatus


def simulate_video_pipeline():
    """Simulate a complete video de-identification pipeline."""
    
    # Initialize manager
    manager = ArtifactManager("./pipeline_test", enable_audit=True)
    
    # Start processing run
    run = manager.start_processing_run({
        "pipeline": "video_deid",
        "timestamp": datetime.now().isoformat(),
        "user": "test_user"
    })
    
    print(f"=== Simulating Video De-identification Pipeline ===")
    print(f"Run ID: {run.run_id}\n")
    
    # Step 1: Input video
    print("1. Registering input video...")
    # In real usage, this would be an actual video file
    video_artifact = manager.create_artifact(
        artifact_type=ArtifactType.VIDEO_RAW,
        processing_module="input_handler",
        metadata={
            "filename": "patient_interview.mp4",
            "duration": "00:15:30",
            "resolution": "1920x1080",
            "fps": 30,
            "size_mb": 250
        }
    )
    print(f"   ✓ Video artifact: {video_artifact.artifact_id[:8]}...")
    
    # Step 2: Extract keypoints
    print("\n2. Extracting keypoints...")
    manager.update_artifact_status(video_artifact.artifact_id, ArtifactStatus.IN_PROGRESS)
    
    # Simulate keypoints extraction
    keypoints_artifact = manager.create_artifact(
        artifact_type=ArtifactType.VIDEO_KEYPOINTS,
        source_artifacts=[video_artifact.artifact_id],
        processing_module="video_deid.keypoints",
        processing_version="2.0.0",
        metadata={
            "total_frames": 27900,
            "people_detected": 2,
            "processing_time_seconds": 145.3,
            "model": "yolo-pose"
        }
    )
    print(f"   ✓ Keypoints artifact: {keypoints_artifact.artifact_id[:8]}...")
    
    # Step 3: Extract audio
    print("\n3. Extracting audio...")
    audio_artifact = manager.create_artifact(
        artifact_type=ArtifactType.AUDIO_RAW,
        source_artifacts=[video_artifact.artifact_id],
        processing_module="video_deid.audio",
        metadata={
            "format": "wav",
            "duration": "00:15:30",
            "channels": 2,
            "sample_rate": 44100
        }
    )
    print(f"   ✓ Audio artifact: {audio_artifact.artifact_id[:8]}...")
    
    # Step 4: Detect PHI in audio
    print("\n4. Detecting PHI in audio...")
    phi_artifact = manager.create_artifact(
        artifact_type=ArtifactType.AUDIO_PHI_INTERVALS,
        source_artifacts=[audio_artifact.artifact_id],
        processing_module="audio_deid.detector",
        metadata={
            "phi_segments_found": 5,
            "total_phi_duration_seconds": 8.5,
            "detection_confidence": 0.92
        }
    )
    print(f"   ✓ PHI intervals: {phi_artifact.artifact_id[:8]}...")
    
    # Step 5: Create de-identified video
    print("\n5. Creating de-identified video...")
    deid_video_artifact = manager.create_artifact(
        artifact_type=ArtifactType.VIDEO_DEID,
        source_artifacts=[video_artifact.artifact_id, keypoints_artifact.artifact_id],
        processing_module="video_deid.blur",
        metadata={
            "blur_method": "gaussian",
            "blur_intensity": "medium",
            "faces_blurred": 2,
            "processing_time_seconds": 89.2
        }
    )
    print(f"   ✓ De-identified video: {deid_video_artifact.artifact_id[:8]}...")
    
    # Step 6: Create scrubbed audio
    print("\n6. Creating scrubbed audio...")
    deid_audio_artifact = manager.create_artifact(
        artifact_type=ArtifactType.AUDIO_DEID,
        source_artifacts=[audio_artifact.artifact_id, phi_artifact.artifact_id],
        processing_module="audio_deid.scrub",
        metadata={
            "segments_replaced": 5,
            "replacement_sound": "beep",
            "processing_time_seconds": 12.7
        }
    )
    print(f"   ✓ Scrubbed audio: {deid_audio_artifact.artifact_id[:8]}...")
    
    # Complete the run
    manager.end_processing_run(ArtifactStatus.COMPLETED)
    
    # Show statistics
    print("\n=== Pipeline Statistics ===")
    stats = manager.get_statistics()
    print(f"Total artifacts created: {stats['artifacts']['total']}")
    print(f"Artifacts by type:")
    for artifact_type, count in stats['artifacts']['by_type'].items():
        print(f"  - {artifact_type}: {count}")
    
    # Show lineage for final video
    print(f"\n=== De-identified Video Lineage ===")
    lineage = manager.get_artifact_lineage(deid_video_artifact.artifact_id)
    print_lineage(lineage)
    
    # Query audit trail
    print("\n=== Recent Operations ===")
    recent_ops = manager.audit.query_audit_trail(limit=10)
    for op in recent_ops[-5:]:  # Show last 5
        print(f"  {op['operation']}.{op['action']} - {op['timestamp']}")
    
    return manager


def print_lineage(lineage: dict, indent: int = 0):
    """Pretty print artifact lineage."""
    prefix = "  " * indent
    status = lineage.get('status', 'unknown')
    artifact_type = lineage.get('type', 'unknown')
    print(f"{prefix}├─ {lineage['artifact_id'][:8]}... ({artifact_type}, {status})")
    for source in lineage.get('sources', []):
        print_lineage(source, indent + 1)


if __name__ == "__main__":
    try:
        manager = simulate_video_pipeline()
        print("\n✓ Pipeline simulation completed successfully!")
        print(f"\nExplore results in: ./pipeline_test/")
        print("- Audit logs: ./pipeline_test/audit/")
        print("- Metadata: ./pipeline_test/storage/metadata/")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()