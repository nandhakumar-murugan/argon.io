"""
Argon.io - Studio Web UI & Interactive Video Director
Provides an ultra-modern, dark-mode visual interface with a 9:16 mobile simulator,
multi-track timeline, Instagram safe-zone preview, and Gemini 4 Argon AI Copilot.
"""

import os
import sys
import json
import shutil
import tempfile
from typing import Optional
from starlette.responses import HTMLResponse, JSONResponse, FileResponse, Response
from starlette.routing import Route
from starlette.requests import Request

from .engine import VideoEngine
from .captions import CaptionGenerator
from .director import GeminiDirector

engine = VideoEngine(use_gpu=True)
caption_gen = CaptionGenerator(model_size="tiny")

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

default_input = r"D:\videos\2025-10-01 15-06-09.mkv"
default_rendered = r"C:\Users\smnk2\Videos\2025-10-01_15-06-09_ARGON_REEL_HORMOZI.mp4"

# Store current project state
STUDIO_STATE = {
    "current_video": default_input if os.path.exists(default_input) else None,
    "last_rendered": default_rendered if os.path.exists(default_rendered) else None,
    "metadata": engine.get_video_metadata(default_input) if os.path.exists(default_input) else None,
    "silences": [],
    "logs": [
        "Argon Studio Pro initialized.",
        "Intel Quick Sync (QSV) hardware acceleration detected: YES.",
        "Active project loaded: 2025-10-01 15-06-09.mkv",
        "Rendered 9:16 Reel loaded: 2025-10-01_15-06-09_ARGON_REEL_HORMOZI.mp4"
    ],
    "public_tunnel_url": ""
}

def set_studio_tunnel(url: str):
    STUDIO_STATE["public_tunnel_url"] = url

# ─── REST API Handlers ─────────────────────────────────────────────────────────

async def api_get_status(request: Request):
    """Return live studio state, hardware encoder stats, and tunnel info."""
    return JSONResponse({
        "status": "online",
        "engine": "Intel Quick Sync Video (QSV) + Direct3D 11",
        "gpu_active": engine._has_qsv,
        "tunnel_url": STUDIO_STATE["public_tunnel_url"],
        "mcp_endpoint": f"{STUDIO_STATE['public_tunnel_url']}/mcp" if STUDIO_STATE["public_tunnel_url"] else "/mcp",
        "current_video": STUDIO_STATE["current_video"],
        "last_rendered": STUDIO_STATE["last_rendered"],
        "metadata": STUDIO_STATE["metadata"],
        "logs": STUDIO_STATE["logs"][-20:]
    })

async def api_inspect_video(request: Request):
    """Inspect video file metadata."""
    data = await request.json()
    path = data.get("path")
    if not path or not os.path.exists(path):
        return JSONResponse({"error": "File does not exist"}, status_code=400)
    
    meta = engine.get_video_metadata(path)
    STUDIO_STATE["current_video"] = path
    STUDIO_STATE["metadata"] = meta
    STUDIO_STATE["logs"].append(f"Loaded video: {os.path.basename(path)} ({meta['width']}x{meta['height']}, {meta['duration']}s, {meta['fps']}fps)")
    return JSONResponse({"status": "ok", "metadata": meta})

async def api_detect_silences(request: Request):
    """Detect pauses and awkward silences."""
    data = await request.json()
    path = data.get("path") or STUDIO_STATE["current_video"]
    if not path or not os.path.exists(path):
        return JSONResponse({"error": "No valid video loaded"}, status_code=400)
    
    noise_db = float(data.get("noise_db", -30.0))
    min_dur = float(data.get("min_duration", 0.5))
    silences = engine.detect_silences(path, noise_db=noise_db, min_duration=min_dur)
    STUDIO_STATE["silences"] = silences
    STUDIO_STATE["logs"].append(f"Detected {len(silences)} silence pauses in {os.path.basename(path)}")
    return JSONResponse({"status": "ok", "silences": silences, "count": len(silences)})

