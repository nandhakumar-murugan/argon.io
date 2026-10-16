"""
Argon.io - Autonomous AI Video Director & Reels Engine
Powered by Gemini 4 Argon, Intel QSV Hardware Acceleration, and OpenAI Whisper.
"""

__version__ = "0.1.0"

from .engine import VideoEngine
from .captions import CaptionGenerator
from .director import GeminiDirector
from .schemas import ReelPlan, ClipSegment

__all__ = [
    "VideoEngine",
    "CaptionGenerator",
    "GeminiDirector",
    "ReelPlan",
    "ClipSegment"
]
