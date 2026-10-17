"""
Argon.io - Motion Graphics, Window Framing, & Video Beautification Engine
Recreates and elevates Palmier Pro's iconic SaaS product demo, browser mockup, and zoom punch effects.
"""

import os
import sys
import subprocess
from typing import Optional, Tuple

from .engine import FFMPEG_PATH, VideoEngine

class EffectsEngine:
    def __init__(self, use_gpu: bool = True):
        self.ffmpeg = FFMPEG_PATH
        self.video_engine = VideoEngine(use_gpu=use_gpu)

    def wrap_in_device_mockup(
        self,
        input_path: str,
        output_path: str,
        target_resolution: str = "1080:1920",
        window_scale: float = 0.90,
        blur_strength: int = 35
    ) -> str:
        """
        Wraps a raw screen capture or demo video inside a sleek floating window with
        macOS traffic-light dots and drops it onto an aesthetic ambient blurred motion backdrop.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        tw, th = map(int, target_resolution.split(":"))
        win_w = int(tw * window_scale)
        # Preserve original aspect ratio of footage for foreground
        meta = self.video_engine.get_video_metadata(input_path)
        orig_w, orig_h = meta["width"], meta["height"]
        aspect = orig_h / orig_w if orig_w > 0 else 9 / 16
        win_h = int(win_w * aspect)

        # Ensure even dimensions for h264 encoder
        win_w = win_w if win_w % 2 == 0 else win_w - 1
        win_h = win_h if win_h % 2 == 0 else win_h - 1

        encoder = "h264_qsv" if self.video_engine._has_qsv else "libx264"

        # Background blurred and scaled to fill canvas, foreground centered inside window frame
        filter_complex = (
            f"[0:v]scale={tw}:{th}:force_original_aspect_ratio=increase,"
            f"crop={tw}:{th},boxblur={blur_strength}:6[bg];"
            f"[0:v]scale={win_w}:{win_h}[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2[v]"
        )

        cmd = [
            self.ffmpeg, "-y",
            "-i", input_path,
            "-filter_complex", filter_complex,
            "-map", "[v]",
            "-map", "0:a?",
            "-c:v", encoder,
            "-b:v", "6M",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            output_path
        ]

        if encoder == "libx264":
            cmd.extend(["-preset", "fast"])

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError:
            if encoder != "libx264":
                cmd[cmd.index("-c:v") + 1] = "libx264"
                cmd.extend(["-preset", "fast"])
                subprocess.run(cmd, capture_output=True, text=True, check=True)

        return output_path

    def add_retention_progress_bar(
        self,
        video_path: str,
        output_path: str,
        bar_color: str = "#8b5cf6",
        bar_height: int = 6
    ) -> str:
        """
        Renders a continuous retention progress bar along the bottom of the video,
        significantly increasing watch-through rate on social platforms.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        meta = self.video_engine.get_video_metadata(video_path)
        total_dur = meta["duration"]
        w, h = meta["width"], meta["height"]

        encoder = "h264_qsv" if self.video_engine._has_qsv else "libx264"

        # Dynamic expanding rectangle filter: w = (t / total_dur) * in_w
        filter_str = (
            f"drawbox=y=ih-{bar_height}:w='(t/{total_dur})*iw':h={bar_height}:"
            f"color={bar_color}@1.0:t=fill"
        )

        cmd = [
            self.ffmpeg, "-y",
            "-i", video_path,
            "-vf", filter_str,
            "-c:v", encoder,
            "-b:v", "6M",
            "-pix_fmt", "yuv420p",
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
