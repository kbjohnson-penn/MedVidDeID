# MedVidDeID

[![GitHub license](https://img.shields.io/badge/license-See%20Components-blue.svg)](LICENSE)
[![Pipeline Status](https://img.shields.io/badge/pipeline-integrated-green.svg)]()
[![Security](https://img.shields.io/badge/security-hardened-yellow.svg)]()

## Overview

MedVidDeID is a comprehensive medical data de-identification pipeline that removes Protected Health Information (PHI) from multi-modal medical data including video, audio, and text.

## Key Features

- **Multi-modal De-identification**: Comprehensive PHI removal from video, audio, and text
- **Security-Hardened**: Path validation, input sanitization, and thread-safe operations
- **HIPAA Compliance**: Complete audit trails with artifact lineage tracking
- **Pipeline Orchestration**: Automated workflow with error handling and recovery
- **Artifact Management**: SHA256 checksums, metadata tracking, and immutable storage
- **AI-Powered**: YOLO pose detection, WhisperX transcription, and NLP-based PHI detection


### Core Components

- **pipeline**: Central artifact management with audit trails
- **video_deid**: Face blurring and pose-based de-identification using YOLO
- **audio_deid**: Speech transcription (WhisperX) and PHI audio scrubbing
- **philter-ucsf**: Text de-identification with 2,260+ PHI detection patterns

## Quick Start

### Prerequisites

```bash
# Required dependencies
conda create -n deid python=3.9
conda activate deid

# For video processing
pip install opencv-python torch torchvision

# For audio transcription (optional)
pip install whisperx

# For text processing
pip install spacy transformers
```

### Installation

```bash
# Clone with all submodules
git clone --recursive https://github.com/kbjohnson-penn/MedVidDeID.git
cd MedVidDeID

# Install pipeline requirements
pip install -r pipeline/requirements.txt

# Setup video_deid module
cd video_deid
pip install -r requirements.txt
pip install -e .
cd ..

# Setup audio_deid module  
cd audio_deid
pip install -r requirements.txt
cd ..

# Setup philter-ucsf module
cd philter-ucsf
pip install -r requirements.txt
cd ..
```

### Basic Usage

```bash
# Process a medical video through complete pipeline
python simple_example.py patient_consultation.mp4

# Output structure:
# output/patient_consultation/
# ├── deid_12345678.mp4              # De-identified video
# ├── keypoints_12345678.csv         # Pose detection data
# ├── transcript.json                # Speech transcription
# ├── scrubbed_audio.mp3             # PHI-removed audio
# └── artifacts/                     # Complete audit trail
```

### Advanced Pipeline Usage

```python
from pipeline.simple_integration import process_video_pipeline
from pathlib import Path

# Programmatic access
result = process_video_pipeline(
    video_path=Path("input_video.mp4"),
    output_dir=Path("./secure_output")
)

if result["success"]:
    print(f"De-identified video: {result['output_video']}")
    print(f"Artifacts: {result['artifacts']}")
    print(f"Processing run: {result['run_id']}")
```

## Component Details

### video_deid Module
- **Technology**: YOLO v8 pose detection, Kalman filter tracking
- **Features**: Face blurring, skeleton overlay, temporal consistency
- **Input**: MP4, AVI, MOV video files
- **Output**: De-identified video with preserved audio

```bash
# Video-only processing
cd video_deid
python -m video_deid.cli --operation_type extract --video input.mp4 --keypoints_csv output.csv
python -m video_deid.cli --operation_type deid --video input.mp4 --keypoints_csv output.csv --output deid.mp4
```

### audio_deid Module
- **Technology**: WhisperX speech-to-text, regex-based PHI detection
- **Features**: Word-level timestamp alignment, beep replacement
- **Input**: MP3, WAV, MP4 audio/video files
- **Output**: Transcript JSON, PHI intervals, scrubbed audio

```bash
# Audio transcription and de-identification
cd audio_deid
python transcribe.py --audio input.mp3 --output_format json
python scrub.py --source input.mp3 --json phi_intervals.json --output scrubbed.mp3
```

### philter-ucsf Module
- **Technology**: 2,260+ regex patterns, NLP context analysis
- **Features**: Medical terminology preservation, configurable redaction
- **Input**: JSON, TSV, TXT medical documents
- **Output**: De-identified text with PHI markers

```bash
# Text de-identification
cd philter-ucsf
python main_format.py -i transcript.json -o deidentified.json -f json
python main.py -i notes/ -o output/ -f ./configs/philter_delta.json --prod=True
```

## Security & Compliance

### Security Features

- **Path Validation**: Prevents directory traversal attacks
- **Input Sanitization**: Regex-based filename and path cleaning
- **Symlink Protection**: Blocks symlink-based security bypasses
- **Process Timeouts**: Prevents resource exhaustion attacks
- **Thread Safety**: Concurrent artifact operations with proper locking

### HIPAA Compliance

- **Audit Trails**: Complete operation logging in structured JSON format
- **Artifact Lineage**: Full provenance tracking from input to output
- **Data Integrity**: SHA256 checksums for all stored artifacts
- **Access Logging**: Tracks all artifact access attempts
- **Log Rotation**: Automatic audit log management with size-based rotation

## Output Structure

```
output/video_name/
├── deid_12345678.mp4                    # Final de-identified video
├── keypoints_12345678.csv               # YOLO pose detection data
├── audio_12345678.mp3                   # Extracted audio track
├── transcript.json                      # WhisperX speech transcription
├── phi_intervals.json                   # PHI time segments for audio
├── scrubbed_audio.mp3                   # De-identified audio
├── deidentified_transcript.json         # PHI-removed transcript
└── artifacts/
    ├── storage/                         # Immutable artifact files
    │   ├── VIDEO_RAW/
    │   ├── VIDEO_KEYPOINTS/
    │   ├── VIDEO_DEID/
    │   ├── AUDIO_RAW/
    │   ├── AUDIO_TRANSCRIPT/
    │   ├── AUDIO_PHI_INTERVALS/
    │   ├── AUDIO_DEID/
    │   ├── TEXT_RAW/
    │   └── TEXT_DEID/
    ├── metadata/                        # JSON metadata for each artifact
    └── audit/
        ├── audit.jsonl                  # Complete operation audit trail
        └── runs/                        # Processing run records
```

## Performance & Scalability

### Resource Requirements
- **CPU**: Multi-core recommended for video processing
- **GPU**: CUDA-capable GPU for optimal YOLO/WhisperX performance
- **Memory**: 8GB+ RAM for processing large medical videos
- **Storage**: 2-3x input file size for artifacts and processing

### Processing Times (Approximate)
- **Video De-identification**: 1-2x real-time (varies by resolution)
- **Audio Transcription**: 0.1-0.3x real-time with GPU
- **Text De-identification**: Near real-time for typical documents

## Development & Testing

### Development Environment

```bash
# Install development dependencies
conda activate deid
pip install -r requirements-dev.txt

# Code formatting (video_deid module)
cd video_deid
black video_deid/
isort video_deid/
flake8 video_deid/
mypy video_deid/
```
