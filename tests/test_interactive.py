#!/usr/bin/env python3
"""Interactive test script for the Artifact Management System."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from pipeline.artifacts import ArtifactManager, ArtifactType

# Create a test directory
test_dir = Path("./test_artifacts")
test_dir.mkdir(exist_ok=True)

# Initialize the manager
manager = ArtifactManager(
    base_path=test_dir,
    enable_audit=True,
    auto_cleanup=False
)

print("Artifact Manager initialized at:", test_dir)
print("\nYou can now interact with the manager:")
print("- manager.start_processing_run()")
print("- manager.create_artifact(...)")
print("- manager.list_artifacts()")
print("- manager.get_statistics()")
print("\nOr explore the created directories:")
print(f"- ls {test_dir}")
print(f"- cat {test_dir}/audit/*.jsonl")

# Example: Create a test file and artifact
test_file = test_dir / "sample.txt"
test_file.write_text("Sample medical data")

# Start a run
run = manager.start_processing_run({"test": True})
print(f"\nStarted run: {run.run_id}")

# Create an artifact
artifact = manager.create_artifact(
    artifact_type=ArtifactType.VIDEO_RAW,
    source_path=test_file,
    processing_module="test",
    metadata={"description": "Test video"}
)
print(f"Created artifact: {artifact.artifact_id}")

# The manager object is available for interactive exploration
print("\nManager object available as 'manager' for interactive use")
print("Try: manager.get_statistics()")