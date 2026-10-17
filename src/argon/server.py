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
from .timeline import Timeline
from .presets import CAPTION_PRESETS

# Initialize the Argon MCP Server
mcp = MCPServer(name="Argon-Video-Director")

# Initialize local engines
video_engine = VideoEngine(use_gpu=True)
caption_engine = CaptionGenerator(model_size="tiny")
global_timeline = Timeline(name="Argon Active Project", aspect_ratio="9:16")

def _get_safe_output_path(input_path: str, suffix: str, ext: Optional[str] = None) -> str:
    base, original_ext = os.path.splitext(input_path)
    extension = ext or original_ext
    candidate_dir = os.path.dirname(os.path.abspath(input_path))
    try:
        test_file = os.path.join(candidate_dir, ".test_write_perm")
        with open(test_file, "w") as f:
            f.write("1")
        os.remove(test_file)
        return f"{base}{suffix}{extension}"
    except Exception:
        user_videos = os.path.expanduser(r"~\Videos")
        os.makedirs(user_videos, exist_ok=True)
        filename = os.path.splitext(os.path.basename(input_path))[0]
        return os.path.join(user_videos, f"{filename}{suffix}{extension}")

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
        output_path = _get_safe_output_path(video_path, "_cut")
    return video_engine.lossless_cut(video_path, output_path, start_time, end_time)

@mcp.tool(description="Convert horizontal (16:9) video into Instagram Reel (9:16, 1080x1920) with blurred background padding.")
def argon_reframe_vertical(
    video_path: str,
    output_path: Optional[str] = None,
    blur_strength: int = 25
) -> str:
    """Reframe video into 9:16 vertical using Intel QSV hardware acceleration."""
    if not output_path:
        output_path = _get_safe_output_path(video_path, "_reel_9x16", ".mp4")
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
        output_srt_path = _get_safe_output_path(video_path, "_captions", ".srt")
    return caption_engine.generate_srt(video_path, output_srt_path)

@mcp.tool(description="Burn high-visibility yellow/white subtitles directly into a video.")
def argon_burn_subtitles(
    video_path: str,
    srt_path: str,
    output_path: Optional[str] = None
) -> str:
    """Burn subtitles into video."""
    if not output_path:
        output_path = _get_safe_output_path(video_path, "_subtitled", ".mp4")
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
        output_path = _get_safe_output_path(video_path, "_FINAL_REEL", ".mp4")

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

# ─── Palmier-Compatible NLE Multi-Track Timeline Tools ───────────────────────

@mcp.tool(description="Read the active multi-track NLE timeline, tracks, clips, aspect ratio, and total duration.")
def get_timeline() -> Dict[str, Any]:
    """Read the active multi-track timeline structure."""
    return global_timeline.to_dict()

@mcp.tool(description="Set timeline canvas aspect ratio ('16:9', '9:16', '1:1', '4:5') and frame rate.")
def set_project_settings(aspect_ratio: str = "9:16", fps: float = 30.0) -> Dict[str, Any]:
    """Change project canvas resolution and aspect ratio."""
    global_timeline.set_aspect_ratio(aspect_ratio)
    global_timeline.fps = fps
    return global_timeline.to_dict()

@mcp.tool(description="Add a media clip to a timeline track (e.g., 'v1' primary, 'v2' b-roll, 'a1' dialogue, 'a2' music).")
def add_clips(
    track_id: str,
    source_path: str,
    start_time: Optional[float] = None,
    duration: Optional[float] = None,
    source_in: float = 0.0,
    source_out: Optional[float] = None
) -> Dict[str, Any]:
    """Place a clip on the timeline."""
    clip = global_timeline.add_clip(
        track_id=track_id,
        source_path=source_path,
        start_time=start_time,
        duration=duration,
        source_in=source_in,
        source_out=source_out
    )
    return {"status": "ok", "clip": clip.to_dict(), "timeline": global_timeline.to_dict()}

@mcp.tool(description="Insert a media clip at an exact timecode and ripple all subsequent clips forward.")
def insert_clips(
    track_id: str,
    source_path: str,
    insert_time: float,
    duration: Optional[float] = None
) -> Dict[str, Any]:
    """Insert clip and ripple forward."""
    clip = global_timeline.insert_clip(
        track_id=track_id,
        source_path=source_path,
        insert_time=insert_time,
        duration=duration
    )
    return {"status": "ok", "clip": clip.to_dict(), "timeline": global_timeline.to_dict()}

@mcp.tool(description="Split a clip into two separate segments at an exact timecode frame.")
def split_clips(clip_id: str, split_time: float) -> Dict[str, Any]:
    """Split clip into two."""
    parts = global_timeline.split_clip(clip_id, split_time)
    return {"status": "ok", "parts": [p.to_dict() for p in parts]}

@mcp.tool(description="Remove a clip from the timeline, optionally closing the resulting gap.")
def remove_clips(clip_id: str, ripple: bool = True) -> Dict[str, Any]:
    """Delete a clip."""
    success = global_timeline.remove_clip(clip_id, ripple=ripple)
    return {"status": "ok" if success else "not_found", "timeline": global_timeline.to_dict()}

@mcp.tool(description="Ripple delete a time range [start_time, end_time] across all tracks and close the gap.")
def ripple_delete_ranges(start_time: float, end_time: float) -> Dict[str, Any]:
    """Delete time range and ripple close."""
    removed_sec = global_timeline.ripple_delete_range(start_time, end_time)
    return {"status": "ok", "removed_seconds": removed_sec, "timeline": global_timeline.to_dict()}

