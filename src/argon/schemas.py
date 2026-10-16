"""
Argon.io - Pydantic Data Schemas for Gemini 4 Argon Video Director
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class ClipSegment(BaseModel):
    start_time: str = Field(description="Start timestamp in HH:MM:SS or SS.mmm format (e.g., '00:01:23.500')")
    end_time: str = Field(description="End timestamp in HH:MM:SS or SS.mmm format (e.g., '00:01:58.200')")
    description: str = Field(description="Summary of the action, dialogue, or insight in this clip")
    hook_score: float = Field(default=0.8, description="Viral hook retention score between 0.0 and 1.0")

class ReelPlan(BaseModel):
    title: str = Field(description="Punchy title for the Instagram Reel / YouTube Short")
    viral_hook_text: str = Field(description="First 3-second attention-grabbing text overlay (e.g., 'Stop doing this 🛑')")
    target_platform: Literal["instagram_reel", "youtube_shorts", "tiktok", "instagram_feed"] = Field(
        default="instagram_reel",
        description="Target social media platform format"
    )
    aspect_ratio: Literal["9:16", "4:5", "1:1"] = Field(
        default="9:16",
        description="Aspect ratio for the export"
    )
    clips: List[ClipSegment] = Field(description="Ordered list of video clips to stitch into the reel")
    suggested_audio_mood: Optional[str] = Field(
        default="energetic tech",
        description="Suggested background music style (e.g., 'lofi beat', 'high energy tech', 'dramatic cinematic')"
    )
    caption_style: Literal["hormozi_yellow", "minimal_white", "bold_neon"] = Field(
        default="hormozi_yellow",
        description="Subtitle styling theme"
    )
    instagram_post_caption: str = Field(
        description="Ready-to-copy Instagram post description with 3-5 high-engagement hashtags"
    )
