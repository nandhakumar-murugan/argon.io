"""
Argon.io - Model Context Protocol (MCP) Server
Allows AI agents (Gemini Spark, Antigravity, Claude, Cursor) to autonomously direct & edit videos.
"""

import os
import sys
import tempfile
from typing import Optional, Dict, Any
from mcp.server.mcpserver import MCPServer

from .engine import VideoEngine
from .captions import CaptionGenerator
from .director import GeminiDirector
from .schemas import ReelPlan

# Initialize the Argon MCP Server
mcp = MCPServer(name="Argon-Video-Director")

# Initialize local engines
video_engine = VideoEngine(use_gpu=True)
caption_engine = CaptionGenerator(model_size="base")

@mcp.tool(description="Inspect video resolution, fps, duration, and codecs.")
def argon_get_video_info(video_path: str) -> Dict[str, Any]:
    """Inspect video file metadata."""
    return video_engine.get_video_metadata(video_path)

@mcp.tool(description="Losslessly cut a video segment in milliseconds without re-encoding.")
def argon_lossless_cut(
    video_path: str,
    start_time: str,
    end_time: str,
    output_path: Optional[str] = None
) -> str:
    """Cut a video segment losslessly."""
    if not output_path:
        base, ext = os.path.splitext(video_path)
        output_path = f"{base}_cut{ext}"
    return video_engine.lossless_cut(video_path, output_path, start_time, end_time)

@mcp.tool(description="Convert horizontal (16:9) video into Instagram Reel (9:16, 1080x1920) with blurred background padding.")
def argon_reframe_vertical(
    video_path: str,
    output_path: Optional[str] = None,
    blur_strength: int = 25
) -> str:
    """Reframe video into 9:16 vertical using Intel QSV hardware acceleration."""
    if not output_path:
        base, ext = os.path.splitext(video_path)
        output_path = f"{base}_reel_9x16{ext}"
    return video_engine.reframe_to_vertical(
        input_path=video_path,
        output_path=output_path,
        target_resolution="1080:1920",
        blur_strength=blur_strength
    )

@mcp.tool(description="Transcribe video using local OpenAI Whisper and generate short kinetic SRT subtitles.")
def argon_generate_captions(
    video_path: str,
    output_srt_path: Optional[str] = None
) -> str:
    """Generate kinetic SRT subtitles from video audio."""
    if not output_srt_path:
        base, _ = os.path.splitext(video_path)
        output_srt_path = f"{base}_captions.srt"
    return caption_engine.generate_srt(video_path, output_srt_path)

@mcp.tool(description="Burn high-visibility yellow/white subtitles directly into a video.")
def argon_burn_subtitles(
    video_path: str,
    srt_path: str,
    output_path: Optional[str] = None
) -> str:
    """Burn subtitles into video."""
    if not output_path:
        base, ext = os.path.splitext(video_path)
        output_path = f"{base}_subtitled{ext}"
    return video_engine.burn_subtitles(video_path, srt_path, output_path)

@mcp.tool(description="Autonomous end-to-end Reel Creator: Directs, slices, reframes (9:16), and subtitles a video for Instagram.")
def argon_create_reel(
    video_path: str,
    prompt: str = "Create a high-energy 30-to-45 second Instagram reel highlighting the main breakthrough",
    output_path: Optional[str] = None,
    with_subtitles: bool = True
) -> Dict[str, Any]:
    """
    Autonomous pipeline:
    1. Gemini 4 Argon creates temporal ReelPlan
    2. Slices the clips via FFmpeg
    3. Stitches together
    4. Reframes to 9:16 vertical (1080x1920)
    5. Burns Whisper subtitles
    """
    if not output_path:
        base, ext = os.path.splitext(video_path)
        output_path = f"{base}_FINAL_REEL{ext}"

    temp_dir = tempfile.mkdtemp(prefix="argon_reel_")
    director = GeminiDirector()

    # Step 1: Gemini 4 Argon Planning
    try:
        plan = director.create_reel_plan(video_path=video_path, user_prompt=prompt)
    except Exception as e:
        # Fallback plan if offline / no API key: take first 30 seconds
        meta = video_engine.get_video_metadata(video_path)
        dur = min(meta["duration"], 30.0)
        from .schemas import ClipSegment
        plan = ReelPlan(
            title=f"Highlight Reel: {os.path.basename(video_path)}",
            viral_hook_text="Check this out 🚀",
            clips=[ClipSegment(start_time="00:00:00", end_time=f"00:00:{int(dur):02d}", description="Opening hook", hook_score=0.9)],
            instagram_post_caption=f"Full demo of {os.path.basename(video_path)}! #Tech #AI #Coding"
        )

    # Step 2: Slice clips
    cut_files = []
    for i, clip in enumerate(plan.clips):
        cut_file = os.path.join(temp_dir, f"clip_{i}.mp4")
        video_engine.lossless_cut(video_path, cut_file, clip.start_time, clip.end_time)
        cut_files.append(cut_file)

    # Step 3: Concat clips
    merged_file = os.path.join(temp_dir, "merged.mp4")
    video_engine.concat_clips(cut_files, merged_file)

    # Step 4: Reframe to 9:16 vertical
    vertical_file = os.path.join(temp_dir, "vertical_9x16.mp4")
    video_engine.reframe_to_vertical(merged_file, vertical_file)

    # Step 5: Generate & Burn Subtitles (Optional)
    final_render = vertical_file
    if with_subtitles:
        srt_file = os.path.join(temp_dir, "captions.srt")
        try:
            caption_engine.generate_srt(merged_file, srt_file)
            subtitled_file = os.path.join(temp_dir, "subtitled.mp4")
            video_engine.burn_subtitles(vertical_file, srt_file, subtitled_file)
            final_render = subtitled_file
        except Exception as e:
            print(f"[Argon] Subtitle step warning: {e}", flush=True)

    # Move final render to output_path
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    import shutil
    shutil.copyfile(final_render, output_path)

    return {
        "status": "success",
        "output_path": output_path,
        "title": plan.title,
        "viral_hook": plan.viral_hook_text,
        "aspect_ratio": "9:16 (1080x1920)",
        "duration_seconds": video_engine.get_video_metadata(output_path)["duration"],
        "instagram_caption": plan.instagram_post_caption,
    }

