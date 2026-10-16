"""
Argon.io - Local Whisper Auto-Caption Generator
Produces fast, word-level synchronized short-form subtitles for Instagram Reels & Shorts.
"""

import os
import sys
import tempfile
from typing import List, Dict, Any

def _format_timestamp(seconds: float) -> str:
    """Format seconds into SRT timestamp HH:MM:SS,mmm"""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    msecs = int((seconds - int(seconds)) * 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{msecs:03d}"

class CaptionGenerator:
    def __init__(self, model_size: str = "tiny"):
        self.model_size = model_size
        self._model = None

    def _get_model(self):
        if self._model is None:
            import whisper
            print(f"[Argon] Loading local Whisper '{self.model_size}' model ...", flush=True)
            self._model = whisper.load_model(self.model_size)
        return self._model

    def generate_srt(self, audio_or_video_path: str, output_srt_path: str, max_words_per_line: int = 4) -> str:
        """
        Transcribe audio and write punchy, short-line SRT subtitles ideal for vertical videos.
        Splits sentences into small 3-4 word kinetic chunks for high viewer retention.
        """
        model = self._get_model()
        print(f"[Argon] Transcribing speech from {os.path.basename(audio_or_video_path)} ...", flush=True)
        result = model.transcribe(audio_or_video_path, word_timestamps=True)

        srt_entries = []
        counter = 1

        for segment in result.get("segments", []):
            words = segment.get("words", [])
            if not words:
                # Fallback to segment-level timestamp
                start_str = _format_timestamp(segment["start"])
                end_str = _format_timestamp(segment["end"])
                text = segment["text"].strip().upper()
                srt_entries.append(f"{counter}\n{start_str} --> {end_str}\n{text}\n")
                counter += 1
                continue

            # Group words into small punchy chunks
            for i in range(0, len(words), max_words_per_line):
                chunk = words[i:i + max_words_per_line]
                if not chunk:
                    continue
                start_t = chunk[0]["start"]
                end_t = chunk[-1]["end"]
                text = " ".join(w["word"].strip() for w in chunk).upper()
                start_str = _format_timestamp(start_t)
                end_str = _format_timestamp(end_t)
                srt_entries.append(f"{counter}\n{start_str} --> {end_str}\n{text}\n")
                counter += 1

        os.makedirs(os.path.dirname(os.path.abspath(output_srt_path)), exist_ok=True)
        with open(output_srt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(srt_entries))

        print(f"[Argon] Subtitle file generated: {output_srt_path} ({counter - 1} cue lines)", flush=True)
        return output_srt_path
