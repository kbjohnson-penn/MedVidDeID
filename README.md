# MedVidDeID

[![GitHub license](https://img.shields.io/badge/license-See%20Components-blue.svg)](LICENSE)

## Overview

MedVidDeID is a comprehensive modular pipeline designed to remove personally identifiable information (PII) from audio/video medical data. By providing robust de-identification capabilities, MedVidDeID enables researchers to unlock the potential of valuable medical recordings while adhering to strict privacy regulations (HIPAA).

## Key Features

- **Multi-modal De-identification**: Handles video, audio, and associated text data
- **Privacy-Preserving**: Removes faces, identifiable body features, spoken names, and textual identifiers
- **Research-Ready**: Maintains data utility for medical research while removing PII
- **Modular Design**: Use components independently or as an end-to-end pipeline

## Repository Structure

This repository is organized as a collection of specialized submodules:

- **[audio_deid](audio_deid/README.md)**: Audio redaction for medical recordings
  - Identifies and removes spoken names and identifiers
  - Preserves medical terminology and context
  - Flexible replacement options (silence, tones)
- **[philter-ucsf](philter-ucsf/README.md)**: Text de-identification for medical notes and transcripts
  - NLP-based PHI detection
  - Handles diverse medical text formats
- **[video_deid](video_deid/README.md)**: Face and body de-identification in medical videos
  - Face detection, tracking, and blurring
  - Pose estimation for identity protection
  - Configurable blur techniques

## Getting Started

### Clone the Repository with Submodules

```bash
# Clone the repository with all submodules
git clone --recursive https://github.com/kbjohnson-penn/MedVidDeID.git

# If already cloned without submodules, initialize and update them
git submodule init
git submodule update
```

### Quick Start

For detailed setup and usage instructions, see the README files in each component directory:

- [Philter UCSF Setup](philter-ucsf/README.md)
- [Audio De-identification Setup](audio_deid/README.md)
- [Video De-identification Setup](video_deid/README.md)

## License

Each submodule may have its own licensing terms. Please refer to the individual component licenses for details.