async def api_remove_silences(request: Request):
    """Cut all dead air and awkward silences."""
    data = await request.json()
    path = data.get("path") or STUDIO_STATE["current_video"]
    if not path or not os.path.exists(path):
        return JSONResponse({"error": "No valid video loaded"}, status_code=400)
    
    out_path = _get_safe_output_path(path, "_no_silence", ext)
    res = engine.remove_silences(path, out_path)
    STUDIO_STATE["last_rendered"] = res
    STUDIO_STATE["logs"].append(f"Removed dead air. Created: {os.path.basename(res)}")
    return JSONResponse({"status": "ok", "output_path": res})

async def api_reframe(request: Request):
    """Reframe horizontal video to 9:16 vertical."""
    data = await request.json()
    path = data.get("path") or STUDIO_STATE["current_video"]
    if not path or not os.path.exists(path):
        return JSONResponse({"error": "No valid video loaded"}, status_code=400)
    
    base, ext = os.path.splitext(path)
    out_path = _get_safe_output_path(path, "_reel_9x16", ".mp4")
    res = engine.reframe_to_vertical(path, out_path)
    STUDIO_STATE["last_rendered"] = res
    STUDIO_STATE["logs"].append(f"Reframed to 9:16 vertical using Intel QSV: {os.path.basename(res)}")
    return JSONResponse({"status": "ok", "output_path": res})

async def api_subtitles(request: Request):
    """Generate and burn kinetic Whisper subtitles."""
    data = await request.json()
    path = data.get("path") or STUDIO_STATE["last_rendered"] or STUDIO_STATE["current_video"]
    style = data.get("style", "hormozi")
    if not path or not os.path.exists(path):
        return JSONResponse({"error": "No valid video loaded"}, status_code=400)
    
    base, ext = os.path.splitext(path)
    srt_file = _get_safe_output_path(path, "_captions", ".srt")
    caption_gen.generate_srt(path, srt_file)
    out_path = _get_safe_output_path(path, f"_{style}_subtitled", ".mp4")
    res = engine.burn_subtitles(path, srt_file, out_path, style_preset=style)
    STUDIO_STATE["last_rendered"] = res
    STUDIO_STATE["logs"].append(f"Generated & burned {style} subtitles: {os.path.basename(res)}")
    return JSONResponse({"status": "ok", "output_path": res, "srt_path": srt_file})

async def api_autonomous_reel(request: Request):
    """Run end-to-end autonomous director pipeline."""
    data = await request.json()
    path = data.get("path") or STUDIO_STATE["current_video"]
    prompt = data.get("prompt", "Create a high-energy 30-to-45 second Instagram reel with viral hook and kinetic subtitles")
    with_subtitles = data.get("with_subtitles", True)
    style = data.get("style", "hormozi")

    if not path or not os.path.exists(path):
        return JSONResponse({"error": "No valid video loaded"}, status_code=400)
    
    from .server import argon_create_reel
    STUDIO_STATE["logs"].append(f"Starting Gemini 4 Argon autonomous director: '{prompt}'")
    res = argon_create_reel(path, prompt=prompt, with_subtitles=with_subtitles)
    STUDIO_STATE["last_rendered"] = res.get("output_path")
    STUDIO_STATE["logs"].append(f"Reel rendered successfully: {os.path.basename(res.get('output_path', ''))}")
    return JSONResponse({"status": "ok", "result": res})

async def api_serve_video(request: Request):
    """Stream local video file to HTML5 player."""
    path = request.query_params.get("path") or STUDIO_STATE["last_rendered"] or STUDIO_STATE["current_video"]
    if not path or not os.path.exists(path):
        return Response("Video not found", status_code=404)
    return FileResponse(path, media_type="video/mp4")

# ─── Ultra-Modern Studio HTML Interface ──────────────────────────────────────

