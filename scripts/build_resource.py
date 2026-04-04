"""
build_resource.py
-----------------
Renders a resource.json file from a carousel slot directory into a branded PDF.

Each section in resource.json becomes one or more pages rendered with Pillow,
matching the creator's visual identity (handle read from config.json). No external PDF library needed --
Pillow's built-in PDF writer stitches the pages together.

Usage:
    python scripts/build_resource.py --slot-dir posts/2026-03-30/0600
    python scripts/build_resource.py --slot-dir posts/2026-03-30/0600 --force
"""

import argparse
import json
import sys
import textwrap
from pathlib import Path


from PIL import Image, ImageDraw, ImageFont

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).resolve().parent.parent
FONTS_DIR  = ROOT / "fonts"
CONFIG     = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
CREATOR_HANDLE = "@" + CONFIG.get("creator", {}).get("name", "yourcreator").lstrip("@")

# ── Brand colors ──────────────────────────────────────────────────────────────
BLACK  = (8,   8,   8)
CREAM  = (237, 232, 223)
GOLD   = (200, 168, 75)
WHITE  = (245, 240, 232)
DIM    = (175, 170, 162)

# ── Canvas ────────────────────────────────────────────────────────────────────
W, H   = 1080, 1350
MARGIN = 80     # left/right margin
TOP    = 120    # first content Y

# ── Font sizes ────────────────────────────────────────────────────────────────
SIZE_TITLE   = 68
SIZE_LABEL   = 28
SIZE_HEADING = 44
SIZE_BODY    = 32
SIZE_ITEM    = 30
SIZE_FOOTER  = 24
SIZE_META    = 22


# ── Font loader ────────────────────────────────────────────────────────────────

def _load_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = FONTS_DIR / name
    if path.exists():
        return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def load_fonts() -> dict:
    return {
        "bold":   _load_font("Poppins-Bold.ttf",      SIZE_BODY),
        "light":  _load_font("Poppins-Light.ttf",     SIZE_BODY),
        "medium": _load_font("Poppins-Medium.ttf",    SIZE_BODY),
        "mono":   _load_font("IBMPlexMono-Regular.ttf", SIZE_FOOTER),
        "title":  _load_font("Poppins-Bold.ttf",      SIZE_TITLE),
        "label":  _load_font("Poppins-Medium.ttf",    SIZE_LABEL),
        "heading":_load_font("Poppins-Bold.ttf",      SIZE_HEADING),
        "body":   _load_font("Poppins-Light.ttf",     SIZE_BODY),
        "item":   _load_font("Poppins-Light.ttf",     SIZE_ITEM),
        "meta":   _load_font("Poppins-Light.ttf",     SIZE_META),
        "footer": _load_font("IBMPlexMono-Regular.ttf", SIZE_FOOTER),
    }


# ── Footer ─────────────────────────────────────────────────────────────────────

def draw_footer(draw: ImageDraw.ImageDraw, fonts: dict, dark: bool) -> None:
    """Draw gold rule + @handle at the bottom of every page."""
    rule_y = H - 80
    draw.rectangle([MARGIN, rule_y, MARGIN + 50, rule_y + 4], fill=GOLD)
    handle_y = rule_y + 12
    draw.text((MARGIN, handle_y), CREATOR_HANDLE, font=fonts["footer"], fill=DIM)


# ── Text helper ────────────────────────────────────────────────────────────────

def draw_wrapped(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    color: tuple,
    x: int,
    y: int,
    max_width: int,
    line_spacing: int = 10,
) -> int:
    """Draw word-wrapped text. Returns Y position after last line."""
    words = text.split()
    lines = []
    current = []

    for word in words:
        test = " ".join(current + [word])
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width or not current:
            current.append(word)
        else:
            lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))

    for line in lines:
        draw.text((x, y), line, font=font, fill=color)
        bbox = draw.textbbox((0, 0), line, font=font)
        y += (bbox[3] - bbox[1]) + line_spacing

    return y


# ── Gold-last-word headline ────────────────────────────────────────────────────

def draw_heading_gold_last(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    base_color: tuple,
    x: int,
    y: int,
    max_width: int,
    line_spacing: int = 12,
) -> int:
    """Draw a heading where the last word is always gold."""
    words = text.split()
    if not words:
        return y

    # Word-wrap the heading
    lines = []
    current = []
    for word in words:
        test = " ".join(current + [word])
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width or not current:
            current.append(word)
        else:
            lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))

    for li, line in enumerate(lines):
        is_last_line = (li == len(lines) - 1)
        line_words = line.split()

        if is_last_line and len(line_words) > 0:
            # Draw all words except last in base color
            prefix = " ".join(line_words[:-1])
            last_word = line_words[-1]

            cx = x
            if prefix:
                draw.text((cx, y), prefix + " ", font=font, fill=base_color)
                pw_bbox = draw.textbbox((0, 0), prefix + " ", font=font)
                cx += pw_bbox[2] - pw_bbox[0]
            draw.text((cx, y), last_word, font=font, fill=GOLD)
        else:
            draw.text((x, y), line, font=font, fill=base_color)

        bbox = draw.textbbox((0, 0), line, font=font)
        y += (bbox[3] - bbox[1]) + line_spacing

    return y


# ── Page builders ──────────────────────────────────────────────────────────────

