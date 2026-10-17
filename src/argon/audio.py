"""
Argon.io - Studio Audio & AI Voiceover Engine
Provides zero-cloud-cost Neural TTS voiceover, auto-ducked background music, and SFX transition stings.
"""

import os
import sys
import asyncio
import tempfile
import subprocess
from typing import Optional, List

from .engine import FFMPEG_PATH

ASSETS_AUDIO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "audio"))
DEFAULT_MUSIC_PATH = os.path.join(ASSETS_AUDIO_DIR, "default_music.mp3")
DEFAULT_WHOOSH_PATH = os.path.join(ASSETS_AUDIO_DIR, "whoosh.mp3")

VOICE_CATALOG = {
    "tech_founder": "en-US-ChristopherNeural",     # Authoritative, confident tech presentation
    "product_specialist": "en-US-JennyNeural",     # Clear, friendly, engaging SaaS walkthrough
    "creator_casual": "en-US-GuyNeural",           # High-energy, casual YouTube/Reels tone
    "indian_tech_male": "en-IN-PrabhatNeural",     # Authentic Indian English male builder voice
    "indian_tech_female": "en-IN-NeerjaNeural",    # Professional Indian English female presenter
    "uk_broadcast": "en-GB-RyanNeural"             # Refined documentary/editorial accent
}

class AudioEngine:
    def __init__(self):
        self.ffmpeg = FFMPEG_PATH

    def generate_voiceover(
        self,
        text: str,
        voice_id: str = "tech_founder",
        output_path: Optional[str] = None
    ) -> str:
        """
        Generate studio-quality neural AI narration using Edge Neural TTS.
        100% free with no monthly subscription credits needed.
        """
        import edge_tts

        voice_name = VOICE_CATALOG.get(voice_id.lower(), voice_id)
        if not output_path:
            user_videos = os.path.expanduser(r"~\Videos")
            os.makedirs(user_videos, exist_ok=True)
            output_path = os.path.join(user_videos, "argon_narration.mp3")

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        async def _speak():
            comm = edge_tts.Communicate(text=text, voice=voice_name, rate="+5%", pitch="+0Hz")
            await comm.save(output_path)

        asyncio.run(_speak())
        return output_path

    def mix_music_with_ducking(
        self,
        video_path: str,
        output_path: str,
        music_path: Optional[str] = None,
        music_volume: float = 0.16,
        duck_volume: float = 0.08
    ) -> str:
        """
        Mixes background music into video with sidechain audio ducking.
        Lowers music volume when dialogue is present, and brings it up during pauses.
        """
        bg_music = music_path or DEFAULT_MUSIC_PATH
        if not os.path.exists(bg_music):
            return video_path  # No music to mix

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # Audio ducking filtergraph using sidechaincompress:
        # [1:a] is background music, looped, volume adjusted
        # [0:a] is primary speech dialogue, used as sidechain key to duck music
        filter_complex = (
            f"[1:a]aloop=loop=-1:size=2e+09,volume={music_volume}[music];"
            f"[music][0:a]sidechaincompress=threshold=0.08:ratio=6:attack=100:release=450[ducked_music];"
            f"[0:a][ducked_music]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )

        cmd = [
            self.ffmpeg,
            "-y",
            "-i", video_path,
            "-i", bg_music,
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            output_path
        ]

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError:
            # Fallback simple amix if sidechain fails on older ffmpeg builds
            simple_filter = f"[1:a]aloop=loop=-1:size=2e+09,volume={duck_volume}[music];[0:a][music]amix=inputs=2:duration=first[aout]"
            cmd_fallback = [
                self.ffmpeg, "-y",
                "-i", video_path, "-i", bg_music,
                "-filter_complex", simple_filter,
                "-map", "0:v", "-map", "[aout]",
                "-c:v", "copy", "-c:a", "aac",
                output_path
            ]
            subprocess.run(cmd_fallback, capture_output=True, text=True, check=True)

        return output_path

    def add_whoosh_stings(
        self,
        video_path: str,
        output_path: str,
        transition_timestamps: List[float],
        whoosh_path: Optional[str] = None
    ) -> str:
        """Adds crisp sound effect whooshes on scene cuts and kinetic title drops."""
        sfx = whoosh_path or DEFAULT_WHOOSH_PATH
        if not os.path.exists(sfx) or not transition_timestamps:
            return video_path

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # Build multi-delayed SFX inputs
        inputs = ["-i", video_path]
        filter_delays = []
        for i, ts in enumerate(transition_timestamps):
            inputs.extend(["-i", sfx])
            delay_ms = int(ts * 1000)
            filter_delays.append(f"[{i+1}:a]adelay={delay_ms}|{delay_ms},volume=0.35[sfx{i}];")

        amix_inputs = "".join(f"[sfx{i}]" for i in range(len(transition_timestamps)))
        filter_graph = "".join(filter_delays) + f"[0:a]{amix_inputs}amix=inputs={len(transition_timestamps)+1}:duration=first[aout]"

        cmd = [self.ffmpeg, "-y"] + inputs + [
            "-filter_complex", filter_graph,
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            output_path
        ]
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return output_path

    mix_background_music = mix_music_with_ducking
