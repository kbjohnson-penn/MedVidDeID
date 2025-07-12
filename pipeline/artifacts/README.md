# Artifact Management System

The Artifact Management System provides comprehensive tracking and storage for all intermediate and final outputs in the MedVidDeID pipeline, maintaining a complete audit trail for compliance and debugging.

## Features

### Core Capabilities
- **Artifact Storage**: Centralized storage with automatic organization by type
- **Metadata Tracking**: Rich metadata for each artifact including processing details
- **Audit Trail**: Complete history of all operations for compliance
- **Lineage Tracking**: Track relationships between artifacts
- **Checksum Verification**: Ensure data integrity with SHA256 checksums
- **Status Management**: Track artifact lifecycle (pending, in_progress, completed, failed)

### Artifact Types
- `VIDEO_RAW`: Original video files
- `VIDEO_KEYPOINTS`: Extracted pose/face keypoints
- `VIDEO_DEID`: De-identified video output
- `AUDIO_RAW`: Original or extracted audio
- `AUDIO_PHI_INTERVALS`: PHI detection results
- `AUDIO_DEID`: De-identified audio
- `TEXT_RAW`: Original text/transcripts (includes transcripts)
- `TEXT_DEID`: De-identified text (includes transcripts)
- `METADATA`: Processing metadata
- `LOG`: Processing logs

## Architecture

```
pipeline/artifacts/
├── __init__.py         # Package exports
├── models.py           # Data models
├── storage.py          # File storage backend
├── audit.py            # Audit trail system
├── manager.py          # Main orchestrator
└── README.md           # This file
```

## Usage

### Basic Setup

```python
from pipeline.artifacts import ArtifactManager, ArtifactType, ArtifactStatus

# Initialize the manager
manager = ArtifactManager(
    base_path="/path/to/storage",
    enable_audit=True,      # Enable audit trail logging
    auto_cleanup=True       # Clean temp files after runs
)
```

### Complete Pipeline Example

```python
# Start a processing run
run = manager.start_processing_run({
    "pipeline": "video_deid",
    "timestamp": datetime.now().isoformat(),
    "user": "researcher_1"
})

# 1. Register input video
video_artifact = manager.create_artifact(
    artifact_type=ArtifactType.VIDEO_RAW,
    source_path=Path("patient_interview.mp4"),
    processing_module="input_handler",
    processing_version="1.0.0",
    metadata={
        "duration": "00:15:30",
        "resolution": "1920x1080",
        "fps": 30,
        "size_mb": 250
    }
)

# 2. Extract and store keypoints
manager.update_artifact_status(video_artifact.artifact_id, ArtifactStatus.IN_PROGRESS)

# After keypoint extraction completes...
keypoints_csv = Path("keypoints_output.csv")
keypoints_artifact = manager.create_artifact(
    artifact_type=ArtifactType.VIDEO_KEYPOINTS,
    source_path=keypoints_csv,
    source_artifacts=[video_artifact.artifact_id],
    processing_module="video_deid.keypoints",
    processing_version="2.0.0",
    metadata={
        "total_frames": 27900,
        "people_detected": 2,
        "model": "yolo-pose"
    }
)

# 3. Create de-identified video
deid_video_path = Path("output_blurred.mp4")
deid_video_artifact = manager.create_artifact(
    artifact_type=ArtifactType.VIDEO_DEID,
    source_path=deid_video_path,
    source_artifacts=[video_artifact.artifact_id, keypoints_artifact.artifact_id],
    processing_module="video_deid.blur",
    metadata={
        "blur_method": "gaussian",
        "blur_intensity": "medium",
        "faces_blurred": 2
    }
)

# End the processing run
manager.end_processing_run(ArtifactStatus.COMPLETED)
```

### Creating Artifacts Without Files

```python
# For metadata-only artifacts (e.g., PHI detection results)
phi_artifact = manager.create_artifact(
    artifact_type=ArtifactType.AUDIO_PHI_INTERVALS,
    source_artifacts=[audio_artifact.artifact_id],
    processing_module="audio_deid.detector",
    metadata={
        "phi_segments": [
            {"start": 45.2, "end": 46.8, "type": "name"},
            {"start": 120.5, "end": 122.1, "type": "mrn"}
        ],
        "total_segments": 2
    }
)
```

### Tracking Relationships

```python
# Link artifacts
manager.link_artifacts(
    source_artifact_ids=[video_id, keypoints_id],
    output_artifact_id=deid_video_id,
    relationship="derived_from"
)

# Get artifact lineage
lineage = manager.get_artifact_lineage(deid_video_id)
```

### Querying Artifacts

