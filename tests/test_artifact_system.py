#!/usr/bin/env python3
"""Test script for the Artifact Management System."""

import sys
import tempfile
from pathlib import Path
from datetime import datetime

# Add pipeline to path
sys.path.append(str(Path(__file__).parent.parent))

from pipeline.artifacts import ArtifactManager, ArtifactType, ArtifactStatus


def test_artifact_system():
    """Test the artifact management system functionality."""
    
    print("=== Testing MedVidDeID Artifact Management System ===\n")
    
    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"1. Initializing ArtifactManager in: {temp_dir}")
        manager = ArtifactManager(
            base_path=temp_dir,
            enable_audit=True,
            auto_cleanup=False
        )
        print("   ✓ Manager initialized successfully\n")
        
        # Test 1: Start processing run
        print("2. Starting processing run")
        run = manager.start_processing_run({
            "test_mode": True,
            "timestamp": datetime.now().isoformat()
        })
        print(f"   ✓ Run started with ID: {run.run_id}\n")
        
        # Test 2: Create test file and artifact
        print("3. Creating test artifact")
        test_file = Path(temp_dir) / "test_video.txt"
        test_file.write_text("This is a test video file")
        
        video_artifact = manager.create_artifact(
            artifact_type=ArtifactType.VIDEO_RAW,
            source_path=test_file,
            processing_module="test_module",
            processing_version="1.0.0",
            metadata={"test": True, "size": "small"}
        )
        print(f"   ✓ Created artifact: {video_artifact.artifact_id}")
        print(f"   ✓ Status: {video_artifact.status.value}")
        print(f"   ✓ Checksum: {video_artifact.checksum[:16]}...\n")
        
        # Test 3: Create derived artifact
        print("4. Creating derived artifact")
        keypoints_artifact = manager.create_artifact(
            artifact_type=ArtifactType.VIDEO_KEYPOINTS,
            source_artifacts=[video_artifact.artifact_id],
            processing_module="test_keypoints",
            metadata={"keypoint_count": 17}
        )
        print(f"   ✓ Created keypoints: {keypoints_artifact.artifact_id}\n")
        
        # Test 4: Link artifacts
        print("5. Linking artifacts")
        manager.link_artifacts(
            source_artifact_ids=[video_artifact.artifact_id],
            output_artifact_id=keypoints_artifact.artifact_id,
            relationship="extracted_from"
        )
        print("   ✓ Artifacts linked\n")
        
        # Test 5: Update status
        print("6. Updating artifact status")
        manager.update_artifact_status(
            keypoints_artifact.artifact_id,
            ArtifactStatus.IN_PROGRESS
        )
        manager.update_artifact_status(
            keypoints_artifact.artifact_id,
            ArtifactStatus.COMPLETED
        )
        print("   ✓ Status updated to COMPLETED\n")
        
        # Test 6: List artifacts
        print("7. Listing artifacts")
        all_artifacts = manager.list_artifacts()
        print(f"   ✓ Total artifacts: {len(all_artifacts)}")
        
        video_artifacts = manager.list_artifacts(artifact_type=ArtifactType.VIDEO_RAW)
        print(f"   ✓ Video artifacts: {len(video_artifacts)}\n")
        
        # Test 7: Get lineage
        print("8. Testing artifact lineage")
        lineage = manager.get_artifact_lineage(keypoints_artifact.artifact_id)
        print(f"   ✓ Lineage depth: {count_lineage_depth(lineage)}")
        print(f"   ✓ Source artifacts: {len(lineage.get('sources', []))}\n")
        
        # Test 8: Test audit trail
        print("9. Testing audit trail")
        recent_audits = manager.audit.query_audit_trail(limit=5)
        print(f"   ✓ Audit entries: {len(recent_audits)}")
        
        artifact_history = manager.audit.get_artifact_history(video_artifact.artifact_id)
        print(f"   ✓ History entries for video: {len(artifact_history)}\n")
        
        # Test 9: Get statistics
        print("10. Getting statistics")
        stats = manager.get_statistics()
        print(f"    ✓ Total storage: {stats['storage']['total_size_mb']:.2f} MB")
        print(f"    ✓ Total artifacts: {stats['artifacts']['total']}")
        print(f"    ✓ By type: {stats['artifacts']['by_type']}")
        print(f"    ✓ By status: {stats['artifacts']['by_status']}\n")
        
        # Test 10: End processing run
        print("11. Ending processing run")
        manager.end_processing_run(ArtifactStatus.COMPLETED)
        print(f"    ✓ Run completed successfully\n")
        
        # Test 11: Error handling
        print("12. Testing error handling")
        try:
            manager.create_artifact(
                artifact_type=ArtifactType.VIDEO_RAW,
                source_path=Path("/nonexistent/file.mp4"),
                processing_module="test_error"
            )
        except FileNotFoundError:
            print("    ✓ FileNotFoundError handled correctly\n")
        
        # Test 12: Export audit trail
        print("13. Exporting audit trail")
        export_path = Path(temp_dir) / "audit_export.json"
        manager.audit.export_audit_trail(export_path, format="json")
        print(f"    ✓ Audit exported to: {export_path}")
        print(f"    ✓ Export size: {export_path.stat().st_size} bytes\n")
        
        print("=== All tests completed successfully! ===")
        
        # Show directory structure
        print("\nStorage structure created:")
        show_directory_tree(Path(temp_dir))


def count_lineage_depth(lineage: dict, depth: int = 1) -> int:
    """Count the maximum depth of lineage tree."""
    if not lineage.get('sources'):
        return depth
    
    max_depth = depth
    for source in lineage['sources']:
        source_depth = count_lineage_depth(source, depth + 1)
        max_depth = max(max_depth, source_depth)
    
    return max_depth


def show_directory_tree(path: Path, prefix: str = "", max_depth: int = 3, current_depth: int = 0):
    """Display directory tree structure."""
    if current_depth >= max_depth:
        return
    
    items = sorted(path.iterdir())
    for i, item in enumerate(items):
        is_last = i == len(items) - 1
        current_prefix = "└── " if is_last else "├── "
        print(f"{prefix}{current_prefix}{item.name}")
        
        if item.is_dir() and current_depth < max_depth - 1:
            next_prefix = prefix + ("    " if is_last else "│   ")
            show_directory_tree(item, next_prefix, max_depth, current_depth + 1)


if __name__ == "__main__":
    try:
        test_artifact_system()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)