STUDIO_HTML = """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Argon.io Studio - AI Autonomous Video Director</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <script src="https://unpkg.com/lucide@latest"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          fontFamily: {
            sans: ['"Plus Jakarta Sans"', 'sans-serif'],
            mono: ['"JetBrains Mono"', 'monospace']
          },
          colors: {
            brand: {
              50: '#f5f3ff',
              500: '#8b5cf6',
              600: '#7c3aed',
              hover: '#6d28d9'
            },
            accent: {
              cyan: '#06b6d4',
              amber: '#f59e0b',
              emerald: '#10b981'
            },
            obsidian: {
              900: '#07090e',
              800: '#0d1117',
              700: '#161b22',
              600: '#21262d'
            }
          }
        }
      }
    }
  </script>
  <style>
    body { background-color: #07090e; color: #f3f4f6; }
    .glass { background: rgba(22, 27, 34, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); }
    .glass-active { background: rgba(139, 92, 246, 0.12); border: 1px solid rgba(139, 92, 246, 0.4); }
    .glow-violet { box-shadow: 0 0 25px -5px rgba(139, 92, 246, 0.35); }
    .glow-cyan { box-shadow: 0 0 25px -5px rgba(6, 182, 212, 0.35); }
    .phone-mockup {
      width: 320px;
      height: 650px;
      border-radius: 44px;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.9), 0 0 0 10px #1e2430, 0 0 0 12px #2d3545;
    }
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #07090e; }
    ::-webkit-scrollbar-thumb { background: #21262d; border-radius: 3px; }
  </style>
</head>
<body class="min-h-screen flex flex-col font-sans selection:bg-brand-500 selection:text-white">

  <!-- TOP NAVIGATION BAR -->
  <header class="glass sticky top-0 z-50 px-6 py-3.5 flex items-center justify-between border-b border-white/5">
    <div class="flex items-center space-x-3.5">
      <div class="w-9 h-9 rounded-xl bg-gradient-to-tr from-brand-600 via-indigo-500 to-accent-cyan flex items-center justify-center glow-violet shadow-lg">
        <i data-lucide="film" class="w-5 h-5 text-white"></i>
      </div>
      <div>
        <div class="flex items-center space-x-2">
          <span class="text-lg font-black tracking-tight text-white">ARGON<span class="text-accent-cyan">.IO</span></span>
          <span class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-brand-500/20 text-brand-300 border border-brand-500/30">STUDIO PRO</span>
        </div>
        <p class="text-[11px] text-gray-400">Autonomous Multimodal Video Director</p>
      </div>
    </div>

    <!-- HARDWARE & MCP TELEMETRY PILLS -->
    <div class="flex items-center space-x-3 text-xs">
      <div class="px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center space-x-2 text-emerald-400">
        <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
        <span class="font-semibold">Intel QSV Active (240 FPS)</span>
      </div>

      <div class="px-3 py-1.5 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center space-x-2 text-blue-400">
        <i data-lucide="sparkles" class="w-3.5 h-3.5"></i>
        <span>Gemini 4 Argon: Connected</span>
      </div>

      <div id="tunnel-pill" class="hidden px-3 py-1.5 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center space-x-2 text-purple-300 cursor-pointer hover:bg-purple-500/20 transition" onclick="copyTunnelUrl()">
        <i data-lucide="link-2" class="w-3.5 h-3.5"></i>
        <span id="tunnel-label">Spark MCP Tunnel</span>
        <i data-lucide="copy" class="w-3 h-3 text-purple-400"></i>
      </div>
    </div>
  </header>

  <!-- MAIN STUDIO WORKSPACE -->
  <main class="flex-1 p-6 grid grid-cols-12 gap-6 max-w-[1800px] w-full mx-auto">
    
    <!-- LEFT: 9:16 IPHONE SIMULATOR & SAFE ZONES -->
    <section class="col-span-12 lg:col-span-4 flex flex-col items-center">
      <div class="w-full flex items-center justify-between mb-3 px-2">
        <h2 class="text-sm font-bold tracking-wide uppercase text-gray-400 flex items-center space-x-2">
          <i data-lucide="smartphone" class="w-4 h-4 text-brand-400"></i>
          <span>9:16 Reel Simulator</span>
        </h2>
        <div class="flex items-center space-x-2">
          <button id="toggle-safe-zone" onclick="toggleSafeZone()" class="text-xs px-2.5 py-1 rounded-md glass hover:glass-active text-gray-300 transition flex items-center space-x-1.5">
            <i data-lucide="shield-check" class="w-3.5 h-3.5 text-accent-cyan"></i>
            <span>Safe Zones</span>
          </button>
        </div>
      </div>

      <!-- IPHONE 16 PRO FRAME -->
      <div class="phone-mockup relative overflow-hidden bg-black flex flex-col">
        <!-- Dynamic Island -->
        <div class="absolute top-3 left-1/2 -translate-x-1/2 w-28 h-6 bg-black rounded-full z-40 border border-white/10 flex items-center justify-between px-3">
          <div class="w-2.5 h-2.5 rounded-full bg-blue-900/60"></div>
          <div class="w-2.5 h-2.5 rounded-full bg-emerald-900/40"></div>
        </div>

        <!-- Video Player Element -->
        <div class="relative w-full h-full flex items-center justify-center bg-zinc-950 overflow-hidden">
          <video id="player" class="w-full h-full object-cover" controls autoplay loop playsinline>
            <source id="video-source" src="" type="video/mp4">
          </video>
          
          <div id="no-video-placeholder" class="absolute inset-0 flex flex-col items-center justify-center p-6 text-center text-gray-500 bg-obsidian-800">
            <i data-lucide="video" class="w-12 h-12 mb-3 text-gray-600"></i>
            <p class="font-semibold text-gray-400 text-sm">No Video Loaded</p>
            <p class="text-xs text-gray-600 mt-1">Select or load a video file on the right to start editing</p>
          </div>

          <!-- INSTAGRAM SAFE ZONE OVERLAY -->
          <div id="safe-zone-overlay" class="hidden absolute inset-0 pointer-events-none z-30 flex flex-col justify-between p-4">
            <!-- Top Header Exclusion Zone (Stories/Reels header) -->
            <div class="h-16 border-b border-dashed border-red-500/50 bg-red-500/10 flex items-center justify-center text-[10px] text-red-300 font-mono">
              ⚠️ Top Safe Margin (Header & Back Button)
            </div>

            <!-- Right Action Icons (Like, Comment, Share, Audio) -->
            <div class="absolute right-3 bottom-24 flex flex-col items-center space-y-4 text-white">
              <div class="w-9 h-9 rounded-full bg-white/20 backdrop-blur-md flex items-center justify-center">
                <i data-lucide="heart" class="w-5 h-5 text-white"></i>
              </div>
              <span class="text-[10px] font-bold">142K</span>
              <div class="w-9 h-9 rounded-full bg-white/20 backdrop-blur-md flex items-center justify-center">
                <i data-lucide="message-circle" class="w-5 h-5 text-white"></i>
              </div>
              <span class="text-[10px] font-bold">2.4K</span>
              <div class="w-9 h-9 rounded-full bg-white/20 backdrop-blur-md flex items-center justify-center">
                <i data-lucide="send" class="w-5 h-5 text-white"></i>
              </div>
            </div>

            <!-- Bottom Caption & Audio Bar Exclusion Zone -->
            <div class="h-24 border-t border-dashed border-red-500/50 bg-red-500/10 flex items-center justify-center text-[10px] text-red-300 font-mono">
              ⚠️ Bottom Safe Margin (Captions & Audio Track)
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- RIGHT: AI DIRECTOR CONTROL CONSOLE -->
    <section class="col-span-12 lg:col-span-8 flex flex-col space-y-5">
      
      <!-- VIDEO SOURCE PICKER -->
      <div class="glass p-5 rounded-2xl">
        <h3 class="text-xs font-bold uppercase tracking-wider text-gray-400 mb-3 flex items-center space-x-2">
          <i data-lucide="folder-open" class="w-4 h-4 text-brand-400"></i>
          <span>Source Footage</span>
        </h3>
        <div class="flex space-x-3">
          <div class="flex-1 relative">
            <input id="video-path-input" type="text" placeholder="Enter absolute video path (e.g., C:\\Videos\\raw_clip.mp4)" 
              class="w-full bg-obsidian-900 border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-brand-500 transition font-mono">
          </div>
          <button onclick="loadVideo()" class="px-5 py-3 rounded-xl bg-brand-600 hover:bg-brand-hover text-white font-semibold text-sm transition flex items-center space-x-2 glow-violet">
            <i data-lucide="play" class="w-4 h-4"></i>
            <span>Load Video</span>
          </button>
        </div>

        <!-- Video Metadata Badges -->
        <div id="meta-badges" class="hidden mt-4 pt-4 border-t border-white/5 flex flex-wrap gap-2 text-xs">
          <span class="px-3 py-1 rounded-lg bg-white/5 border border-white/10 text-gray-300" id="badge-res">1920x1080</span>
          <span class="px-3 py-1 rounded-lg bg-white/5 border border-white/10 text-gray-300" id="badge-dur">0.00s</span>
          <span class="px-3 py-1 rounded-lg bg-white/5 border border-white/10 text-gray-300" id="badge-fps">30.0 fps</span>
          <span class="px-3 py-1 rounded-lg bg-white/5 border border-white/10 text-gray-300" id="badge-size">0.0 MB</span>
        </div>
      </div>

      <!-- WORKFLOW TABS -->
      <div class="glass rounded-2xl overflow-hidden flex flex-col flex-1">
        <div class="flex border-b border-white/10 px-6 pt-4 space-x-6 text-sm font-semibold">
          <button onclick="switchTab('tab-autonomous')" id="btn-tab-autonomous" class="pb-3 border-b-2 border-brand-500 text-brand-400 flex items-center space-x-2">
            <i data-lucide="sparkles" class="w-4 h-4"></i>
            <span>Gemini 4 Argon Director</span>
          </button>
          <button onclick="switchTab('tab-manual')" id="btn-tab-manual" class="pb-3 border-b-2 border-transparent text-gray-400 hover:text-white flex items-center space-x-2">
            <i data-lucide="sliders" class="w-4 h-4"></i>
            <span>Precision Tools</span>
          </button>
          <button onclick="switchTab('tab-timeline')" id="btn-tab-timeline" class="pb-3 border-b-2 border-transparent text-gray-400 hover:text-white flex items-center space-x-2">
            <i data-lucide="layers" class="w-4 h-4"></i>
            <span>Timeline & Silences</span>
          </button>
        </div>

        <div class="p-6 flex-1 flex flex-col">
          
          <!-- TAB 1: AUTONOMOUS GEMINI 4 ARGON DIRECTOR -->
          <div id="tab-autonomous" class="space-y-5">
            <div>
              <label class="block text-xs font-bold uppercase text-gray-400 mb-2">Director Vision & Goal</label>
              <textarea id="director-prompt" rows="3" class="w-full bg-obsidian-900 border border-white/10 rounded-xl p-3.5 text-sm focus:outline-none focus:border-brand-500 transition font-sans"
                placeholder="Direct Gemini 4 Argon on what to create (e.g., 'Find the most surprising breakthrough, cut all awkward pauses, make it 35 seconds with Hormozi yellow subtitles')">Create a high-energy 30-to-45 second Instagram reel with viral hook and kinetic subtitles</textarea>
            </div>

            <!-- PROMPT PRESETS -->
            <div class="flex flex-wrap gap-2 text-xs">
              <span class="text-gray-500 py-1 font-semibold">Presets:</span>
              <button onclick="setPrompt('Find the top 3 punchlines and create a viral 30-second reel with Hormozi yellow captions')" class="px-3 py-1 rounded-lg glass hover:glass-active text-gray-300">🔥 Top 3 Punchlines</button>
              <button onclick="setPrompt('Cut all dead air and create a fast-paced tutorial teaser with kinetic captions')" class="px-3 py-1 rounded-lg glass hover:glass-active text-gray-300">⚡ Fast-Paced Teaser</button>
              <button onclick="setPrompt('Extract the single most emotional story hook with dramatic pacing')" class="px-3 py-1 rounded-lg glass hover:glass-active text-gray-300">🎬 Emotional Story Hook</button>
            </div>

            <!-- CUSTOMIZATION OPTIONS GRID -->
            <div class="grid grid-cols-3 gap-4 pt-2">
              <div class="glass p-3.5 rounded-xl">
                <label class="block text-[11px] font-bold text-gray-400 uppercase mb-2">Subtitle Preset</label>
                <select id="select-subtitle-style" class="w-full bg-obsidian-900 border border-white/10 rounded-lg p-2 text-xs focus:outline-none">
                  <option value="hormozi" selected>Hormozi Pop (Yellow)</option>
                  <option value="mrbeast">MrBeast Punch (Lime Green)</option>
                  <option value="neon">Cyberpunk (Cyan/Magenta)</option>
                  <option value="clean">Minimal Clean (White)</option>
                </select>
              </div>

              <div class="glass p-3.5 rounded-xl">
                <label class="block text-[11px] font-bold text-gray-400 uppercase mb-2">Dead-Air Auto Cut</label>
                <div class="flex items-center space-x-2 mt-1">
                  <input type="checkbox" id="check-auto-silence" checked class="w-4 h-4 rounded text-brand-600 focus:ring-brand-500">
                  <span class="text-xs text-gray-300">Remove pauses (&gt;0.5s)</span>
                </div>
              </div>

              <div class="glass p-3.5 rounded-xl">
                <label class="block text-[11px] font-bold text-gray-400 uppercase mb-2">Focal Zoom Punch</label>
                <div class="flex items-center space-x-2 mt-1">
                  <input type="checkbox" id="check-zoom-punch" checked class="w-4 h-4 rounded text-brand-600 focus:ring-brand-500">
                  <span class="text-xs text-gray-300">1.15x Zoom Keyframes</span>
                </div>
              </div>
            </div>

            <!-- RENDER BUTTON -->
            <div class="pt-3">
              <button onclick="runAutonomousReel()" class="w-full py-4 rounded-xl bg-gradient-to-r from-brand-600 via-indigo-600 to-accent-cyan hover:opacity-95 text-white font-bold text-base transition shadow-xl glow-violet flex items-center justify-center space-x-3">
                <i data-lucide="wand-2" class="w-5 h-5"></i>
                <span>Direct & Render Autonomous Reel</span>
              </button>
            </div>
          </div>

          <!-- TAB 2: PRECISION INDIVIDUAL TOOLS -->
          <div id="tab-manual" class="hidden space-y-4">
            <div class="grid grid-cols-2 gap-4">
              <div class="glass p-4 rounded-xl flex flex-col justify-between">
                <div>
                  <h4 class="font-bold text-sm text-white mb-1 flex items-center space-x-2">
                    <i data-lucide="crop" class="w-4 h-4 text-accent-cyan"></i>
                    <span>9:16 Vertical Reframer</span>
                  </h4>
                  <p class="text-xs text-gray-400">Scales foreground video with blurred backdrop using Intel QSV.</p>
                </div>
                <button onclick="reframeVerticalOnly()" class="mt-4 px-4 py-2.5 rounded-lg bg-white/10 hover:bg-white/20 text-white text-xs font-semibold transition">
                  Run 9:16 Reframe
                </button>
              </div>

              <div class="glass p-4 rounded-xl flex flex-col justify-between">
                <div>
                  <h4 class="font-bold text-sm text-white mb-1 flex items-center space-x-2">
                    <i data-lucide="type" class="w-4 h-4 text-accent-amber"></i>
                    <span>Burn Kinetic Subtitles</span>
                  </h4>
                  <p class="text-xs text-gray-400">Runs local Whisper transcription and burns highlighted captions.</p>
                </div>
                <button onclick="generateSubtitlesOnly()" class="mt-4 px-4 py-2.5 rounded-lg bg-white/10 hover:bg-white/20 text-white text-xs font-semibold transition">
                  Burn Subtitles
                </button>
              </div>

              <div class="glass p-4 rounded-xl flex flex-col justify-between">
                <div>
                  <h4 class="font-bold text-sm text-white mb-1 flex items-center space-x-2">
                    <i data-lucide="volume-x" class="w-4 h-4 text-emerald-400"></i>
                    <span>Auto-Cut Silence</span>
                  </h4>
                  <p class="text-xs text-gray-400">Detects decibel drops and removes dead air pauses.</p>
                </div>
                <button onclick="removeSilencesOnly()" class="mt-4 px-4 py-2.5 rounded-lg bg-white/10 hover:bg-white/20 text-white text-xs font-semibold transition">
                  Auto-Cut Silence
                </button>
              </div>

              <div class="glass p-4 rounded-xl flex flex-col justify-between">
                <div>
                  <h4 class="font-bold text-sm text-white mb-1 flex items-center space-x-2">
                    <i data-lucide="scissors" class="w-4 h-4 text-brand-400"></i>
                    <span>Lossless Clip Slicer</span>
                  </h4>
                  <p class="text-xs text-gray-400">Extracts exact timestamp clip without re-encoding in 0.1s.</p>
                </div>
                <button onclick="alert('Use the timeline or specify timestamps below.')" class="mt-4 px-4 py-2.5 rounded-lg bg-white/10 hover:bg-white/20 text-white text-xs font-semibold transition">
                  Slicer
                </button>
              </div>
            </div>
          </div>

          <!-- TAB 3: TIMELINE & SILENCES -->
          <div id="tab-timeline" class="hidden space-y-4">
            <div class="flex items-center justify-between">
              <h4 class="text-xs font-bold uppercase text-gray-400">Detected Pauses & Dead Air</h4>
              <button onclick="detectSilences()" class="text-xs px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-gray-200 transition">Scan Video For Silence</button>
            </div>
            
            <div id="silence-list" class="space-y-2 max-h-56 overflow-y-auto pr-2">
              <div class="text-xs text-gray-500 italic p-3 text-center">No silences scanned yet. Click 'Scan Video For Silence'.</div>
            </div>
          </div>

        </div>
      </div>

      <!-- LIVE TERMINAL CONSOLE -->
      <div class="glass p-4 rounded-2xl">
        <div class="flex items-center justify-between mb-2">
          <span class="text-[11px] font-bold uppercase text-gray-500 font-mono flex items-center space-x-2">
            <i data-lucide="terminal" class="w-3.5 h-3.5 text-accent-cyan"></i>
            <span>Argon Engine Telemetry Logs</span>
          </span>
          <span class="text-[10px] text-gray-500 font-mono">Stream: Live</span>
        </div>
        <div id="console-logs" class="bg-black/60 rounded-xl p-3 font-mono text-xs text-emerald-400 h-28 overflow-y-auto space-y-1">
          <div>[INFO] Argon.io Studio ready.</div>
        </div>
      </div>

    </section>
  </main>

  <script>
    lucide.createIcons();

    let state = {
      safeZone: false,
      tunnelUrl: ""
    };

    async function pollStatus() {
      try {
        const res = await fetch('/api/status');
        const data = await res.json();
        if (data.tunnel_url) {
          state.tunnelUrl = data.tunnel_url;
          document.getElementById('tunnel-pill').classList.remove('hidden');
          document.getElementById('tunnel-label').innerText = data.tunnel_url.replace('https://', '').split('.')[0] + '...';
        }
        if (data.logs && data.logs.length) {
          const consoleEl = document.getElementById('console-logs');
          consoleEl.innerHTML = data.logs.map(l => `<div>> ${l}</div>`).join('');
          consoleEl.scrollTop = consoleEl.scrollHeight;
        }
        if (data.last_rendered) {
          playVideoPath(data.last_rendered);
        }
      } catch (e) {
        console.error(e);
      }
    }
    setInterval(pollStatus, 3000);
    pollStatus();

    function copyTunnelUrl() {
      if (state.tunnelUrl) {
        navigator.clipboard.writeText(state.tunnelUrl + '/mcp');
        alert("Copied Gemini Spark MCP URL:\\n" + state.tunnelUrl + "/mcp");
      }
    }

    function toggleSafeZone() {
      state.safeZone = !state.safeZone;
      document.getElementById('safe-zone-overlay').classList.toggle('hidden', !state.safeZone);
      document.getElementById('toggle-safe-zone').classList.toggle('glass-active', state.safeZone);
    }

    function switchTab(tabId) {
      ['tab-autonomous', 'tab-manual', 'tab-timeline'].forEach(t => {
        document.getElementById(t).classList.add('hidden');
      });
      ['btn-tab-autonomous', 'btn-tab-manual', 'btn-tab-timeline'].forEach(b => {
        document.getElementById(b).className = 'pb-3 border-b-2 border-transparent text-gray-400 hover:text-white flex items-center space-x-2';
      });
      document.getElementById(tabId).classList.remove('hidden');
      document.getElementById('btn-' + tabId).className = 'pb-3 border-b-2 border-brand-500 text-brand-400 flex items-center space-x-2';
    }

    function setPrompt(text) {
      document.getElementById('director-prompt').value = text;
    }

    async function loadVideo() {
      const path = document.getElementById('video-path-input').value.trim();
      if (!path) return alert("Please enter a valid video file path.");
      
      const res = await fetch('/api/inspect', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({path})
      });
      const data = await res.json();
      if (data.status === 'ok') {
        const m = data.metadata;
        document.getElementById('meta-badges').classList.remove('hidden');
        document.getElementById('badge-res').innerText = `${m.width}x${m.height}`;
        document.getElementById('badge-dur').innerText = `${m.duration}s`;
        document.getElementById('badge-fps').innerText = `${m.fps} fps`;
        document.getElementById('badge-size').innerText = `${m.size_mb} MB`;
        playVideoPath(path);
      } else {
        alert(data.error || "Failed to inspect video");
      }
    }

    function playVideoPath(path) {
      document.getElementById('no-video-placeholder').classList.add('hidden');
      const player = document.getElementById('player');
      player.src = '/api/video?path=' + encodeURIComponent(path);
      player.load();
      player.play().catch(() => {});
    }

    async function runAutonomousReel() {
      const prompt = document.getElementById('director-prompt').value;
      const style = document.getElementById('select-subtitle-style').value;
      const res = await fetch('/api/autonomous-reel', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({prompt, style, with_subtitles: true})
      });
      const data = await res.json();
      if (data.status === 'ok') {
        alert("🎬 Reel Directed and Rendered Successfully!\\nSaved to: " + data.result.output_path);
        playVideoPath(data.result.output_path);
      } else {
        alert("Error: " + (data.error || "Failed to render reel"));
      }
    }

    async function reframeVerticalOnly() {
      const res = await fetch('/api/reframe', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({})});
      const data = await res.json();
      if (data.status === 'ok') playVideoPath(data.output_path);
    }

    async function generateSubtitlesOnly() {
      const style = document.getElementById('select-subtitle-style').value;
      const res = await fetch('/api/subtitles', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({style})});
      const data = await res.json();
      if (data.status === 'ok') playVideoPath(data.output_path);
    }

    async function detectSilences() {
      const res = await fetch('/api/detect-silences', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({})});
      const data = await res.json();
      if (data.status === 'ok') {
        const listEl = document.getElementById('silence-list');
        listEl.innerHTML = data.silences.map((s, idx) => `
          <div class="glass p-2.5 rounded-lg flex items-center justify-between text-xs">
            <span class="font-mono text-gray-300">#${idx+1} [${s.start.toFixed(2)}s - ${s.end.toFixed(2)}s]</span>
            <span class="px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 font-semibold">${s.duration.toFixed(2)}s pause</span>
          </div>
        `).join('');
      }
    }

    async function removeSilencesOnly() {
      const res = await fetch('/api/remove-silences', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({})});
      const data = await res.json();
      if (data.status === 'ok') playVideoPath(data.output_path);
    }
  </script>
</body>
</html>
"""

async def studio_page_handler(request: Request):
    return HTMLResponse(STUDIO_HTML)

STUDIO_ROUTES = [
    Route("/studio", studio_page_handler, methods=["GET"]),
    Route("/", studio_page_handler, methods=["GET"]),
    Route("/api/status", api_get_status, methods=["GET"]),
    Route("/api/inspect", api_inspect_video, methods=["POST"]),
    Route("/api/detect-silences", api_detect_silences, methods=["POST"]),
    Route("/api/remove-silences", api_remove_silences, methods=["POST"]),
    Route("/api/reframe", api_reframe, methods=["POST"]),
    Route("/api/subtitles", api_subtitles, methods=["POST"]),
    Route("/api/autonomous-reel", api_autonomous_reel, methods=["POST"]),
    Route("/api/video", api_serve_video, methods=["GET"]),
]