```python
# List all artifacts
all_artifacts = manager.list_artifacts()
print(f"Total artifacts: {len(all_artifacts)}")

# Filter by type
videos = manager.list_artifacts(
    artifact_type=ArtifactType.VIDEO_DEID,
    status=ArtifactStatus.COMPLETED
)

# Get specific artifact
artifact = manager.get_artifact(artifact_id)
if artifact:
    print(f"Type: {artifact.artifact_type.value}")
    print(f"Status: {artifact.status.value}")
    print(f"Created: {artifact.created_at}")

# Get artifact file path
file_path = manager.get_artifact_file(artifact_id)
if file_path and file_path.exists():
    print(f"File location: {file_path}")
    print(f"File size: {file_path.stat().st_size / 1024 / 1024:.2f} MB")
```

### Audit Trail

```python
# Query audit trail
entries = manager.audit.query_audit_trail(
    operation="artifact_creation",
    success=True,
    limit=10
)

# Get artifact history
history = manager.audit.get_artifact_history(artifact_id)

# Export audit trail
manager.audit.export_audit_trail(
    output_path=Path("audit_export.json"),
    start_time=datetime(2024, 1, 1),
    format="json"
)
```

## Storage Structure

```
storage/
├── artifacts/          # Actual artifact files
│   ├── video_raw/
│   ├── video_keypoints/
│   ├── video_deid/
│   └── ...
├── metadata/           # JSON metadata files
│   └── {artifact_id}.json
├── runs/               # Processing run records
└── temp/               # Temporary files

audit/
└── audit_YYYYMM.jsonl  # Monthly audit logs
```

## Integration with Submodules

### Video De-identification
```python
# Store original video
video_artifact = manager.create_artifact(
    ArtifactType.VIDEO_RAW,
    source_path=video_path,
    processing_module="video_deid"
)

# After keypoint extraction
keypoints_artifact = manager.create_artifact(
    ArtifactType.VIDEO_KEYPOINTS,
    source_path=keypoints_csv,
    source_artifacts=[video_artifact.artifact_id],
    processing_module="video_deid.keypoints"
)
```

### Audio De-identification
```python
# Store PHI intervals
phi_artifact = manager.create_artifact(
    ArtifactType.AUDIO_PHI_INTERVALS,
    source_path=phi_json,
    source_artifacts=[audio_artifact.artifact_id],
    processing_module="audio_deid"
)
```

### Text De-identification
```python
# Store de-identified transcript
text_artifact = manager.create_artifact(
    ArtifactType.TEXT_DEID,
    source_path=deid_text,
    source_artifacts=[raw_text_artifact.artifact_id],
    processing_module="philter-ucsf"
)
```

## Best Practices

1. **Always Start/End Runs**: Use `start_processing_run()` and `end_processing_run()`
2. **Track Relationships**: Use `source_artifacts` to maintain lineage
3. **Include Metadata**: Add relevant processing parameters
4. **Handle Errors**: Update status to FAILED with error messages
5. **Regular Cleanup**: Use `cleanup_old_artifacts()` for storage management

## Error Handling

```python
# Handle artifact creation failures
try:
    artifact = manager.create_artifact(
        artifact_type=ArtifactType.VIDEO_RAW,
        source_path=Path("missing_file.mp4"),
        processing_module="input_handler"
    )
except FileNotFoundError as e:
    print(f"Failed to create artifact: {e}")
    # The error is automatically logged to audit trail

# Update artifact status on failure
try:
    # Process video...
    process_video(video_path)
except Exception as e:
    manager.update_artifact_status(
        artifact_id,
        ArtifactStatus.FAILED,
        error_message=str(e)
    )
```

## Statistics and Monitoring

```python
# Get comprehensive statistics
stats = manager.get_statistics()

print("=== Storage Statistics ===")
print(f"Total size: {stats['storage']['total_size_mb']:.2f} MB")
print(f"Total artifacts: {stats['storage']['total_artifacts']}")

print("\n=== Artifact Distribution ===")
for artifact_type, count in stats['artifacts']['by_type'].items():
    print(f"  {artifact_type}: {count}")

print("\n=== Status Distribution ===")
for status, count in stats['artifacts']['by_status'].items():
    print(f"  {status}: {count}")

if 'audit' in stats:
    print(f"\n=== Errors ===")
    print(f"Total errors: {stats['audit']['total_errors']}")
    for op, count in stats['audit']['errors_by_operation'].items():
        print(f"  {op}: {count}")
```

## Cleanup and Maintenance

```python
# Clean up temporary files
manager.storage.cleanup_temp()

# Remove artifacts older than 30 days
removed = manager.cleanup_old_artifacts(days_old=30)
print(f"Removed {removed} old artifacts")

# Export audit trail before cleanup
manager.audit.export_audit_trail(
    output_path=Path("audit_backup.json"),
    format="json"
)
```

## Security Considerations

- All artifacts are checksummed for integrity
- Audit trail provides complete traceability
- No PHI should be stored in metadata fields
- Use artifact IDs instead of patient identifiers
- Regular cleanup prevents data accumulation