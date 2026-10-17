"""
Argon.io - Gemini 4 Argon Video Director
Ingests video files, performs deep temporal reasoning, and outputs structured ReelPlan JSON.
"""

import os
import sys
import json
import time
from typing import Optional
from .schemas import ReelPlan, ClipSegment

class GeminiDirector:
    def __init__(self, model_id: str = "gemini-4-argon", api_key: Optional[str] = None):
        self.model_id = model_id
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY environment variable or argument is required to use Gemini 4 Argon.")
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def create_reel_plan(
        self,
        video_path: str,
        user_prompt: str = "Create a viral 30-to-60 second Instagram Reel with high audience retention",
        target_platform: str = "instagram_reel"
    ) -> ReelPlan:
        """
        Send video to Gemini 4 Argon for deep temporal analysis and structured edit planning.
        """
        client = self._get_client()
        print(f"[Argon Director] Uploading {os.path.basename(video_path)} to Gemini API ...", flush=True)
        video_file = client.files.upload(file=video_path)

        # Wait until file finishes processing
        while video_file.state.name == "PROCESSING":
            print("   Waiting for Gemini video processing ...", flush=True)
            time.sleep(3)
            video_file = client.files.get(name=video_file.name)

        if video_file.state.name == "FAILED":
            raise RuntimeError(f"Gemini video processing failed: {video_file.error.message}")

        print(f"[Argon Director] Video active. Submitting to {self.model_id} with tunable reasoning ...", flush=True)

        is_nxndx_style = any(k in user_prompt.lower() for k in ["nxndx", "nandha", "kgisl", "kite", "campus", "vlog", "coimbatore", "gsa", "ambassador", "like me", "my account"])
        
        if is_nxndx_style:
            system_instruction = (
                "You are the dedicated AI Video Director for Nandhakumar Murugan (@nxndx_31), a Google Student Ambassador at KGiSL (Coimbatore). "
                "His signature Instagram Reels style features: "
                "1. Relatable Campus Life / College Vlogs: Time-stamped hooks (e.g. '8:30 AM to 12:50 PM ✨🙏', 'Wait for the 4:30 PM energy 🏃‍♂️💨', 'College polamaa… 😎🔥'), "
                "   witty Tanglish humor ('Campus la student, vibe la DON! 🎒👑'), community question CTAs ('Best part of college Pooja? 👀🪔'), and trending Coimbatore/KITE hashtags (#KGiSL #KITE #Coimbatore #CollegeVlog #TamilReels). "
                "2. Google Ambassador & Tech Innovation: Empowering student builders, Gemini AI models, late-night coding sessions (#GoogleStudentAmbassador #TeamGemini #GSA2026). "
                "Synthesize an exact, timestamped Edit Decision List (ReelPlan) that matches his authentic pacing, energy, and tone."
            )
        else:
            system_instruction = (
                "You are a World-Class Short-Form Video Director for Instagram Reels and YouTube Shorts. "
                "Analyze the uploaded video through time, identify the most engaging viral hook, eliminate dead air, "
                "and synthesize an exact, timestamped Edit Decision List (ReelPlan)."
            )

        prompt = f"""
        User Request: {user_prompt}
        Target Platform: {target_platform}

        Instructions:
        1. Identify the strongest 3-second opening hook that stops scrolling on Instagram.
        2. Select the most impactful 1 to 3 clip segments that form a complete, engaging narrative.
        3. Ensure total duration is between 25 and 55 seconds.
        4. Provide exact start and end timestamps in 'HH:MM:SS.mmm' or 'SS.mmm' format.
        5. Write a high-converting Instagram caption with 3-5 trending hashtags.
        """

        interaction = client.interactions.create(
            model=self.model_id,
            input=[video_file, prompt],
            generation_config={
                "thinking_level": "high",
                "thinking_summaries": "auto",
            },
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": ReelPlan.model_json_schema(),
            },
        )

        raw_json = interaction.steps[-1].content[0].text
        reel_plan = ReelPlan.model_validate_json(raw_json)
        print(f"[Argon Director] Plan synthesized: '{reel_plan.title}' with {len(reel_plan.clips)} clip(s).", flush=True)
        return reel_plan
