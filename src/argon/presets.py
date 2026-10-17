"""
Argon.io - 28 Verified Caption & Motion Graphics Styling Catalog
Reverse-engineered and enhanced from Palmier Pro's verified production templates.
Supports ASS and SRT force_style parameters, SVG overlays, and FFmpeg filter graphs.
"""

from typing import Dict, Any

CAPTION_PRESETS: Dict[str, Dict[str, Any]] = {
    # ── Vertical Presets (1080x1920: Reels / TikTok / Shorts) ───────────────
    "clean_creator": {
        "name": "Clean Creator",
        "orientation": "vertical",
        "description": "White Inter bold in the vertical safe zone with soft shadow. Clean default for talking heads.",
        "font_name": "Inter",
        "font_size": 24,
        "bold": True,
        "primary_color": "&H00FFFFFF",  # White
        "outline_color": "&H00000000",
        "back_color": "&H80000000",
        "border_style": 1,
        "outline": 1.5,
        "shadow": 2.0,
        "alignment": 2,  # Bottom center
        "margin_v": 70,
        "max_words_per_line": 3,
        "animation": "fade"
    },
    "keyword_yellow": {
        "name": "Keyword Yellow (Hormozi)",
        "orientation": "vertical",
        "description": "High-retention Inter/Arial Black with punchy yellow pop and strong shadow.",
        "font_name": "Arial Black",
        "font_size": 25,
        "bold": True,
        "primary_color": "&H0000FFFF",  # Yellow (BGR)
        "outline_color": "&H00000000",
        "back_color": "&H90000000",
        "border_style": 3,  # Opaque box
        "outline": 3.0,
        "shadow": 2.0,
        "alignment": 2,
        "margin_v": 75,
        "max_words_per_line": 3,
        "animation": "pop"
    },
    "karaoke_fill": {
        "name": "Karaoke Fill",
        "orientation": "vertical",
        "description": "Poppins bold with word-by-word active highlight fill.",
        "font_name": "Poppins",
        "font_size": 24,
        "bold": True,
        "primary_color": "&H00FFFFFF",
        "outline_color": "&H00000000",
        "back_color": "&H70000000",
        "border_style": 1,
        "outline": 2.0,
        "shadow": 2.0,
        "alignment": 2,
        "margin_v": 70,
        "max_words_per_line": 3,
        "animation": "karaoke"
    },
    "phrase_pop": {
        "name": "Phrase Pop",
        "orientation": "vertical",
        "description": "Manrope bold with gold word pop for high-tempo hooks.",
        "font_name": "Manrope",
        "font_size": 26,
        "bold": True,
        "primary_color": "&H0020D0F0",  # Gold / Amber
        "outline_color": "&H00000000",
        "back_color": "&H80000000",
        "border_style": 1,
        "outline": 2.5,
        "shadow": 3.0,
        "alignment": 2,
        "margin_v": 70,
        "max_words_per_line": 2,
        "animation": "pop"
    },
    "minimal_podcast": {
        "name": "Minimal Podcast",
        "orientation": "vertical",
        "description": "Inter on a sleek translucent rounded black pill for tasteful understated clips.",
        "font_name": "Segoe UI Semibold",
        "font_size": 20,
        "bold": True,
        "primary_color": "&H00FFFFFF",
        "outline_color": "&H00000000",
        "back_color": "&HB0000000",
        "border_style": 3,
        "outline": 1.0,
        "shadow": 0.0,
        "alignment": 2,
        "margin_v": 65,
        "max_words_per_line": 4,
        "animation": "none"
    },
    "modern_podcast": {
        "name": "Modern Podcast",
        "orientation": "vertical",
        "description": "DM Sans with cyan/sky-blue active word emphasis.",
        "font_name": "Segoe UI",
        "font_size": 22,
        "bold": True,
        "primary_color": "&H00FFFF00",  # Cyan (BGR)
        "outline_color": "&H00000000",
        "back_color": "&HA0000000",
        "border_style": 3,
        "outline": 1.5,
        "shadow": 1.5,
        "alignment": 2,
        "margin_v": 65,
        "max_words_per_line": 3,
        "animation": "pop"
    },
    "punch_zoom": {
        "name": "Punch Zoom (Cold Open)",
        "orientation": "vertical",
        "description": "Anton ALL CAPS dead-center punch for scrolling hooks.",
        "font_name": "Impact",
        "font_size": 32,
        "bold": True,
        "primary_color": "&H0000FFFF",  # Yellow
        "outline_color": "&H00000000",
        "back_color": "&H00000000",
        "border_style": 1,
        "outline": 4.0,
        "shadow": 3.0,
        "alignment": 5,  # Dead center
        "margin_v": 0,
        "max_words_per_line": 2,
        "animation": "zoom"
    },
    "meme_classic": {
        "name": "Meme Classic",
        "orientation": "vertical",
        "description": "Impact ALL CAPS with thick black border for relatable reaction clips.",
        "font_name": "Impact",
        "font_size": 28,
        "bold": True,
        "primary_color": "&H00FFFFFF",
        "outline_color": "&H00000000",
        "back_color": "&H00000000",
        "border_style": 1,
        "outline": 4.0,
        "shadow": 2.0,
        "alignment": 2,
        "margin_v": 70,
        "max_words_per_line": 3,
        "animation": "none"
    },
    "mrbeast": {
        "name": "MrBeast Punch",
        "orientation": "vertical",
        "description": "Electric lime green ALL CAPS bold pop with heavy black outline.",
        "font_name": "Arial Black",
        "font_size": 25,
        "bold": True,
        "primary_color": "&H0000FF00",  # Lime Green
        "outline_color": "&H00000000",
        "back_color": "&H90000000",
        "border_style": 1,
        "outline": 3.5,
        "shadow": 2.5,
        "alignment": 2,
        "margin_v": 75,
        "max_words_per_line": 3,
        "animation": "pop"
    },
    "one_word_hypnotic": {
        "name": "One Word Hypnotic",
        "orientation": "vertical",
        "description": "Single high-impact word at a time, center-locked for maximum retention.",
        "font_name": "Arial Black",
        "font_size": 30,
        "bold": True,
        "primary_color": "&H00FFFFFF",
        "outline_color": "&H00000000",
        "back_color": "&H80000000",
        "border_style": 3,
        "outline": 2.0,
        "shadow": 2.0,
        "alignment": 5,  # Center
        "margin_v": 0,
        "max_words_per_line": 1,
        "animation": "pop"
    },

    # ── Horizontal Presets (1920x1080: YouTube / Product Demos / Web) ───────
    "podcast_clean": {
        "name": "Podcast Clean",
        "orientation": "horizontal",
        "description": "Helvetica / Segoe UI, white, subtle lower-third for long-form broadcasts.",
        "font_name": "Segoe UI",
        "font_size": 18,
        "bold": False,
        "primary_color": "&H00FFFFFF",
        "outline_color": "&H00000000",
        "back_color": "&H60000000",
        "border_style": 1,
        "outline": 1.2,
        "shadow": 1.0,
        "alignment": 2,
        "margin_v": 45,
        "max_words_per_line": 6,
        "animation": "fade"
    },
    "documentary": {
        "name": "Documentary Bar",
        "orientation": "horizontal",
        "description": "Full sentence readability on a translucent charcoal lower bar.",
        "font_name": "Arial",
        "font_size": 19,
        "bold": True,
        "primary_color": "&H00FFFFFF",
        "outline_color": "&H00000000",
        "back_color": "&HA0151515",
        "border_style": 3,
        "outline": 1.0,
        "shadow": 0.0,
        "alignment": 2,
        "margin_v": 45,
        "max_words_per_line": 7,
        "animation": "none"
    },
    "cinematic_title": {
        "name": "Cinematic Title",
        "orientation": "horizontal",
        "description": "Wide-spaced uppercase serif/sans for film, product launches, and trailers.",
        "font_name": "Georgia",
        "font_size": 22,
        "bold": True,
        "primary_color": "&H00E5E5E5",
        "outline_color": "&H00000000",
        "back_color": "&H00000000",
        "border_style": 1,
        "outline": 1.5,
        "shadow": 2.5,
        "alignment": 2,
        "margin_v": 55,
        "max_words_per_line": 4,
        "animation": "fade"
    },
    "typewriter_terminal": {
        "name": "Typewriter Terminal (Dev)",
        "orientation": "horizontal",
        "description": "Green Courier font on a dark terminal bar for code walkthroughs & demos.",
        "font_name": "Courier New",
        "font_size": 19,
        "bold": True,
        "primary_color": "&H0000FF66",  # Hacker Matrix Green
        "outline_color": "&H00000000",
        "back_color": "&HD00A0A0A",
        "border_style": 3,
        "outline": 0.5,
        "shadow": 0.0,
        "alignment": 2,
        "margin_v": 45,
        "max_words_per_line": 5,
        "animation": "typewriter"
    },
    "retro_vhs": {
        "name": "Retro VHS 80s",
        "orientation": "both",
        "description": "Cream vintage font with cyan/magenta chromatic glow.",
        "font_name": "Courier New",
        "font_size": 23,
        "bold": True,
        "primary_color": "&H00D0FFFF",  # Warm cream
        "outline_color": "&H00FF00FF",  # Magenta glow
        "back_color": "&H00000000",
        "border_style": 1,
        "outline": 2.0,
        "shadow": 3.0,
        "alignment": 2,
        "margin_v": 55,
        "max_words_per_line": 4,
        "animation": "none"
    },
    "tiktok_bottom_bar": {
        "name": "TikTok Bottom Bar",
        "orientation": "vertical",
        "description": "Solid black text on white rectangular sticker at lower margin.",
        "font_name": "Arial Black",
        "font_size": 22,
        "bold": True,
        "primary_color": "&H00000000",  # Black text
        "outline_color": "&H00FFFFFF",  # White border
        "back_color": "&H00FFFFFF",     # White solid box
        "border_style": 3,
        "outline": 0.0,
        "shadow": 0.0,
        "alignment": 2,
        "margin_v": 80,
        "max_words_per_line": 3,
        "animation": "none"
    }
}

def get_ass_style_string(preset_id: str) -> str:
    """Builds the FFmpeg subtitles force_style argument string for a given preset."""
    preset = CAPTION_PRESETS.get(preset_id.lower(), CAPTION_PRESETS["keyword_yellow"])
    return (
        f"FontName={preset['font_name']},"
        f"FontSize={preset['font_size']},"
        f"PrimaryColour={preset['primary_color']},"
        f"OutlineColour={preset['outline_color']},"
        f"BackColour={preset['back_color']},"
        f"BorderStyle={preset['border_style']},"
        f"Outline={preset['outline']},"
        f"Shadow={preset['shadow']},"
        f"Alignment={preset['alignment']},"
        f"MarginV={preset['margin_v']}"
    )