def make_cover_page(meta: dict, fonts: dict) -> Image.Image:
    """Dark cover page with resource title and format label."""
    img  = Image.new("RGB", (W, H), BLACK)
    draw = ImageDraw.Draw(img)

    # Format label
    fmt_label = meta.get("format", "resource").upper().replace("_", " ")
    draw.text((MARGIN, TOP), fmt_label, font=fonts["label"], fill=GOLD)

    # Title (gold last word)
    title = meta.get("title", "Resource")
    y = TOP + 60
    y = draw_heading_gold_last(draw, title, fonts["title"], WHITE, MARGIN, y, W - MARGIN * 2, line_spacing=16)

    # Divider
    y += 40
    draw.rectangle([MARGIN, y, MARGIN + 80, y + 3], fill=GOLD)
    y += 30

    # CTA word
    cta_word = meta.get("ctaWord", "")
    if cta_word:
        msg = f"You typed {cta_word}. Here is what I promised."
        y = draw_wrapped(draw, msg, fonts["meta"], DIM, MARGIN, y + 20, W - MARGIN * 2, line_spacing=8)

    draw_footer(draw, fonts, dark=True)
    return img


def make_section_page(
    section: dict,
    page_index: int,
    total_sections: int,
    fonts: dict,
) -> Image.Image:
    """One page per section. Alternates dark/light starting with light for page 1."""
    dark = (page_index % 2 == 0)   # page 0 (first section) = light, page 1 = dark, ...
    bg   = BLACK if dark else CREAM
    body_color = WHITE if dark else BLACK
    secondary  = DIM if dark else (120, 115, 108)

    img  = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)

    y = TOP

    # Section number label
    label = f"{page_index + 1} / {total_sections}"
    draw.text((MARGIN, y), label, font=fonts["label"], fill=GOLD if dark else secondary)
    y += 44

    # Section heading (gold last word)
    heading = section.get("heading", "")
    if heading:
        y = draw_heading_gold_last(
            draw, heading, fonts["heading"], body_color,
            MARGIN, y, W - MARGIN * 2, line_spacing=14
        )
        y += 24

    # Section body
    body = section.get("body", "")
    if body:
        y = draw_wrapped(draw, body, fonts["body"], body_color, MARGIN, y, W - MARGIN * 2, line_spacing=10)
        y += 28

    # Bullet items
    items = section.get("items", [])
    for item in items:
        # Gold bullet
        bullet_x = MARGIN
        bullet_y = y + 6
        draw.ellipse([bullet_x, bullet_y, bullet_x + 8, bullet_y + 8], fill=GOLD)
        item_x = MARGIN + 24
        y = draw_wrapped(draw, item, fonts["item"], body_color, item_x, y, W - item_x - MARGIN, line_spacing=8)
        y += 12

    draw_footer(draw, fonts, dark=dark)
    return img


def make_closer_page(footer_text: str, fonts: dict) -> Image.Image:
    """Dark closer page with the footer CTA."""
    img  = Image.new("RGB", (W, H), BLACK)
    draw = ImageDraw.Draw(img)

    y = TOP + 80
    y = draw_wrapped(draw, footer_text, fonts["heading"], WHITE, MARGIN, y, W - MARGIN * 2, line_spacing=16)

    draw_footer(draw, fonts, dark=True)
    return img


# ── Main builder ───────────────────────────────────────────────────────────────

def build_resource_pdf(slot_dir: Path, force: bool = False) -> Path:
    resource_json = slot_dir / "resource.json"
    output_pdf    = slot_dir / "resource.pdf"

    if not resource_json.exists():
        print(f"  [SKIP] No resource.json found at {resource_json}")
        sys.exit(0)

    if output_pdf.exists() and not force:
        print(f"  [SKIP] resource.pdf already exists at {output_pdf} (use --force to overwrite)")
        sys.exit(0)

    data = json.loads(resource_json.read_text(encoding="utf-8"))
    meta     = data.get("meta", {})
    sections = data.get("sections", [])
    footer   = data.get("footer", "")

    if not sections:
        print(f"  [ERROR] resource.json has no sections.")
        sys.exit(1)

    print(f"  Building resource PDF: {meta.get('title', '(untitled)')}")
    print(f"  Format  : {meta.get('format', 'unknown')}")
    print(f"  Sections: {len(sections)}")

    fonts = load_fonts()

    pages = []
    pages.append(make_cover_page(meta, fonts))

    for i, section in enumerate(sections):
        pages.append(make_section_page(section, i, len(sections), fonts))

    if footer:
        pages.append(make_closer_page(footer, fonts))

    first_page = pages[0]
    rest_pages = pages[1:]

    first_page.save(
        str(output_pdf),
        format="PDF",
        save_all=True,
        append_images=rest_pages,
    )

    print(f"  Saved  : {output_pdf}  ({len(pages)} pages)")
    return output_pdf


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Build PDF resource from resource.json")
    parser.add_argument(
        "--slot-dir",
        required=True,
        help="Path to the slot directory (e.g. posts/2026-03-30/0600)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing resource.pdf",
    )
    args = parser.parse_args()

    slot_dir = Path(args.slot_dir)
    if not slot_dir.is_absolute():
        slot_dir = ROOT / slot_dir

    if not slot_dir.exists():
        print(f"  [ERROR] Slot directory not found: {slot_dir}")
        sys.exit(1)

    build_resource_pdf(slot_dir, force=args.force)


if __name__ == "__main__":
    main()
