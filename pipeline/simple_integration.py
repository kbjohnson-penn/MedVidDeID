"""
Simple integration for MedVidDeID pipeline.

Based on the working pattern from test_with_real_video.py.
"""

import subprocess
import sys
from pathlib import Path
from typing import Dict

from .artifacts import ArtifactManager, ArtifactType, ArtifactStatus


def process_video_pipeline(video_path: Path, output_dir: Path) -> Dict:
    """Process video through complete pipeline.
    
    Simple function that replicates test_with_real_video.py logic.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize artifact manager (like in the test)
    manager = ArtifactManager(
        base_path=output_dir / "artifacts",
        enable_audit=True,
        auto_cleanup=False
    )
    
    # Start processing run (like in the test)
    run = manager.start_processing_run({
        "input_video": str(video_path),
        "pipeline": "video_deid"
    })
    
    video_cli = Path("video_deid/video_deid/cli.py")
    if not video_cli.exists():
        return {"success": False, "error": "video_deid CLI not found"}
    
    try:
        # Step 1: Register input video (from test lines 100-106)
        video_artifact = manager.create_artifact(
            artifact_type=ArtifactType.VIDEO_RAW,
            source_path=video_path,
            processing_module="input_handler",
            metadata={"filename": video_path.name}
        )
        
        # Step 2: Extract keypoints (from test lines 116-140)
        keypoints_path = output_dir / f"keypoints_{video_artifact.artifact_id[:8]}.csv"
        manager.update_artifact_status(video_artifact.artifact_id, ArtifactStatus.IN_PROGRESS)
        
        # Validate paths before subprocess call
        resolved_video = video_path.resolve()
        resolved_keypoints = keypoints_path.resolve() 
        resolved_cli = video_cli.resolve()
        
        if not resolved_video.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        cmd = [
            sys.executable, str(resolved_cli),
            "--operation_type", "extract", 
            "--video", str(resolved_video),
            "--keypoints_csv", str(resolved_keypoints),
            "--progress"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        
        if result.returncode != 0:
            manager.update_artifact_status(video_artifact.artifact_id, ArtifactStatus.FAILED)
            manager.end_processing_run(ArtifactStatus.FAILED)
            return {"success": False, "error": "Keypoint extraction failed"}
        
        # Create keypoints artifact
        keypoints_artifact = manager.create_artifact(
            artifact_type=ArtifactType.VIDEO_KEYPOINTS,
            source_path=keypoints_path,
            source_artifacts=[video_artifact.artifact_id],
            processing_module="video_deid.keypoints"
        )
        
        # Step 3: De-identify video (from test lines 156-181)
        deid_path = output_dir / f"deid_{video_artifact.artifact_id[:8]}.mp4"
        resolved_deid = deid_path.resolve()
        
        cmd = [
            sys.executable, str(resolved_cli),
            "--operation_type", "deid",
            "--video", str(resolved_video),
            "--keypoints_csv", str(resolved_keypoints),
            "--output", str(resolved_deid),
            "--progress"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        
        if result.returncode != 0 or not deid_path.exists():
            manager.update_artifact_status(video_artifact.artifact_id, ArtifactStatus.FAILED)
            manager.end_processing_run(ArtifactStatus.FAILED)
            return {"success": False, "error": "De-identification failed"}
        
        # Create de-identified video artifact
        deid_artifact = manager.create_artifact(
            artifact_type=ArtifactType.VIDEO_DEID,
            source_path=deid_path,
            source_artifacts=[video_artifact.artifact_id, keypoints_artifact.artifact_id],
            processing_module="video_deid.blur"
        )
        
        # Step 4: Extract audio and transcribe (optional)
        transcript_artifact = None
        try:
            # Extract audio from original video
            # Sanitize audio path to prevent command injection
            import re
            safe_id = re.sub(r'[^\w]', '_', video_artifact.artifact_id[:8])
            audio_path = output_dir / f"audio_{safe_id}.mp3"
            resolved_audio = audio_path.resolve()
            
            # Use FFmpeg to extract audio
            audio_cmd = [
                "ffmpeg", "-y", "-i", str(resolved_video), 
                "-vn", "-acodec", "libmp3lame", "-q:a", "4", 
                str(resolved_audio)
            ]
            
            audio_result = subprocess.run(audio_cmd, capture_output=True, text=True, timeout=120)
            
            if audio_result.returncode == 0 and audio_path.exists():
                # Create audio artifact
                audio_artifact = manager.create_artifact(
                    artifact_type=ArtifactType.AUDIO_RAW,
                    source_path=audio_path,
                    source_artifacts=[video_artifact.artifact_id],
                    processing_module="ffmpeg"
                )
                
                # Transcribe audio using WhisperX
                transcribe_script = Path("audio_deid/transcribe.py").resolve()
                if transcribe_script.exists() and transcribe_script.name == "transcribe.py":
                    transcript_cmd = [
                        sys.executable, str(transcribe_script),
                        "--audio", str(resolved_audio),
                        "--output_format", "json",
                        "--output_dir", str(output_dir.resolve())
                    ]
                    
                    transcript_result = subprocess.run(transcript_cmd, capture_output=True, text=True, timeout=300)
                    
                    if transcript_result.returncode == 0 and "SUCCESS" in transcript_result.stdout:
                        # Find transcript file
                        transcript_path = output_dir / f"{audio_path.stem}.json"
                        if not transcript_path.exists():
                            transcript_path = output_dir / "transcript.json"
                        
                        if transcript_path.exists():
                            transcript_artifact = manager.create_artifact(
                                artifact_type=ArtifactType.AUDIO_TRANSCRIPT,
                                source_path=transcript_path,
                                source_artifacts=[audio_artifact.artifact_id],
                                processing_module="whisperx"
                            )
        
        except Exception as e:
            # Transcription is optional, don't fail the whole pipeline
            manager.logger.warning(f"Transcription failed: {e}")
        
        manager.update_artifact_status(video_artifact.artifact_id, ArtifactStatus.COMPLETED)
        manager.end_processing_run(ArtifactStatus.COMPLETED)
        
        result = {
            "success": True,
            "run_id": run.run_id,
            "output_video": str(deid_path),
            "artifacts": {
                "video": video_artifact.artifact_id,
                "keypoints": keypoints_artifact.artifact_id,
                "deid_video": deid_artifact.artifact_id
            }
        }
        
        # Add transcript artifact if created
        if transcript_artifact:
            result["artifacts"]["transcript"] = transcript_artifact.artifact_id
            result["transcript_path"] = str(transcript_artifact.file_path)
        
        return result
        
    except FileNotFoundError as e:
        manager.end_processing_run(ArtifactStatus.FAILED)
        return {"success": False, "error": f"File not found: {e}"}
    except Exception as e:
        manager.end_processing_run(ArtifactStatus.FAILED)
        return {"success": False, "error": "Processing failed"}