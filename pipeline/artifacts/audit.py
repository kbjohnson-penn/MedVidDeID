"""Audit trail system for tracking all operations."""

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import threading

from .models import AuditEntry


class AuditTrail:
    """Manages audit trail for all pipeline operations."""
    
    def __init__(self, audit_path: Union[str, Path], rotation_size_mb: int = 100):
        """Initialize audit trail.
        
        Args:
            audit_path: Path to audit log directory
            rotation_size_mb: Size in MB before rotating audit log
        """
        self.audit_path = Path(audit_path)
        self.audit_path.mkdir(parents=True, exist_ok=True)
        self.rotation_size_mb = rotation_size_mb
        self.current_log = self._get_current_log_path()
        self.logger = logging.getLogger(__name__)
        self._lock = threading.Lock()
    
    def _get_current_log_path(self) -> Path:
        """Get path to current audit log file."""
        timestamp = datetime.now().strftime("%Y%m")
        return self.audit_path / f"audit_{timestamp}.jsonl"
    
    def log_operation(self, 
                     operation: str,
                     action: str,
                     artifact_id: Optional[str] = None,
                     user: Optional[str] = None,
                     module: Optional[str] = None,
                     details: Optional[Dict[str, Any]] = None,
                     success: bool = True,
                     error_message: Optional[str] = None) -> AuditEntry:
        """Log an operation to the audit trail.
        
        Args:
            operation: Type of operation (e.g., "artifact_storage", "processing")
            action: Specific action (e.g., "store", "retrieve", "process")
            artifact_id: ID of the artifact involved
            user: User who performed the operation
            module: Module that performed the operation
            details: Additional details about the operation
            success: Whether the operation succeeded
            error_message: Error message if operation failed
            
        Returns:
            The created audit entry
        """
        entry = AuditEntry(
            operation=operation,
            action=action,
            artifact_id=artifact_id,
            user=user,
            module=module,
            details=details or {},
            success=success,
            error_message=error_message
        )
        
        self._write_entry(entry)
        
        # Log to standard logger as well
        log_msg = f"Audit: {operation}.{action} - {'SUCCESS' if success else 'FAILED'}"
        if artifact_id:
            log_msg += f" - Artifact: {artifact_id}"
        if error_message:
            log_msg += f" - Error: {error_message}"
        
        if success:
            self.logger.info(log_msg)
        else:
            self.logger.error(log_msg)
        
        return entry
    
    def _write_entry(self, entry: AuditEntry):
        """Write an audit entry to the log file.
        
        Args:
            entry: Audit entry to write
        """
        with self._lock:
            # Check if we need to rotate
            if self._should_rotate():
                self._rotate_log()
            
            # Write entry as JSON line
            with open(self.current_log, 'a') as f:
                json.dump(entry.to_dict(), f)
                f.write('\n')
    
    def _should_rotate(self) -> bool:
        """Check if current log file should be rotated."""
        if not self.current_log.exists():
            return False
        
        size_mb = self.current_log.stat().st_size / (1024 * 1024)
        return size_mb >= self.rotation_size_mb
    
    def _rotate_log(self):
        """Rotate the current log file."""
        if not self.current_log.exists():
            return
        
        # Find next available rotation number
        base_name = self.current_log.stem
        rotation_num = 1
        while True:
            rotated_path = self.current_log.parent / f"{base_name}.{rotation_num}.jsonl"
            if not rotated_path.exists():
                break
            rotation_num += 1
        
        # Rename current log
        self.current_log.rename(rotated_path)
        self.logger.info(f"Rotated audit log to {rotated_path}")
        
        # Update current log path
        self.current_log = self._get_current_log_path()
    
    def query_audit_trail(self,
                         start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None,
                         operation: Optional[str] = None,
                         action: Optional[str] = None,
                         artifact_id: Optional[str] = None,
                         user: Optional[str] = None,
                         module: Optional[str] = None,
                         success: Optional[bool] = None,
                         limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Query the audit trail with filters.
        
        Args:
            start_time: Filter entries after this time
            end_time: Filter entries before this time
            operation: Filter by operation type
            action: Filter by action
            artifact_id: Filter by artifact ID
            user: Filter by user
            module: Filter by module
            success: Filter by success status
            limit: Maximum number of entries to return
            
        Returns:
            List of audit entries matching the filters
        """
        entries = []
        
        # Get all audit log files
        log_files = sorted(self.audit_path.glob("audit_*.jsonl"), reverse=True)
        
        for log_file in log_files:
            with open(log_file, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        
                        # Apply filters
                        if start_time and datetime.fromisoformat(entry["timestamp"]) < start_time:
                            continue
                        if end_time and datetime.fromisoformat(entry["timestamp"]) > end_time:
                            continue
                        if operation and entry["operation"] != operation:
                            continue
                        if action and entry["action"] != action:
                            continue
                        if artifact_id and entry["artifact_id"] != artifact_id:
                            continue
                        if user and entry["user"] != user:
                            continue
                        if module and entry["module"] != module:
                            continue
                        if success is not None and entry["success"] != success:
                            continue
                        
                        entries.append(entry)
                        
                        if limit and len(entries) >= limit:
                            return entries
                    
                    except json.JSONDecodeError:
                        self.logger.warning(f"Invalid JSON in audit log: {line}")
                        continue
        
        return entries
    
    def get_artifact_history(self, artifact_id: str) -> List[Dict[str, Any]]:
        """Get complete history for a specific artifact.
        
        Args:
            artifact_id: ID of the artifact
            
        Returns:
            List of all audit entries for the artifact
        """
        return self.query_audit_trail(artifact_id=artifact_id)
    
    def get_error_summary(self, 
                         start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Get summary of errors in the audit trail.
        
        Args:
            start_time: Start time for analysis
            end_time: End time for analysis
            
        Returns:
            Dictionary with error statistics
        """
        errors = self.query_audit_trail(
            start_time=start_time,
            end_time=end_time,
            success=False
        )
        
        # Group errors by operation and module
        error_by_operation = {}
        error_by_module = {}
        error_messages = []
        
        for error in errors:
            op = error.get("operation", "unknown")
            mod = error.get("module", "unknown")
            msg = error.get("error_message", "")
            
            error_by_operation[op] = error_by_operation.get(op, 0) + 1
            error_by_module[mod] = error_by_module.get(mod, 0) + 1
            if msg:
                error_messages.append(msg)
        
        return {
            "total_errors": len(errors),
            "errors_by_operation": error_by_operation,
            "errors_by_module": error_by_module,
            "unique_error_messages": list(set(error_messages)),
            "time_range": {
                "start": start_time.isoformat() if start_time else None,
                "end": end_time.isoformat() if end_time else None
            }
        }
    
    def export_audit_trail(self, 
                          output_path: Path,
                          start_time: Optional[datetime] = None,
                          end_time: Optional[datetime] = None,
                          format: str = "json") -> Path:
        """Export audit trail to a file.
        
        Args:
            output_path: Path for the exported file
            start_time: Start time for export
            end_time: End time for export
            format: Export format (json or csv)
            
        Returns:
            Path to the exported file
        """
        entries = self.query_audit_trail(start_time=start_time, end_time=end_time)
        
        if format == "json":
            with open(output_path, 'w') as f:
                json.dump(entries, f, indent=2)
        elif format == "csv":
            if entries:
                keys = entries[0].keys()
                with open(output_path, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=keys)
                    writer.writeheader()
                    writer.writerows(entries)
        else:
            raise ValueError(f"Unsupported export format: {format}")
        
        self.logger.info(f"Exported {len(entries)} audit entries to {output_path}")
        return output_path