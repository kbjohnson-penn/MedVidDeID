"""Data models for the Artifact Management System."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
import uuid


class ArtifactType(Enum):
    """Types of artifacts in the pipeline."""
    VIDEO_RAW = "video_raw"
    VIDEO_KEYPOINTS = "video_keypoints"
    VIDEO_DEID = "video_deid"
    AUDIO_RAW = "audio_raw"
    AUDIO_TRANSCRIPT = "audio_transcript"
    AUDIO_PHI_INTERVALS = "audio_phi_intervals"
    AUDIO_DEID = "audio_deid"
    TEXT_RAW = "text_raw"
    TEXT_DEID = "text_deid"
    METADATA = "metadata"
    LOG = "log"


class ArtifactStatus(Enum):
    """Status of an artifact in the pipeline."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


@dataclass
class ArtifactMetadata:
    """Metadata for tracking artifacts."""
    artifact_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    artifact_type: ArtifactType = ArtifactType.METADATA
    status: ArtifactStatus = ArtifactStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    source_artifacts: List[str] = field(default_factory=list)
    processing_module: Optional[str] = None
    processing_version: Optional[str] = None
    file_path: Optional[Path] = None
    file_size: Optional[int] = None
    checksum: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    
    def update_status(self, status: ArtifactStatus, error_message: Optional[str] = None):
        """Update artifact status and timestamp."""
        self.status = status
        self.updated_at = datetime.now()
        if error_message:
            self.error_message = error_message


@dataclass
class AuditEntry:
    """Audit trail entry for tracking operations."""
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    operation: str = ""
    artifact_id: Optional[str] = None
    user: Optional[str] = None
    module: Optional[str] = None
    action: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert audit entry to dictionary."""
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp.isoformat(),
            "operation": self.operation,
            "artifact_id": self.artifact_id,
            "user": self.user,
            "module": self.module,
            "action": self.action,
            "details": self.details,
            "success": self.success,
            "error_message": self.error_message
        }


@dataclass
class ProcessingRun:
    """Represents a complete processing run through the pipeline."""
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    status: ArtifactStatus = ArtifactStatus.IN_PROGRESS
    input_artifacts: List[str] = field(default_factory=list)
    output_artifacts: List[str] = field(default_factory=list)
    configuration: Dict[str, Any] = field(default_factory=dict)
    error_messages: List[str] = field(default_factory=list)
    
    def complete(self, status: ArtifactStatus = ArtifactStatus.COMPLETED):
        """Mark the processing run as complete."""
        self.completed_at = datetime.now()
        self.status = status