def _start_tunnel(port: int):
    """Starts a public secure tunnel (Cloudflare or ngrok) for web clients like Gemini Spark."""
    import shutil
    import subprocess
    import threading
    import re

    cf_bin = shutil.which("cloudflared") or shutil.which("cloudflared.exe")
    if not cf_bin:
        for candidate in [
            r"C:\Program Files (x86)\cloudflared\cloudflared.exe",
            r"C:\Program Files\cloudflared\cloudflared.exe",
            os.path.expanduser("~/.cloudflared/cloudflared.exe"),
        ]:
            if os.path.exists(candidate):
                cf_bin = candidate
                break

    if cf_bin:
        try:
            proc = subprocess.Popen(
                [cf_bin, "tunnel", "--protocol", "http2", "--url", f"http://127.0.0.1:{port}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace"
            )

            def _reader(pipe):
                for line in iter(pipe.readline, ""):
                    m = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
                    if m:
                        public_url = m.group(0)
                        print("\n" + "=" * 65)
                        print("🚀 ARGON.IO IS LIVE & READY FOR GEMINI SPARK!")
                        print("=" * 65)
                        print(f"👉 Gemini Spark MCP URL: {public_url}/mcp")
                        print(f"👉 Local Direct URL    : http://127.0.0.1:{port}/mcp")
                        print("=" * 65)
                        print("\n📋 How to connect in Gemini Spark (Web):")
                        print("1. Go to Gemini Spark (https://gemini.google.com/spark)")
                        print("2. Navigate to Settings > Connected Apps / MCP Tools")
                        print("3. Add Custom MCP Server and paste the URL above")
                        print("4. Done! Gemini 4 Argon can now direct and edit reels directly on your PC!\n")
                        print("=" * 65 + "\n", flush=True)

            threading.Thread(target=_reader, args=(proc.stderr,), daemon=True).start()
            return proc
        except Exception as e:
            print(f"[Argon] Cloudflare tunnel warning: {e}", flush=True)

    print(f"\n[Info] Cloudflare tunnel binary not found in standard paths.")
    print(f"       Argon is listening locally on: http://127.0.0.1:{port}/mcp")
    print(f"       To expose to Gemini Spark: install cloudflared or run ngrok http {port}\n", flush=True)
    return None


def main():
    """Run the Argon MCP server in stdio, HTTP, or with automatic Gemini Spark tunnel."""
    import argparse
    from mcp.server.streamable_http_manager import TransportSecuritySettings

    parser = argparse.ArgumentParser(description="Argon.io - AI Video Director MCP Server")
    parser.add_argument("command", nargs="?", default="serve", help="Command: serve")
    parser.add_argument("--transport", default=None, choices=["stdio", "sse", "streamable-http"], help="MCP transport mode")
    parser.add_argument("--spark", "--tunnel", "--remote", action="store_true", dest="remote", help="Launch public HTTPS tunnel for Gemini Spark (web)")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8080, help="Port for HTTP/SSE mode (default: 8080)")
    args, _ = parser.parse_known_args()

    # Determine transport
    if args.remote or args.transport in ["streamable-http", "sse"]:
        transport = args.transport or "streamable-http"
        print("=" * 65)
        print("🎬 Argon.io - Autonomous AI Video Director MCP Server")
        print("   Powered by Gemini 4 Argon & Intel QSV Hardware Engine")
        print("=" * 65)
        print(f"Local Server: http://{args.host}:{args.port}/mcp (Streamable HTTP)")

        if args.remote:
            _start_tunnel(args.port)

        sec_settings = TransportSecuritySettings(
            enable_dns_rebinding_protection=False,
            allowed_hosts=["*"],
            allowed_origins=["*"]
        )

        mcp.run(
            transport=transport,
            host=args.host,
            port=args.port,
            transport_security=sec_settings
        )
    else:
        # Default to stdio for local desktop apps (Claude Desktop, Cursor, Antigravity)
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
