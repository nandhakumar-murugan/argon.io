"""
Argon.io - Intel Iris Xe Hardware-Accelerated Video Rendering Engine
Leverages FFmpeg with Intel Quick Sync (QSV) & Direct3D 11 for ultra-fast rendering.
"""

import os
import sys
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional

FFMPEG_PATH = shutil.which("ffmpeg") or r"C:\Users\smnk2\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe"
FFPROBE_PATH = shutil.which("ffprobe") or r"C:\Users\smnk2\AppData\Local\Microsoft\WinGet\Links\ffprobe.exe"

class VideoEngine:
    def __init__(self, use_gpu: bool = True):
        self.ffmpeg = FFMPEG_PATH
        self.ffprobe = FFPROBE_PATH
        self.use_gpu = use_gpu
        self._has_qsv = self._check_qsv_support()

    def _check_qsv_support(self) -> bool:
        """Check if Intel QuickSync Video encoder is supported on this machine."""
        if not self.use_gpu:
            return False
        try:
            res = subprocess.run(
                [self.ffmpeg, "-encoders"],
                capture_output=True,
                text=True,
                errors="ignore"
            )
            return "h264_qsv" in res.stdout
        except Exception:
            return False

    def get_video_metadata(self, video_path: str) -> Dict[str, Any]:
        """Inspect video streams, duration, resolution, and fps via ffprobe."""
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        cmd = [
            self.ffprobe,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)

        video_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
        audio_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), {})
        fmt = data.get("format", {})

        width = int(video_stream.get("width", 0))
        height = int(video_stream.get("height", 0))
        duration = float(fmt.get("duration", 0.0))
        r_frame_rate = video_stream.get("r_frame_rate", "30/1")
        try:
            num, den = map(int, r_frame_rate.split("/"))
            fps = round(num / den, 2) if den != 0 else 30.0
        except Exception:
            fps = 30.0

        return {
            "path": video_path,
            "filename": os.path.basename(video_path),
            "width": width,
            "height": height,
            "duration": duration,
            "fps": fps,
            "codec": video_stream.get("codec_name", "unknown"),
            "has_audio": bool(audio_stream),
            "size_mb": round(os.path.getsize(video_path) / (1024 * 1024), 2)
        }

    def lossless_cut(self, input_path: str, output_path: str, start_time: str, end_time: str) -> str:
        """Cut a clip in milliseconds without re-encoding (stream copy)."""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        cmd = [
            self.ffmpeg,
            "-y",
            "-ss", str(start_time),
            "-to", str(end_time),
            "-i", input_path,
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            output_path
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        return output_path

    def reframe_to_vertical(
        self,
        input_path: str,
        output_path: str,
        target_resolution: str = "1080:1920",
        blur_strength: int = 25
    ) -> str:
        """
        Convert landscape 16:9 video to 9:16 vertical (1080x1920) for Instagram Reels.
        Fills the background with a blurred, scaled version of the video while
        centering the original footage crisply on top.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        tw, th = target_resolution.split(":")

        # Filter graph: background blurred and scaled, foreground scaled to fit width and centered
        filter_complex = (
            f"[0:v]scale={tw}:{th}:force_original_aspect_ratio=increase,"
            f"crop={tw}:{th},boxblur={blur_strength}:5[bg];"
            f"[0:v]scale={tw}:{th}:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2[v]"
        )

        encoder = "h264_qsv" if self._has_qsv else "libx264"
        cmd = [
            self.ffmpeg,
            "-y",
            "-i", input_path,
            "-filter_complex", filter_complex,
            "-map", "[v]",
            "-map", "0:a?",
            "-c:v", encoder,
            "-b:v", "6M",
            "-maxrate", "8M",
            "-bufsize", "12M",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            output_path
        ]

        if encoder == "libx264":
            cmd.extend(["-preset", "fast"])

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError:
            # Fallback to software CPU libx264 if QSV device was busy
            if encoder != "libx264":
                cmd[cmd.index("-c:v") + 1] = "libx264"
                cmd.extend(["-preset", "fast"])
                subprocess.run(cmd, capture_output=True, text=True, check=True)

        return output_path

    def concat_clips(self, clip_paths: List[str], output_path: str) -> str:
        """Stitch multiple video clips together seamlessly."""
        if not clip_paths:
            raise ValueError("No clips provided to concatenate")
        if len(clip_paths) == 1:
            shutil.copyfile(clip_paths[0], output_path)
            return output_path

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
            for p in clip_paths:
                f.write(f"file '{os.path.abspath(p).replace(chr(92), '/')}'\n")
            list_file = f.name

        try:
            cmd = [
                self.ffmpeg,
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", list_file,
                "-c", "copy",
                output_path
            ]
            subprocess.run(cmd, capture_output=True, check=True)
        finally:
            if os.path.exists(list_file):
                os.remove(list_file)

        return output_path

    def burn_subtitles(self, video_path: str, srt_path: str, output_path: str) -> str:
        """Burn subtitles (.srt or .ass) into video with high-visibility styling."""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        clean_srt = os.path.abspath(srt_path).replace("\\", "/").replace(":", "\\:")
        subtitle_filter = (
            f"subtitles='{clean_srt}':force_style='"
            "FontName=Arial Black,FontSize=20,PrimaryColour=&H0000FFFF,"
            "BackColour=&H80000000,BorderStyle=3,Outline=2,Shadow=1,Alignment=2,MarginV=60'"
        )

        encoder = "h264_qsv" if self._has_qsv else "libx264"
        cmd = [
            self.ffmpeg,
            "-y",
            "-i", video_path,
            "-vf", subtitle_filter,
            "-c:v", encoder,
            "-b:v", "6M",
            "-c:a", "copy",
            output_path
        ]
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError:
            if encoder != "libx264":
                cmd[cmd.index("-c:v") + 1] = "libx264"
                cmd.extend(["-preset", "fast"])
                subprocess.run(cmd, capture_output=True, text=True, check=True)

        return output_path
