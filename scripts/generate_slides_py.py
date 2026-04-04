#!/usr/bin/env python3
"""
generate_slides_py.py
Generates carousel slides: Pinterest backgrounds + smart Pillow text overlay.

Rules (never break these):
- NO blanket dark overlay. The photo IS the slide.
- Analyze each image individually before placing text.
- Text goes in naturally dark/empty zones only.
- Right edge (last 13% of frame) is dead zone -- platform UI buttons live there.
- Targeted brightness reduction only where text sits, with gradient fade.
- Gold is ALWAYS RGB(255, 252, 0) = #fffc00. Never any other shade.
- Every slide gets fresh analysis. No carry-over from previous slides.
"""

import argparse
import json, sys, urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageStat

# ── PATHS ─────────────────────────────────────────────────────────────────────
ROOT      = Path(__file__).parent.parent
CONFIG    = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
FONTS_DIR = ROOT / "fonts"
FONTS_DIR.mkdir(exist_ok=True)

# Creator handle — read from config, never hardcoded
CREATOR_HANDLE = "@" + CONFIG.get("creator", {}).get("name", "yourcreator").lstrip("@")

# ── VISUAL IDENTITY ───────────────────────────────────────────────────────────
W, H       = 1080, 1350
BLACK      = (8,   8,   8)
CREAM      = (237, 232, 223)
GOLD       = (255, 252,  0)      # #fffc00 -- the ONLY gold, always
WHITE_BODY = (245, 240, 232)
DIM        = (175, 170, 162)
JPEG_Q     = 96

# Safe zone: exclude right 13% (TikTok/Instagram like/comment/share strip)
SAFE_RIGHT_MARGIN = 0.13
SAFE_W = int(W * (1 - SAFE_RIGHT_MARGIN))  # 939 px

# Footer area at bottom that text must not overlap
FOOTER_RESERVE = 140

# ── FONTS ─────────────────────────────────────────────────────────────────────
FONT_URLS = {
    "Poppins-Bold.ttf":      "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Bold.ttf",
    "Poppins-Light.ttf":     "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Light.ttf",
    "Poppins-Medium.ttf":    "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Medium.ttf",
    "IBMPlexMono-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/ibmplexmono/IBMPlexMono-Regular.ttf",
    "LibreBaskerville-Bold.ttf": "https://fonts.gstatic.com/s/librebaskerville/v24/kmKUZrc3Hgbbcjq75U4uslyuy4kn0olVQ-LglH6T17ujFgkSCQ.ttf",
    "Anton-Regular.ttf":         "https://fonts.gstatic.com/s/anton/v27/1Ptgg87LROyAm0K0.ttf",
}

def ensure_fonts():
    for fname, url in FONT_URLS.items():
        fpath = FONTS_DIR / fname
        if not fpath.exists():
            print(f"  Downloading {fname}...")
            try:
                urllib.request.urlretrieve(url, fpath)
            except Exception as e:
                print(f"  [WARN] Could not download {fname}: {e} — will fall back to Poppins-Bold")
    # Hook headline: Anton (ultra-condensed bold sans-serif — the viral news style).
    # Falls back to Poppins-Bold if download failed.
    anton = FONTS_DIR / "Anton-Regular.ttf"
    hook_font_path = str(anton) if anton.exists() else str(FONTS_DIR / "Poppins-Bold.ttf")
    return {
        "bold":          ImageFont.truetype(str(FONTS_DIR / "Poppins-Bold.ttf"),      68),
        "hook_headline": ImageFont.truetype(hook_font_path, 96),
        "body":          ImageFont.truetype(str(FONTS_DIR / "Poppins-Light.ttf"),     44),
        "label":         ImageFont.truetype(str(FONTS_DIR / "Poppins-Medium.ttf"),    32),
        "footer":        ImageFont.truetype(str(FONTS_DIR / "IBMPlexMono-Regular.ttf"), 26),
    }