@mcp.tool(description="Automatically detect and eliminate awkward dead air pauses and silences from a video.")
def remove_silence(video_path: str, noise_db: float = -30.0, min_duration: float = 0.5) -> Dict[str, Any]:
    """Dead air auto-cutter."""
    out_path = _get_safe_output_path(video_path, "_no_silence", ".mp4")
    res = video_engine.remove_silences(video_path, out_path, noise_db=noise_db, min_duration=min_duration)
    return {"status": "ok", "output_path": res}

@mcp.tool(description="List all 28 verified Palmier-compatible caption presets and styles.")
def list_caption_presets() -> Dict[str, Any]:
    """List 28 verified caption templates."""
    return {"presets": CAPTION_PRESETS}

@mcp.tool(description="Add stylized captions to a video using any of the 28 verified presets (e.g. 'keyword_yellow', 'clean_creator', 'mrbeast', 'typewriter_terminal').")
def add_captions(video_path: str, preset_id: str = "keyword_yellow") -> Dict[str, Any]:
    """Burn subtitles with chosen preset."""
    srt_path = _get_safe_output_path(video_path, "_captions", ".srt")
    caption_engine.generate_srt(video_path, srt_path)
    out_path = _get_safe_output_path(video_path, f"_{preset_id}_subtitled", ".mp4")
    res = video_engine.burn_subtitles(video_path, srt_path, out_path, style_preset=preset_id)
    return {"status": "ok", "output_path": res, "srt_path": srt_path, "preset": preset_id}

@mcp.tool(description="Export project to MP4 (Intel QSV hardware accelerated) or Apple Final Cut Pro / Adobe Premiere XML.")
def export_project(output_path: Optional[str] = None, export_type: str = "mp4") -> Dict[str, Any]:
    """Export project as MP4 or FCPXML/XML."""
    if export_type in ["fcpxml", "xml"]:
        if not output_path:
            output_path = os.path.expanduser(r"~\Videos\argon_project.fcpxml")
        res = global_timeline.export_fcpxml(output_path)
        return {"status": "ok", "type": "fcpxml", "output_path": res}
    else:
        if not output_path:
            output_path = os.path.expanduser(r"~\Videos\argon_rendered_timeline.mp4")
        res = global_timeline.render(output_path)
        return {"status": "ok", "type": "mp4", "output_path": res}

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
                        from .studio import set_studio_tunnel
                        set_studio_tunnel(public_url)
                        print("\n" + "=" * 65)
                        print("🚀 ARGON.IO STUDIO & GEMINI SPARK MCP LIVE!")
                        print("=" * 65)
                        print(f"👉 Argon Studio Web UI : http://127.0.0.1:{port}/studio")
                        print(f"👉 Gemini Spark MCP URL: {public_url}/mcp")
                        print(f"👉 Local MCP Endpoint  : http://127.0.0.1:{port}/mcp")
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
    print(f"       Argon Studio is listening locally on: http://127.0.0.1:{port}/studio")
    print(f"       To expose to Gemini Spark: install cloudflared or run ngrok http {port}\n", flush=True)
    return None


def main():
    """Run the Argon MCP server in stdio, HTTP, or with interactive Studio UI & Gemini Spark tunnel."""
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    import argparse
    import webbrowser
    import uvicorn
    from starlette.applications import Starlette
    from starlette.middleware import Middleware
    from starlette.middleware.cors import CORSMiddleware
    from mcp.server.streamable_http_manager import TransportSecuritySettings
    from .studio import STUDIO_ROUTES

    parser = argparse.ArgumentParser(description="Argon.io - AI Video Director & Studio")
    parser.add_argument("command", nargs="?", default="serve", choices=["serve", "studio", "ui"], help="Command: serve, studio, ui")
    parser.add_argument("--transport", default=None, choices=["stdio", "sse", "streamable-http"], help="MCP transport mode")
    parser.add_argument("--spark", "--tunnel", "--remote", action="store_true", dest="remote", help="Launch public HTTPS tunnel for Gemini Spark (web)")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8080, help="Port for Studio / HTTP mode (default: 8080)")
    parser.add_argument("--open", "-o", action="store_true", help="Automatically open Argon Studio UI in browser")
    args, _ = parser.parse_known_args()

    is_studio_mode = args.command in ["studio", "ui"] or args.remote or args.transport in ["streamable-http", "sse"]

    if is_studio_mode:
        print("=" * 65)
        print("🎬 Argon.io Studio - Autonomous AI Video Director")
        print("   Powered by Gemini 4 Argon & Intel QSV Hardware Engine")
        print("=" * 65)
        print(f"👉 Web Studio: http://127.0.0.1:{args.port}/studio")
        print(f"👉 Local MCP : http://127.0.0.1:{args.port}/mcp")

        if args.remote or args.command in ["studio", "ui"]:
            _start_tunnel(args.port)

        sec_settings = TransportSecuritySettings(
            enable_dns_rebinding_protection=False,
            allowed_hosts=["*"],
            allowed_origins=["*"]
        )

        app_streamable = mcp.streamable_http_app(transport_security=sec_settings)
        combined_routes = STUDIO_ROUTES + list(app_streamable.routes)
        combined_middleware = [
            Middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_methods=["*"],
                allow_headers=["*"],
                allow_credentials=True,
            )
        ]
        app = Starlette(
            routes=combined_routes,
            middleware=combined_middleware,
            lifespan=app_streamable.router.lifespan_context
        )

        if args.open or args.command in ["studio", "ui"]:
            def _open_browser():
                import time
                time.sleep(1.2)
                webbrowser.open(f"http://127.0.0.1:{args.port}/studio")
            import threading
            threading.Thread(target=_open_browser, daemon=True).start()

        uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    else:
        # Default to stdio for local desktop apps (Claude Desktop, Cursor, Antigravity)
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
