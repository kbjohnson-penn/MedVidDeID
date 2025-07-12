"""Storage backend for artifacts."""

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
import logging

from .models import ArtifactMetadata, ArtifactType, ArtifactStatus


class ArtifactStorage:
    """Manages physical storage of artifacts."""
    
    def __init__(self, base_path: Union[str, Path], create_dirs: bool = True):
        """Initialize artifact storage.
        
        Args:
            base_path: Base directory for artifact storage
            create_dirs: Whether to create directories if they don't exist
        """
        self.base_path = Path(base_path)
        self.logger = logging.getLogger(__name__)
        
        if create_dirs:
            self._setup_directories()
    
    def _setup_directories(self):
        """Create directory structure for artifact storage."""
        directories = [
            self.base_path,
            self.base_path / "artifacts",
            self.base_path / "metadata",
            self.base_path / "runs",
            self.base_path / "temp"
        ]
        
        # Create subdirectories for each artifact type
        for artifact_type in ArtifactType:
            directories.append(self.base_path / "artifacts" / artifact_type.value)
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Ensured directory exists: {directory}")
    
    def store_artifact(self, source_path: Path, artifact: ArtifactMetadata) -> Path:
        """Store an artifact file and update metadata.
        
        Args:
            source_path: Path to the source file
            artifact: Artifact metadata
            
        Returns:
            Path to the stored artifact
        """
        # Validate source path for security
        if source_path.is_symlink():
            raise ValueError("Symlinks not allowed for security")
        resolved_source = source_path.resolve()
        if not resolved_source.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")
        
        # Sanitize filename to prevent path traversal and dangerous chars
        import re
        safe_filename = re.sub(r'[^\w\-_\.]', '_', resolved_source.name)
        if len(safe_filename) > 100:
            safe_filename = safe_filename[:100]
        
        # Determine storage path
        artifact_dir = self.base_path / "artifacts" / artifact.artifact_type.value
        storage_path = artifact_dir / f"{artifact.artifact_id}_{safe_filename}"
        
        # Copy file to storage
        shutil.copy2(resolved_source, storage_path)
        
        # Update metadata
        artifact.file_path = storage_path
        artifact.file_size = storage_path.stat().st_size
        artifact.checksum = self._calculate_checksum(storage_path)
        
        # Save metadata
        self.save_metadata(artifact)
        
        self.logger.info(f"Stored artifact {artifact.artifact_id} at {storage_path}")
        return storage_path
    
    def retrieve_artifact(self, artifact_id: str) -> Optional[Path]:
        """Retrieve an artifact by ID.
        
        Args:
            artifact_id: Unique artifact identifier
            
        Returns:
            Path to the artifact file or None if not found
        """
        metadata = self.load_metadata(artifact_id)
        if metadata and metadata.file_path and Path(metadata.file_path).exists():
            return Path(metadata.file_path)
        return None
    
    def save_metadata(self, artifact: ArtifactMetadata):
        """Save artifact metadata to JSON file.
        
        Args:
            artifact: Artifact metadata to save
        """
        metadata_path = self.base_path / "metadata" / f"{artifact.artifact_id}.json"
        
        # Convert to dict, handling Path objects
        metadata_dict = {
            "artifact_id": artifact.artifact_id,
            "artifact_type": artifact.artifact_type.value,
            "status": artifact.status.value,
            "created_at": artifact.created_at.isoformat(),
            "updated_at": artifact.updated_at.isoformat(),
            "source_artifacts": artifact.source_artifacts,
            "processing_module": artifact.processing_module,
            "processing_version": artifact.processing_version,
            "file_path": str(artifact.file_path) if artifact.file_path else None,
            "file_size": artifact.file_size,
            "checksum": artifact.checksum,
            "metadata": artifact.metadata,
            "error_message": artifact.error_message
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata_dict, f, indent=2)
        
        self.logger.debug(f"Saved metadata for artifact {artifact.artifact_id}")
    
    def load_metadata(self, artifact_id: str) -> Optional[ArtifactMetadata]:
        """Load artifact metadata from JSON file.
        
        Args:
            artifact_id: Unique artifact identifier
            
        Returns:
            ArtifactMetadata object or None if not found
        """
        metadata_path = self.base_path / "metadata" / f"{artifact_id}.json"
        
        if not metadata_path.exists():
            return None
        
        with open(metadata_path, 'r') as f:
            data = json.load(f)
        
        # Convert back to ArtifactMetadata
        artifact = ArtifactMetadata(
            artifact_id=data["artifact_id"],
            artifact_type=ArtifactType(data["artifact_type"]),
            status=ArtifactStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            source_artifacts=data["source_artifacts"],
            processing_module=data["processing_module"],
            processing_version=data["processing_version"],
            file_path=Path(data["file_path"]) if data["file_path"] else None,
            file_size=data["file_size"],
            checksum=data["checksum"],
            metadata=data["metadata"],
            error_message=data["error_message"]
        )
        
        return artifact
    
    def list_artifacts(self, artifact_type: Optional[ArtifactType] = None,
                      status: Optional[ArtifactStatus] = None) -> List[ArtifactMetadata]:
        """List artifacts with optional filtering.
        
        Args:
            artifact_type: Filter by artifact type
            status: Filter by status
            
        Returns:
            List of artifact metadata objects
        """
        artifacts = []
        metadata_dir = self.base_path / "metadata"
        
        for metadata_file in metadata_dir.glob("*.json"):
            artifact = self.load_metadata(metadata_file.stem)
            if artifact:
                # Apply filters
                if artifact_type and artifact.artifact_type != artifact_type:
                    continue
                if status and artifact.status != status:
                    continue
                artifacts.append(artifact)
        
        return artifacts
    
    def cleanup_temp(self):
        """Clean up temporary files."""
        temp_dir = self.base_path / "temp"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            temp_dir.mkdir()
            self.logger.info("Cleaned up temporary directory")
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics.
        
        Returns:
            Dictionary with storage statistics
        """
        total_size = 0
        artifact_counts = {}
        
        for artifact_type in ArtifactType:
            artifact_dir = self.base_path / "artifacts" / artifact_type.value
            if artifact_dir.exists():
                files = list(artifact_dir.glob("*"))
                artifact_counts[artifact_type.value] = len(files)
                total_size += sum(f.stat().st_size for f in files if f.is_file())
        
        return {
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "artifact_counts": artifact_counts,
            "total_artifacts": sum(artifact_counts.values())
        }
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Hexadecimal checksum string
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()


# Import datetime for the load_metadata method
from datetime import datetime