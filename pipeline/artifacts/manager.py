"""Main Artifact Manager for orchestrating storage and audit trails."""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timedelta
import os
import threading

from .models import (
    ArtifactMetadata, ArtifactType, ArtifactStatus, 
    ProcessingRun, AuditEntry
)
from .storage import ArtifactStorage
from .audit import AuditTrail


class ArtifactManager:
    """Orchestrates artifact storage and audit trail management."""
    
    def __init__(self, 
                 base_path: Union[str, Path],
                 enable_audit: bool = True,
                 auto_cleanup: bool = False):
        """Initialize the Artifact Manager.
        
        Args:
            base_path: Base directory for artifact storage
            enable_audit: Whether to enable audit trail
            auto_cleanup: Whether to automatically clean up temp files
        """
        self.base_path = Path(base_path)
        self.storage = ArtifactStorage(self.base_path / "storage")
        self.enable_audit = enable_audit
        self._lock = threading.Lock()
        self.auto_cleanup = auto_cleanup
        self.logger = logging.getLogger(__name__)
        
        if self.enable_audit:
            self.audit = AuditTrail(self.base_path / "audit")
        
        # Track current processing run
        self.current_run: Optional[ProcessingRun] = None
        
        self.logger.info(f"Initialized ArtifactManager at {self.base_path}")
    
    def start_processing_run(self, 
                           configuration: Optional[Dict[str, Any]] = None) -> ProcessingRun:
        """Start a new processing run.
        
        Args:
            configuration: Configuration for this run
            
        Returns:
            ProcessingRun object
        """
        self.current_run = ProcessingRun(configuration=configuration or {})
        
        if self.enable_audit:
            self.audit.log_operation(
                operation="processing_run",
                action="start",
                user=os.getenv("USER"),
                details={
                    "run_id": self.current_run.run_id,
                    "configuration": self.current_run.configuration
                }
            )
        
        self.logger.info(f"Started processing run {self.current_run.run_id}")
        return self.current_run
    
    def end_processing_run(self, status: ArtifactStatus = ArtifactStatus.COMPLETED):
        """End the current processing run.
        
        Args:
            status: Final status of the run
        """
        if not self.current_run:
            self.logger.warning("No active processing run to end")
            return
        
        self.current_run.complete(status)
        
        if self.enable_audit:
            self.audit.log_operation(
                operation="processing_run",
                action="end",
                user=os.getenv("USER"),
                details={
                    "run_id": self.current_run.run_id,
                    "status": status.value,
                    "duration": str(self.current_run.completed_at - self.current_run.started_at),
                    "input_artifacts": self.current_run.input_artifacts,
                    "output_artifacts": self.current_run.output_artifacts
                },
                success=status == ArtifactStatus.COMPLETED
            )
        
        if self.auto_cleanup:
            self.storage.cleanup_temp()
        
        self.logger.info(f"Ended processing run {self.current_run.run_id} with status {status.value}")
        self.current_run = None
    
    def create_artifact(self,
                       artifact_type: ArtifactType,
                       source_path: Optional[Path] = None,
                       source_artifacts: Optional[List[str]] = None,
                       processing_module: Optional[str] = None,
                       processing_version: Optional[str] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> ArtifactMetadata:
        """Create a new artifact.
        
        Args:
            artifact_type: Type of the artifact
            source_path: Path to the source file (if applicable)
            source_artifacts: List of source artifact IDs
            processing_module: Module that created this artifact
            processing_version: Version of the processing module
            metadata: Additional metadata
            
        Returns:
            ArtifactMetadata object
        """
        with self._lock:
            # Validate inputs
            if source_path and not isinstance(source_path, Path):
                raise ValueError("source_path must be a Path object")
            if metadata and not isinstance(metadata, dict):
                raise ValueError("metadata must be a dictionary")
            if source_artifacts and not isinstance(source_artifacts, list):
                raise ValueError("source_artifacts must be a list")
            
            artifact = ArtifactMetadata(
                artifact_type=artifact_type,
                source_artifacts=source_artifacts or [],
                processing_module=processing_module,
                processing_version=processing_version,
                metadata=metadata or {}
            )
            
            # Store file if provided
            if source_path:
                try:
                    self.storage.store_artifact(source_path, artifact)
                    artifact.update_status(ArtifactStatus.COMPLETED)
                except Exception as e:
                    artifact.update_status(ArtifactStatus.FAILED, str(e))
                    self.logger.error(f"Failed to store artifact: {e}")
                    if self.enable_audit:
                        self.audit.log_operation(
                            operation="artifact_storage",
                            action="store",
                            artifact_id=artifact.artifact_id,
                            module=processing_module,
                            success=False,
                            error_message=str(e)
                        )
                    raise
            else:
                # Save metadata even if no file is provided
                artifact.update_status(ArtifactStatus.COMPLETED)
                self.storage.save_metadata(artifact)
            
            # Update current run
            if self.current_run:
                self.current_run.output_artifacts.append(artifact.artifact_id)
            
            # Log to audit trail
            if self.enable_audit:
                self.audit.log_operation(
                    operation="artifact_creation",
                    action="create",
                artifact_id=artifact.artifact_id,
                module=processing_module,
                details={
                    "type": artifact_type.value,
                    "source_artifacts": source_artifacts,
                    "has_file": source_path is not None
                }
            )
            
            self.logger.info(f"Created artifact {artifact.artifact_id} of type {artifact_type.value}")
            return artifact
    
    def update_artifact_status(self,
                             artifact_id: str,
                             status: ArtifactStatus,
                             error_message: Optional[str] = None):
        """Update the status of an artifact.
        
        Args:
            artifact_id: ID of the artifact
            status: New status
            error_message: Error message if status is FAILED
        """
        with self._lock:
            artifact = self.storage.load_metadata(artifact_id)
            if not artifact:
                self.logger.error(f"Artifact {artifact_id} not found")
                return
            
            artifact.update_status(status, error_message)
            self.storage.save_metadata(artifact)
            
            if self.enable_audit:
                self.audit.log_operation(
                    operation="artifact_update",
                    action="update_status",
                    artifact_id=artifact_id,
                    details={
                        "new_status": status.value,
                        "error_message": error_message
                    },
                    success=status != ArtifactStatus.FAILED
                )
            
            self.logger.info(f"Updated artifact {artifact_id} status to {status.value}")
    
    def get_artifact(self, artifact_id: str) -> Optional[ArtifactMetadata]:
        """Get artifact metadata by ID.
        
        Args:
            artifact_id: ID of the artifact
            
        Returns:
            ArtifactMetadata object or None
        """
        with self._lock:
            artifact = self.storage.load_metadata(artifact_id)
            
            if self.enable_audit:
                self.audit.log_operation(
                    operation="artifact_access",
                action="get_metadata",
                artifact_id=artifact_id,
                success=artifact is not None
            )
            
            return artifact
    
    def get_artifact_file(self, artifact_id: str) -> Optional[Path]:
        """Get the file path for an artifact.
        
        Args:
            artifact_id: ID of the artifact
            
        Returns:
            Path to the artifact file or None
        """
        path = self.storage.retrieve_artifact(artifact_id)
        
        if self.enable_audit:
            self.audit.log_operation(
                operation="artifact_access",
                action="get_file",
                artifact_id=artifact_id,
                success=path is not None
            )
        
        return path
    
    def list_artifacts(self,
                      artifact_type: Optional[ArtifactType] = None,
                      status: Optional[ArtifactStatus] = None,
                      run_id: Optional[str] = None) -> List[ArtifactMetadata]:
        """List artifacts with optional filtering.
        
        Args:
            artifact_type: Filter by type
            status: Filter by status
            run_id: Filter by processing run ID
            
        Returns:
            List of ArtifactMetadata objects
        """
        artifacts = self.storage.list_artifacts(artifact_type, status)
        
        # Filter by run_id if specified
        if run_id:
            artifacts = [
                a for a in artifacts 
                if a.metadata.get("run_id") == run_id
            ]
        
        return artifacts
    
    def link_artifacts(self,
                      source_artifact_ids: List[str],
                      output_artifact_id: str,
                      relationship: str = "derived_from"):
        """Create a relationship between artifacts.
        
        Args:
            source_artifact_ids: List of source artifact IDs
            output_artifact_id: Output artifact ID
            relationship: Type of relationship
        """
        output_artifact = self.get_artifact(output_artifact_id)
        if not output_artifact:
            self.logger.error(f"Output artifact {output_artifact_id} not found")
            return
        
        # Update source artifacts
        output_artifact.source_artifacts.extend(source_artifact_ids)
        output_artifact.metadata[f"{relationship}_artifacts"] = source_artifact_ids
        self.storage.save_metadata(output_artifact)
        
        if self.enable_audit:
            self.audit.log_operation(
                operation="artifact_link",
                action="create_relationship",
                artifact_id=output_artifact_id,
                details={
                    "source_artifacts": source_artifact_ids,
                    "relationship": relationship
                }
            )
        
        self.logger.info(f"Linked {len(source_artifact_ids)} artifacts to {output_artifact_id}")
    
    def get_artifact_lineage(self, artifact_id: str) -> Dict[str, Any]:
        """Get the complete lineage of an artifact.
        
        Args:
            artifact_id: ID of the artifact
            
        Returns:
            Dictionary representing the artifact lineage
        """
        def build_lineage(aid: str, visited: set) -> Dict[str, Any]:
            if aid in visited:
                return {"artifact_id": aid, "circular_reference": True}
            
            visited.add(aid)
            artifact = self.get_artifact(aid)
            
            if not artifact:
                return {"artifact_id": aid, "not_found": True}
            
            lineage = {
                "artifact_id": aid,
                "type": artifact.artifact_type.value,
                "status": artifact.status.value,
                "created_at": artifact.created_at.isoformat(),
                "processing_module": artifact.processing_module,
                "sources": []
            }
            
            for source_id in artifact.source_artifacts:
                lineage["sources"].append(build_lineage(source_id, visited))
            
            return lineage
        
        return build_lineage(artifact_id, set())
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about artifacts and operations.
        
        Returns:
            Dictionary with various statistics
        """
        storage_stats = self.storage.get_storage_stats()
        
        # Get status distribution
        all_artifacts = self.storage.list_artifacts()
        status_dist = {}
        type_dist = {}
        
        for artifact in all_artifacts:
            status_dist[artifact.status.value] = status_dist.get(artifact.status.value, 0) + 1
            type_dist[artifact.artifact_type.value] = type_dist.get(artifact.artifact_type.value, 0) + 1
        
        stats = {
            "storage": storage_stats,
            "artifacts": {
                "total": len(all_artifacts),
                "by_status": status_dist,
                "by_type": type_dist
            }
        }
        
        # Add audit statistics if enabled
        if self.enable_audit:
            error_summary = self.audit.get_error_summary()
            stats["audit"] = {
                "total_errors": error_summary["total_errors"],
                "errors_by_operation": error_summary["errors_by_operation"]
            }
        
        return stats
    
    def cleanup_old_artifacts(self, days_old: int = 30):
        """Clean up artifacts older than specified days.
        
        Args:
            days_old: Remove artifacts older than this many days
        """
        cutoff_date = datetime.now() - timedelta(days=days_old)
        artifacts = self.storage.list_artifacts()
        removed_count = 0
        
        for artifact in artifacts:
            if artifact.created_at < cutoff_date:
                if artifact.file_path and artifact.file_path.exists():
                    artifact.file_path.unlink()
                    removed_count += 1
                    
                    if self.enable_audit:
                        self.audit.log_operation(
                            operation="artifact_cleanup",
                            action="remove_old",
                            artifact_id=artifact.artifact_id,
                            details={"age_days": (datetime.now() - artifact.created_at).days}
                        )
        
        self.logger.info(f"Cleaned up {removed_count} old artifacts")
        return removed_count