# ── IMAGE ANALYSIS ────────────────────────────────────────────────────────────

def analyze_zones(img: Image.Image, prefer_dark: bool = True) -> str:
    """
    Divide image into top / middle / bottom zones (within safe area).
    prefer_dark=True  → return darkest zone  (for dark slides, white text)
    prefer_dark=False → return lightest zone (for light slides, black text)
    Footer area and right edge are excluded from analysis.
    """
    gray = img.convert("L")
    footer_top = H - FOOTER_RESERVE

    top    = gray.crop((0, 0,            SAFE_W, H // 3))
    middle = gray.crop((0, H // 3,       SAFE_W, 2 * H // 3))
    bottom = gray.crop((0, 2 * H // 3,   SAFE_W, footer_top))

    scores = {
        "top":    ImageStat.Stat(top).mean[0],
        "middle": ImageStat.Stat(middle).mean[0],
        "bottom": ImageStat.Stat(bottom).mean[0],
    }
    if prefer_dark:
        chosen = min(scores, key=scores.get)   # darkest zone → white text reads well
    else:
        chosen = max(scores, key=scores.get)   # lightest zone → black text reads well
    print(f"    Zone analysis: top={scores['top']:.0f} mid={scores['middle']:.0f} bot={scores['bottom']:.0f} -> {chosen}")
    return chosen


def zone_text_y(zone: str, block_h: int) -> int:
    """Return the y coordinate where the text block should start for this zone."""
    PAD_TOP = 100
    if zone == "top":
        return PAD_TOP
    elif zone == "bottom":
        return H - FOOTER_RESERVE - block_h - 20
    else:  # middle
        return (H - FOOTER_RESERVE - block_h) // 2


def darken_text_zone(img: Image.Image, y_start: int, y_end: int) -> Image.Image:
    """
    Apply targeted brightness reduction (factor 0.50) only where text will sit.
    Soft gradient fade of 60px at top and bottom of the zone.
    The rest of the photo is untouched.
    """
    FACTOR   = 0.50
    FADE_PX  = 60
    ZONE_PAD = 40

    top_    = max(0, y_start - ZONE_PAD)
    bottom_ = min(H, y_end   + ZONE_PAD)
    zone_h  = bottom_ - top_
    if zone_h <= 0:
        return img

    img = img.copy().convert("RGB")

    # Crop zone, darken it
    zone_crop = img.crop((0, top_, W, bottom_))
    darkened  = ImageEnhance.Brightness(zone_crop).enhance(FACTOR)

    # Build per-row alpha mask for soft gradient edges
    mask = Image.new("L", (W, zone_h), 0)
    for y in range(zone_h):
        if y < FADE_PX:
            alpha = int(255 * y / FADE_PX)
        elif y > zone_h - FADE_PX:
            alpha = int(255 * (zone_h - y) / FADE_PX)
        else:
            alpha = 255
        mask.paste(alpha, (0, y, W, y + 1))

    img.paste(darkened, (0, top_), mask)
    return img


def lighten_text_zone(img: Image.Image, y_start: int, y_end: int) -> Image.Image:
    """
    Apply a cream wash to the text zone on light slides.
    Ensures the zone is bright enough for black text regardless of what the photo looks like.
    Soft gradient fade at top and bottom edges — texture still shows through.
    """
    ALPHA_MAX = 175   # ~69% cream wash at peak — strong but texture shows
    FADE_PX   = 60
    ZONE_PAD  = 40

    top_    = max(0, y_start - ZONE_PAD)
    bottom_ = min(H, y_end   + ZONE_PAD)
    zone_h  = bottom_ - top_
    if zone_h <= 0:
        return img

    img = img.copy().convert("RGB")

    cream_layer = Image.new("RGB", (W, zone_h), CREAM)

    mask = Image.new("L", (W, zone_h), 0)
    for y in range(zone_h):
        if y < FADE_PX:
            alpha = int(ALPHA_MAX * y / FADE_PX)
        elif y > zone_h - FADE_PX:
            alpha = int(ALPHA_MAX * (zone_h - y) / FADE_PX)
        else:
            alpha = ALPHA_MAX
        mask.paste(alpha, (0, y, W, y + 1))

    img.paste(cream_layer, (0, top_), mask)
    return img


def apply_hook_panel(img: Image.Image, panel_start: float = 0.38) -> tuple:
    """
    Hook slide: photo fully visible on top, smooth gradient fade to black below.
    Gradient starts at panel_start and reaches full black at ~72% of height.
    Photo bleeds into darkness naturally — no hard cut line.
    Returns (img, dark_zone_y) where dark_zone_y is where text can safely start.
    """
    img        = img.copy().convert("RGB")
    overlay    = Image.new("RGB", (W, H), (0, 0, 0))
    mask       = Image.new("L",   (W, H), 0)

    fade_start = int(H * panel_start)
    fade_end   = int(H * 0.72)       # fully black by 72%

    for y in range(H):
        if y <= fade_start:
            alpha = 0
        elif y >= fade_end:
            alpha = 255
        else:
            progress = (y - fade_start) / (fade_end - fade_start)
            # ease-in curve so the fade feels natural, not linear
            alpha = int(255 * (progress ** 1.6))
        mask.paste(alpha, (0, y, W, y + 1))

    img.paste(overlay, mask=mask)
    dark_zone_y = int(H * 0.62)      # reliable text zone: well into the dark area
    return img, dark_zone_y


def draw_badge(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont,
               x: int, y: int) -> int:
    """
    Draw a small blue badge pill (NEWS-style) with white text.
    Returns the y-coordinate immediately below the badge (for headline placement).
    """
    BADGE_BG    = (30, 100, 220)   # strong blue
    BADGE_PAD_X = 18
    BADGE_PAD_Y = 8
    RADIUS      = 6

    bbox = draw.textbbox((0, 0), text, font=font)
    tw   = bbox[2] - bbox[0]
    th   = bbox[3] - bbox[1]
    rx0  = x
    ry0  = y
    rx1  = x + tw + BADGE_PAD_X * 2
    ry1  = y + th + BADGE_PAD_Y * 2
    draw.rounded_rectangle([rx0, ry0, rx1, ry1], radius=RADIUS, fill=BADGE_BG)
    draw.text((x + BADGE_PAD_X, y + BADGE_PAD_Y), text, font=font, fill=(255, 255, 255))
    return ry1 + 16


def quality_check(img: Image.Image, text_y: int, block_h: int, is_dark: bool) -> tuple:
    """
    Measure average brightness of the text zone after all overlays.
    Returns (passed: bool, brightness: float).
    Dark slides (white text): zone should be dark (brightness < 110).
    Light slides (black text): zone should be light (brightness > 145).
    """
    y0   = max(0, text_y - 10)
    y1   = min(H - FOOTER_RESERVE, text_y + block_h + 10)
    crop = img.convert("L").crop((0, y0, SAFE_W, y1))
    brightness = ImageStat.Stat(crop).mean[0]
    passed = (brightness < 110) if is_dark else (brightness > 145)
    label  = f"{'dark' if is_dark else 'light'} zone — {'PASS' if passed else 'WARN'}"
    print(f"    Quality check: brightness={brightness:.0f} [{label}]")
    return passed, brightness


def draw_shadowed_text(draw: ImageDraw.ImageDraw, pos: tuple, text: str,
                       font, fill: tuple, is_dark: bool, offset: int = 2) -> None:
    """
    Draw text with a subtle offset shadow for extra contrast against any background.
    Dark slides (white text)  → black shadow offset +2px
    Light slides (black text) → white/cream shadow offset +2px
    """
    x, y = pos
    shadow = (0, 0, 0) if is_dark else (245, 240, 232)
    draw.text((x + offset, y + offset), text, font=font, fill=shadow)
    draw.text((x, y), text, font=font, fill=fill)


def draw_gold_text(draw: ImageDraw.ImageDraw, pos: tuple, text: str,
                   font, is_dark: bool) -> None:
    """
    Draw gold text with crisp, sharp edges regardless of background.

    Root cause of the blur problem:
    Gold (255,252,0) has high luminance. On dark slides, anti-aliased edge pixels
    blend gold→black = high contrast = crisp. On light slides, edge pixels blend
    gold→cream = both high luminance = muddy, smeared appearance.

    Fix: on light slides, draw a 1px dark stroke first (8-direction offset) to
    define glyph boundaries, then draw gold on top. On dark slides, plain gold
    is already crisp — no stroke needed.
    """
    x, y = pos
    if not is_dark:
        # 1px dark stroke — defines edges against the cream background
        stroke_color = (25, 25, 25)
        for dx, dy in [(-1,-1),(0,-1),(1,-1),(-1,0),(1,0),(-1,1),(0,1),(1,1)]:
            draw.text((x + dx, y + dy), text, font=font, fill=stroke_color)
    draw.text((x, y), text, font=font, fill=GOLD)


def find_emphasis_word(headline: str) -> str | None:
    """
    Find the word intended for gold (ALL CAPS = emphasis word).
    Returns the lowercased form for post-lowercase matching, or None.

    Rule: 2+ alpha chars, fully uppercase, punctuation stripped before check.
    Example: "Stop performing. Start SHIPPING." -> "shipping"
    Fallback if None: caller uses last-word-of-last-line rule.
    """
    for word in headline.split():
        core = word.rstrip('.,!?:;')
        if len(core) >= 2 and core.isalpha() and core == core.upper():
            return core.lower()
    return None

# ── TEXT UTILITIES ────────────────────────────────────────────────────────────

def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_w: int,
              draw: ImageDraw.ImageDraw) -> list[str]:
    words = text.split()
    lines, line = [], []
    for word in words:
        test = " ".join(line + [word])
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_w:
            line.append(word)
        else:
            if line:
                lines.append(" ".join(line))
            line = [word]
    if line:
        lines.append(" ".join(line))
    return lines

# ── TEXT OVERLAY ──────────────────────────────────────────────────────────────

SWIPE_LABELS = {
    "en": "SWIPE FOR MORE  ›",
    "fr": "BALAYEZ POUR PLUS  ›",
    "es": "DESLIZA PARA MÁS  ›",
}

RED_TRENDING = (220, 38, 38)   # vivid red pill on hook slide


def add_overlay(bg_path: Path, slide: dict, fonts: dict, out_path: Path,
                total_slides: int, lang: str = "en"):
    """
    Full-image single overlay system.

    ONE color layer over the ENTIRE photo — no zone-specific treatment.
    The photo shows through consistently tinted everywhere, then text sits on top.

    Dark slides (ODD):  62% black overlay  → deep dark canvas, white text pops.
    Light slides (EVEN): 65% cream overlay → warm light canvas, black text pops.

    Zone analysis is used only for TEXT PLACEMENT (top / middle / bottom),
    not for contrast — the full overlay already guarantees uniform readability.

    Text shadow: 2px offset shadow in contrasting color on all text elements.
    Quality check: safety net — if the tint somehow fails, emergency 20% pass added.
    """
    n            = slide.get("number", 1)
    is_hook      = (slide.get("role") == "hook")
    is_dark      = (n % 2 == 1)   # ODD = dark | EVEN = light
    tint_color   = BLACK if is_dark else CREAM
    hook_panel_y = int(H * 0.60)  # default; overwritten if bg exists

    if bg_path and bg_path.exists():
        img = Image.open(bg_path).convert("RGB")
        img = img.resize((W, H), Image.LANCZOS)

        if is_hook:
            # ── HOOK slide: hard-cut black panel, photo untouched on top ─────
            # Matches the 'Anthropic just dropped' viral style:
            # photo completely clean in top 57%, solid black below.
            img, hook_panel_y = apply_hook_panel(img, panel_start=0.60)
            print(f"    Hook panel: hard cut at y={hook_panel_y}")
        else:
            # ── All other slides: full-image color overlay ───────────────────
            # Dark: 62% black  → photo visible but deeply tinted, white text pops.
            # Light: 65% cream → photo visible with warm cream wash, black text pops.
            BASE_ALPHA = 0.62 if is_dark else 0.65
            tint       = Image.new("RGB", (W, H), tint_color)
            img        = Image.blend(img, tint, BASE_ALPHA)
            print(f"    Full overlay: {'dark' if is_dark else 'light'} at {int(BASE_ALPHA*100)}%")
    else:
        img = Image.new("RGB", (W, H), BLACK if is_dark else CREAM)

    headline = slide.get("headline", "")
    body     = slide.get("body", "")

    PAD   = 28 if is_hook else 80
    MAX_W = SAFE_W - PAD * 2

    # Detect ALL CAPS emphasis word BEFORE lowercasing (it gets lost after)
    emphasis_word = find_emphasis_word(headline)

    is_cta = slide.get("role") == "cta"
    if is_hook:
        headline = headline.upper()   # ALL CAPS — viral news/editorial style
    elif not is_cta:
        headline = headline.lower()
    body = body.lower()

    # ── Dynamic headline font sizing ──────────────────────────────────────────
    # Hook slides use the large serif display font (editorial/news feel).
    # Regular slides use Poppins Bold. Both reduce size until ≤3 lines.
    tmp_img  = img.copy()
    tmp_draw = ImageDraw.Draw(tmp_img)

    if is_hook:
        anton = FONTS_DIR / "Anton-Regular.ttf"
        hook_fpath = str(anton) if anton.exists() else str(FONTS_DIR / "Poppins-Bold.ttf")
        # Target ≤2 lines — try sizes from largest down until it fits
        for size in [112, 96, 84, 74, 64]:
            headline_font = ImageFont.truetype(hook_fpath, size)
            h_lines       = wrap_text(headline, headline_font, MAX_W, tmp_draw)
            if len(h_lines) <= 2:
                break
    else:
        headline_font = fonts["bold"]
        h_lines       = wrap_text(headline, headline_font, MAX_W, tmp_draw)
        if len(h_lines) > 3:
            for size in [58, 52, 46]:
                headline_font = ImageFont.truetype(str(FONTS_DIR / "Poppins-Bold.ttf"), size)
                h_lines       = wrap_text(headline, headline_font, MAX_W, tmp_draw)
                if len(h_lines) <= 3:
                    break

    # Hook slides: lines nearly touching for editorial density; others: standard
    h_line_gap = 2 if is_hook else 18
    h_line_h   = tmp_draw.textbbox((0, 0), "Ag", font=headline_font)[3] + h_line_gap

    # ── Body font: 40px baseline, shrink if wraps > 2 lines ──────────────────
    body_font = ImageFont.truetype(str(FONTS_DIR / "Poppins-Light.ttf"), 40)
    b_lines   = []
    for para in body.split("\n"):
        b_lines += wrap_text(para, body_font, MAX_W, tmp_draw)
    if len(b_lines) > 2:
        body_font = ImageFont.truetype(str(FONTS_DIR / "Poppins-Light.ttf"), 34)
        b_lines   = []
        for para in body.split("\n"):
            b_lines += wrap_text(para, body_font, MAX_W, tmp_draw)

    b_line_h = tmp_draw.textbbox((0, 0), "Ag", font=body_font)[3] + 14

    GAP     = 32
    block_h = len(h_lines) * h_line_h + (GAP + len(b_lines) * b_line_h if b_lines else 0)

    # ── Zone analysis — for text PLACEMENT only (not contrast) ──────────────
    # Hook slides always anchor text at the bottom (news editorial pattern).
    # Other slides: zone analysis finds the compositionally open area.
    BADGE_H = 0
    if is_hook:
        zone   = "bottom"
        # Text starts below separator (3px) + brand mark (~36px) + gap (18px)
        text_y = hook_panel_y + 3 + 36 + 18
        # No generic clamp for hooks — panel placement is intentional
        print(f"    Hook: panel_y={hook_panel_y}, text_y={text_y}")
    else:
        zone   = analyze_zones(img, prefer_dark=is_dark) if (bg_path and bg_path.exists()) else "middle"
        text_y = zone_text_y(zone, block_h)
        text_y = max(80, min(text_y, H - FOOTER_RESERVE - block_h - 20))

    # ── Quality safety-net ────────────────────────────────────────────────────
    # Full overlay should always pass. If it somehow fails, add emergency 20% tint.
    passed, brightness = quality_check(img, text_y, block_h, is_dark)
    if not passed:
        print(f"    [AUTO-FIX] Brightness={brightness:.0f} — adding emergency tint pass...")
        emergency = Image.new("RGB", (W, H), tint_color)
        img = Image.blend(img, emergency, 0.20)
        passed2, brightness2 = quality_check(img, text_y, block_h, is_dark)
        if not passed2 and not is_dark and brightness2 < 100:
            print(f"    [OVERRIDE] Zone still dark ({brightness2:.0f}) — switching to white text")
            is_dark = True

    # ── Draw text ─────────────────────────────────────────────────────────────
    draw       = ImageDraw.Draw(img)
    text_color = WHITE_BODY if is_dark else BLACK
    TEXT_X     = PAD

    # Hook headlines are centered on the full image width; others left-aligned.
    def line_x(line_text, font):
        if is_hook:
            lb = draw.textbbox((0, 0), line_text, font=font)
            return (W - (lb[2] - lb[0])) // 2 - lb[0]
        return TEXT_X

    # Gold span rule:
    # - If a marked ALL CAPS word exists → gold that single word (author intent).
    # - Hook fallback → gold the last 2 words of the last line (verb+noun CTA feel).
    # - Non-hook fallback → gold the last word of the last line.
    # Gold drawn WITHOUT shadow — shadow muddies the color.
    emphasis_drawn = False
    y = text_y
    for line_idx, line in enumerate(h_lines):
        is_last_line = (line_idx == len(h_lines) - 1)
        words        = line.split()

        # Determine gold span [gold_start, gold_end] (inclusive word indices)
        gold_start = gold_end = None
        if is_hook:
            # Hook slides: ALWAYS last 2 words of last line — CTA phrase feel, no exceptions
            if is_last_line and not emphasis_drawn and words:
                gold_end   = len(words) - 1
                gold_start = max(0, len(words) - 2)
        else:
            # Non-hook: respect marked ALL CAPS word first, fall back to last word
            if emphasis_word and not emphasis_drawn:
                for wi, w in enumerate(words):
                    if w.rstrip('.,!?:;').lower() == emphasis_word:
                        gold_start = gold_end = wi
                        break
            if gold_start is None and is_last_line and not emphasis_drawn and words:
                gold_start = gold_end = len(words) - 1

        if gold_start is not None:
            before_words = words[:gold_start]
            gold_words   = words[gold_start:gold_end + 1]
            after_words  = words[gold_end + 1:]
            gold_text    = " ".join(gold_words)
            full_line    = (" ".join(before_words) + " " if before_words else "") + gold_text + (" " + " ".join(after_words) if after_words else "")
            x = line_x(full_line, headline_font)
            if before_words:
                before_text = " ".join(before_words) + " "
                draw_shadowed_text(draw, (x, y), before_text, headline_font, text_color, is_dark)
                bw = draw.textbbox((0, 0), before_text, font=headline_font)
                x += bw[2] - bw[0]
            draw_gold_text(draw, (x, y), gold_text, headline_font, is_dark)
            gw = draw.textbbox((0, 0), gold_text, font=headline_font)
            x += gw[2] - gw[0]
            if after_words:
                after_text = " " + " ".join(after_words)
                draw_shadowed_text(draw, (x, y), after_text, headline_font, text_color, is_dark)
            emphasis_drawn = True
        else:
            draw_shadowed_text(draw, (line_x(line, headline_font), y), line, headline_font, text_color, is_dark)

        y += h_line_h

    if b_lines:
        y += GAP
        for line in b_lines:
            draw_shadowed_text(draw, (TEXT_X, y), line, body_font, text_color, is_dark)
            y += b_line_h

    if is_hook:
        # ── Hook footer: red TRENDING pill + SWIPE pill ───────────────────────
        # No separator line — the hard panel cut is already a clean boundary.

        # Red "TRENDING" pill — centered in hook panel (replaces @handle)
        trend_font  = fonts["label"]
        tb          = draw.textbbox((0, 0), "TRENDING", font=trend_font)
        t_w, t_h    = tb[2] - tb[0], tb[3] - tb[1]
        tp_x, tp_y  = 24, 10
        tpill_w     = t_w + tp_x * 2
        tpill_h     = t_h + tp_y * 2
        tpill_x     = (W - tpill_w) // 2
        tpill_y     = hook_panel_y + 8
        draw.rounded_rectangle(
            [tpill_x, tpill_y, tpill_x + tpill_w, tpill_y + tpill_h],
            radius=tpill_h // 2, fill=RED_TRENDING,
        )
        draw.text((tpill_x + tp_x - tb[0], tpill_y + tp_y - tb[1]),
                  "TRENDING", font=trend_font, fill=(255, 255, 255))

        # Language-aware "SWIPE FOR MORE ›" pill — white border, centered
        cta         = SWIPE_LABELS.get(lang, SWIPE_LABELS["en"])
        cta_font    = fonts["label"]
        cb          = draw.textbbox((0, 0), cta, font=cta_font)
        cta_w, cta_h = cb[2] - cb[0], cb[3] - cb[1]
        pill_pad_x, pill_pad_y = 28, 14
        pill_w      = cta_w + pill_pad_x * 2
        pill_h      = cta_h + pill_pad_y * 2
        pill_x      = (W - pill_w) // 2
        pill_y      = H - pill_h - 80
        draw.rounded_rectangle(
            [pill_x, pill_y, pill_x + pill_w, pill_y + pill_h],
            radius=pill_h // 2, outline=(255, 255, 255), width=2,
        )
        draw.text((pill_x + pill_pad_x - cb[0], pill_y + pill_pad_y - cb[1]),
                  cta, font=cta_font, fill=(255, 255, 255))
    else:
        # ── Standard footer: gold rule only (no @handle) ─────────────────────
        footer_y = H - 90
        draw.rectangle([TEXT_X, footer_y, TEXT_X + 50, footer_y + 4], fill=GOLD)

    # ── Slide counter — skip on hook (cover slide never shows "1/N") ──────────
    if not is_hook:
        draw.text((TEXT_X, 48), f"{n}/{total_slides}", font=fonts["footer"], fill=DIM)

    img.save(out_path, "JPEG", quality=JPEG_Q)
    print(f"  [OK] Slide {n} saved -> {out_path.name}")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate carousel slides with Pinterest backgrounds.")
    parser.add_argument("post_dir", nargs="?", default=None,
                        help="Path to the post slot directory (contains carousel.json)")
    parser.add_argument("--lang", default="en", choices=["en", "fr", "es", "x"],
                        help="Language version to generate (default: en). Use 'x' for the 4-slide X synthesis.")
    args = parser.parse_args()

    post_dir = Path(args.post_dir) if args.post_dir else ROOT / "posts" / "2026-03-26" / "0600"
    lang     = args.lang

    carousel = json.loads((post_dir / "carousel.json").read_text(encoding="utf-8"))

    # Support both multi-lang format (has "en"/"fr"/"es"/"x" keys) and old flat format
    is_multilang = any(k in carousel for k in ("en", "fr", "es", "x"))
    if is_multilang:
        lang_data = carousel.get(lang, carousel.get("en", {}))
        slides    = lang_data.get("slides", [])
        caption   = lang_data.get("caption", "")
    else:
        slides  = carousel["slides"]
        caption = carousel.get("caption", "")

    if not slides:
        print(f"[ERROR] No slides found for lang={lang} in {post_dir / 'carousel.json'}")
        sys.exit(1)

    total      = len(slides)
    slides_dir = post_dir / "slides"
    slides_dir.mkdir(exist_ok=True)

    # Topic: X synthesis may have different topic; fall back to EN meta
    if is_multilang:
        topic = lang_data.get("meta", {}).get("topic", "") or \
                carousel.get("en", {}).get("meta", {}).get("topic", "AI and productivity")
    else:
        topic = carousel.get("meta", {}).get("topic", "AI and productivity")

    # Language-specific finals subdir.
    # X uses slides/x/ with its own raw backgrounds (different content from EN/FR/ES).
    # EN/FR/ES share the same raw backgrounds in slides/.
    finals_dir = slides_dir / lang
    finals_dir.mkdir(exist_ok=True)

    # For X: raw backgrounds live in slides/x-raw/ (separate from EN/FR/ES pool)
    # For EN: raw backgrounds live in slides/ (shared with FR/ES)
    if lang == "x":
        x_raw_dir = slides_dir / "x-raw"
        x_raw_dir.mkdir(exist_ok=True)
        bg_base_dir = x_raw_dir
    else:
        bg_base_dir = slides_dir

    print(f"\nGenerating {total} slides for: {topic[:60]}...")
    print(f"Language: {lang.upper()}")
    fonts = ensure_fonts()
    print("Fonts ready.\n")

    # Raw Pinterest backgrounds check
    # EN/FR/ES share the same raw backgrounds (slides/slide-NN-raw.jpg)
    # X has its own raw backgrounds (slides/x-raw/slide-NN-raw.jpg)
    need_bgs_check = lang in ("en", "x")
    if need_bgs_check:
        slides_with_bg = sum(
            1 for s in slides
            if (bg_base_dir / f"slide-{s['number']:02d}-raw.jpg").exists()
        )
        if slides_with_bg == total:
            print(f"Pinterest backgrounds ready: {slides_with_bg}/{total} slides.")
        elif slides_with_bg > 0:
            print(f"Pinterest backgrounds: {slides_with_bg}/{total} slides. "
                  f"{total - slides_with_bg} missing — run fetch_backgrounds.py first.")
        else:
            print(f"[WARN] No Pinterest backgrounds found — slides will use solid color fallback.")
            if lang == "x":
                print(f"  Run: python scripts/fetch_backgrounds.py --slot-dir {post_dir} --lang x")
            else:
                print(f"  Run: python scripts/fetch_backgrounds.py --slot-dir {post_dir}")
    else:
        print(f"Reusing shared Pinterest backgrounds (lang={lang} reuses EN raw backgrounds).")

    # Apply text overlays — uses raw Pinterest bg if available, solid color fallback otherwise
    print("\nApplying smart text overlays (per-slide analysis)...")
    for slide in slides:
        n          = slide["number"]
        raw_path   = bg_base_dir / f"slide-{n:02d}-raw.jpg"
        final_path = finals_dir  / f"slide-{n:02d}-final.jpg"

        print(f"\n  -- Slide {n} ({slide.get('role','?')}) --")
        add_overlay(
            bg_path      = raw_path if raw_path.exists() else None,
            slide        = slide,
            fonts        = fonts,
            out_path     = final_path,
            total_slides = total,
            lang         = lang,
        )

    print(f"\n[DONE] {total} slides saved to: {finals_dir}")
    print(f"\nCaption:\n{caption}")


if __name__ == "__main__":
    main()
