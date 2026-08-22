import os
import uuid
import datetime
from pathlib import Path
from typing import Tuple, Union
import cv2
import imageio_ffmpeg
import subprocess
import json

from backend.core.config import settings
from backend.video_processing.schemas import VideoMetadata


class VideoIngestionError(Exception):
    """Custom exception raised during video ingestion and validation."""
    pass


class VideoIngestionService:
    """
    Handles ingestion of video files into the system and generates base metadata.
    """

    def __init__(self, upload_dir: Path = None):
        if upload_dir is None:
            upload_dir = Path(settings.USER_UPLOADS_PATH)
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def validate_and_ingest(self, file_source: Union[str, Path]) -> Tuple[Path, VideoMetadata]:
        """
        Validates the video source and generates metadata.
        Returns the resolved file path and VideoMetadata schema.
        """
        video_path = Path(file_source).resolve()

        if not video_path.exists():
            raise VideoIngestionError(f"Video file does not exist at path: {video_path}")

        if not video_path.is_file():
            raise VideoIngestionError(f"Provided path is not a file: {video_path}")

        # Check file extension
        ext = video_path.suffix.lower()
        allowed = getattr(settings, "ALLOWED_EXTENSIONS", ['.mp4', '.mov', '.avi', '.mkv'])
        if ext not in allowed:
            raise ValueError(
                f"Unsupported video format '{ext}'. Allowed extensions: {allowed}"
            )

        # Check file size
        file_size_bytes = video_path.stat().st_size
        if file_size_bytes == 0:
            raise VideoIngestionError("Video file is empty (0 bytes).")

        file_size_mb = file_size_bytes / (1024 * 1024)
        if file_size_mb > settings.MAX_FILE_SIZE_MB:
            raise VideoIngestionError(
                f"File size ({file_size_mb:.1f}MB) exceeds maximum allowed limit ({settings.MAX_FILE_SIZE_MB}MB)."
            )

        # Extract metadata via OpenCV and FFmpeg
        metadata = self._extract_metadata(video_path, file_size_bytes)
        return video_path, metadata

    def _extract_metadata(self, video_path: Path, file_size_bytes: int) -> VideoMetadata:
        """Inspects the video stream and audio stream using OpenCV and FFmpeg binary."""
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise VideoIngestionError(f"Unable to decode video stream from file: {video_path.name}")

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        cap.release()

        if frame_count <= 0 or width <= 0 or height <= 0:
            raise VideoIngestionError(f"Corrupted or invalid video properties for file: {video_path.name}")

        # Calculate duration
        duration_seconds = frame_count / fps if fps > 0 else 0.0
        if duration_seconds > settings.MAX_VIDEO_DURATION_SECONDS:
            raise VideoIngestionError(
                f"Video duration ({duration_seconds:.1f}s) exceeds maximum allowed limit ({settings.MAX_VIDEO_DURATION_SECONDS}s)."
            )

        # Probe audio presence using ffprobe / ffmpeg
        has_audio = self._check_audio_presence(video_path)

        video_id = f"vid_{uuid.uuid4().hex[:12]}"
        created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        return VideoMetadata(
            video_id=video_id,
            filename=video_path.name,
            file_type=video_path.suffix.lstrip(".").lower(),
            file_size_bytes=file_size_bytes,
            duration_seconds=round(duration_seconds, 2),
            width=width,
            height=height,
            fps=round(fps, 2),
            frame_count=frame_count,
            has_audio=has_audio,
            has_video_stream=True,
            created_at=created_at,
        )

    def _check_audio_presence(self, video_path: Path) -> bool:
        """Determines if the video file contains an active audio stream using FFmpeg binary."""
        try:
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            cmd = [ffmpeg_exe, "-i", str(video_path)]
            process = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10
            )
            stderr_output = process.stderr.lower()
            # FFmpeg prints stream information to stderr
            return "audio:" in stderr_output or "stream #0:" in stderr_output and "audio" in stderr_output
        except Exception:
            return False
