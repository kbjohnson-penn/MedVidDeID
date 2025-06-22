# Tests for MedVidDeID Pipeline

This directory contains test scripts for the MedVidDeID pipeline and artifact management system.

## Test Files

### Unit Tests
- **`test_artifact_system.py`** - Comprehensive unit tests for the artifact management system
- **`test_pipeline_integration.py`** - Simulated pipeline integration test

### Interactive Tests
- **`test_interactive.py`** - Interactive test environment for manual exploration
- **`test_video_tracking.py`** - Simple video tracking test (minimal requirements)
- **`test_video_artifact_only.py`** - Full artifact test with video metadata (requires OpenCV)

### Integration Tests
- **`test_with_real_video.py`** - Full pipeline test with video_deid (requires video_deid installation)

## Running Tests

### Basic Unit Tests
```bash
# From the MedVidDeID root directory
python tests/test_artifact_system.py
python tests/test_pipeline_integration.py
```

### Video Tests
```bash
# Simple tracking (no dependencies)
python tests/test_video_tracking.py path/to/video.mp4

# With OpenCV metadata extraction
python tests/test_video_artifact_only.py path/to/video.mp4

# Full pipeline (requires video_deid installed)
python tests/test_with_real_video.py path/to/video.mp4
```

### Interactive Testing
```bash
# Interactive exploration
python -i tests/test_interactive.py
```

## Dependencies

- **All tests**: Python 3.7+, pipeline module
- **Video metadata tests**: OpenCV (`pip install opencv-python`)
- **Full pipeline tests**: video_deid module installed

## Output Locations

Tests create temporary directories:
- `test_artifact_system.py` - Uses system temp directory
- `test_video_*` - Creates `./artifact_test/` or `./video_artifact_test/`
- `test_with_real_video.py` - Creates `./test_output/YYYYMMDD_HHMMSS/`

## Test Structure

Each test demonstrates different aspects:

1. **Artifact creation and storage**
2. **Metadata tracking**
3. **Audit trail functionality**
4. **Relationship management**
5. **Statistics and monitoring**
6. **Error handling**

The tests validate that the artifact management system properly tracks all pipeline operations and maintains data integrity.