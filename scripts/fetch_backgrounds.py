"""
fetch_backgrounds.py
--------------------
Downloads Pinterest images as slide backgrounds for a carousel slot.

Pinterest photos as slide backgrounds — one photo per slide that
visually matches what the slide is talking about. Same background is reused
across EN/FR/ES language versions (only text + auto-music vary).

Workflow:
  1. Claude writes carousel.json with a `bgQuery` per slide
     ("fog blur dark aesthetic", "clean minimal desk light", etc.)
  2. Claude opens pinterest.com in Chrome, searches each bgQuery, picks best photo
  3. Run this script with the Pinterest image URL to download + save as raw background
  4. generate_slides_py.py sees raw file already exists → overlays text

Usage:
  # Print all bgQuery values Claude should search on Pinterest
  python scripts/fetch_backgrounds.py --slot-dir posts/YYYY-MM-DD/HHMM --list

  # Save one Pinterest image as a slide background
  python scripts/fetch_backgrounds.py --slot-dir posts/YYYY-MM-DD/HHMM --slide 1 --url https://i.pinimg.com/736x/...

  # Save all slides at once from a JSON map  {slide_num: url}
  python scripts/fetch_backgrounds.py --slot-dir posts/YYYY-MM-DD/HHMM --map '{"1":"https://...","2":"https://..."}'

  # Check which slides already have backgrounds and which still need one
  python scripts/fetch_backgrounds.py --slot-dir posts/YYYY-MM-DD/HHMM --status

Pinterest URL upgrade:
  Any Pinterest image URL (236x, 474x, 736x) is automatically upgraded to
  the highest resolution (originals/) before downloading.

Canvas:
  All images are center-cropped and resized to 1080x1350px (4:5, portrait)
  to match the carousel canvas. Pillow handles the crop.
"""

import argparse
import json
import re
import sys
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image

# Force UTF-8 on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT      = Path(__file__).resolve().parent.parent
POSTS_DIR = ROOT / "posts"

# Target canvas dimensions
CANVAS_W = 1080
CANVAS_H = 1350

# Pinterest CDN size prefixes — we upgrade any of these to originals
PINIMG_SIZES = re.compile(r"(https://i\.pinimg\.com/)(\d+x(?:/\d+x)?)(/.+)")


# ---------------------------------------------------------------------------
# URL utilities
# ---------------------------------------------------------------------------

def upgrade_pinterest_url(url: str) -> str:
    """
    Upgrade a Pinterest image URL to the highest available resolution.
    236x / 474x / 736x  →  originals
    """
    m = PINIMG_SIZES.match(url)
    if m:
        return f"{m.group(1)}originals{m.group(3)}"
    return url


def is_pinterest_url(url: str) -> bool:
    return "pinimg.com" in url or "pinterest.com" in url


# ---------------------------------------------------------------------------
# Image download + crop
# ---------------------------------------------------------------------------

def download_image(url: str) -> Image.Image:
    """Download an image from a URL and return a Pillow Image."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.pinterest.com/",
    }
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return Image.open(BytesIO(r.content)).convert("RGB")


def smart_crop(img: Image.Image, target_w: int = CANVAS_W, target_h: int = CANVAS_H) -> Image.Image:
    """
    Resize + center-crop an image to target dimensions.
    Preserves as much of the image as possible (scale to fill, then crop center).
    """
    src_w, src_h = img.size

    # Scale so the image fills the target (no black bars)
    scale = max(target_w / src_w, target_h / src_h)
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)
    img   = img.resize((new_w, new_h), Image.LANCZOS)

    # Center crop
    left = (new_w - target_w) // 2
    top  = (new_h - target_h) // 2
    img  = img.crop((left, top, left + target_w, top + target_h))

    return img


def save_background(img: Image.Image, dest_path: Path, quality: int = 96) -> None:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest_path, format="JPEG", quality=quality, optimize=True)


# ---------------------------------------------------------------------------
# Slot directory helpers
# ---------------------------------------------------------------------------

def get_slot_dir(slot_dir_arg: str) -> Path:
    p = Path(slot_dir_arg)
    if not p.is_absolute():
        p = ROOT / p
    if not p.exists():
        print(f"ERROR: slot directory not found: {p}")
        sys.exit(1)
    return p


def get_raw_path(slot_dir: Path, slide_num: int, lang: str = "en") -> Path:
    """Return the path where a raw background should be saved."""
    if lang == "x":
        return slot_dir / "slides" / "x-raw" / f"slide-{slide_num:02d}-raw.jpg"
    return slot_dir / "slides" / f"slide-{slide_num:02d}-raw.jpg"


def read_carousel(slot_dir: Path) -> dict:
    carousel_path = slot_dir / "carousel.json"
    if not carousel_path.exists():
        print(f"ERROR: no carousel.json in {slot_dir}")
        sys.exit(1)
    return json.loads(carousel_path.read_text(encoding="utf-8"))


def get_slides(carousel: dict, lang: str = "en") -> list[dict]:
    """
    Extract the slides list from carousel.json.
    Supports both flat format and multi-lang format.
    lang="x" returns X synthesis slides.
    """
    if lang == "x":
        return carousel.get("x", {}).get("slides", [])
    if "en" in carousel:
        return carousel["en"].get("slides", [])
    if "slides" in carousel:
        return carousel["slides"]
    return []


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_list(slot_dir: Path, lang: str = "en") -> None:
    """Print bgQuery for each slide so Claude knows what to search on Pinterest."""
    carousel = read_carousel(slot_dir)
    slides   = get_slides(carousel, lang)

    label = f"X synthesis (4 slides)" if lang == "x" else f"EN/FR/ES (main slides)"
    print(f"\n{'='*60}")
    print(f"  Pinterest search queries  |  {slot_dir.parent.name}/{slot_dir.name}  [{label}]")
    print(f"{'='*60}")
    print(f"{'Slide':<8} {'Theme':<8} {'bgQuery'}")
    print(f"{'-'*60}")

    for slide in slides:
        num     = slide.get("number", "?")
        theme   = slide.get("theme", "dark" if int(str(num)) % 2 == 1 else "light")
        query   = slide.get("bgQuery", "")
        raw_exists = get_raw_path(slot_dir, int(str(num)), lang).exists()
        status  = "[OK]" if raw_exists else "[need]"

        if query:
            print(f"  {num:<6} {theme:<8} {status}  {query}")
        else:
            print(f"  {num:<6} {theme:<8} {status}  (no bgQuery — add to carousel.json)")

    lang_flag = " --lang x" if lang == "x" else ""
    print()
    print("Search on Pinterest:  https://www.pinterest.com/search/pins/?q=QUERY")
    print(f"Then run:  --slide N --url https://i.pinimg.com/...{lang_flag}")
    print()


def cmd_status(slot_dir: Path, lang: str = "en") -> None:
    """Show which slides have backgrounds and which still need them."""
    carousel = read_carousel(slot_dir)
    slides   = get_slides(carousel, lang)
    done, missing = [], []

    for slide in slides:
        num = slide.get("number", "?")
        raw_path = get_raw_path(slot_dir, int(str(num)), lang)
        if raw_path.exists():
            done.append(num)
        else:
            missing.append(num)

    label = " [X]" if lang == "x" else ""
    print(f"\n  Slot: {slot_dir.parent.name}/{slot_dir.name}{label}")
    print(f"  Done:    slides {done}")
    print(f"  Missing: slides {missing}")
    if not missing:
        print("  All backgrounds ready. Run generate_slides_py.py to apply text overlays.")
    print()


def cmd_save(slot_dir: Path, slide_num: int, url: str, force: bool = False, lang: str = "en") -> None:
    """Download a Pinterest image and save it as the raw background for a slide."""
    dest = get_raw_path(slot_dir, slide_num, lang)

    if dest.exists() and not force:
        print(f"  Slide {slide_num} already has a background: {dest}")
        print(f"  Use --force to overwrite.")
        return

    # Upgrade URL to highest resolution
    original_url = url
    url = upgrade_pinterest_url(url)
    if url != original_url:
        print(f"  Upgraded URL: {url}")

    print(f"  Downloading slide {slide_num} background...")
    try:
        img = download_image(url)
    except requests.HTTPError as e:
        # If originals/ fails, fall back to 736x
        if "originals" in url:
            fallback = url.replace("/originals/", "/736x/")
            print(f"  originals/ failed ({e.response.status_code}), trying 736x...")
            img = download_image(fallback)
        else:
            raise

    orig_size = img.size
    img = smart_crop(img)
    save_background(img, dest)

    print(f"  Saved:    {dest.relative_to(ROOT)}")
    print(f"  Original: {orig_size[0]}x{orig_size[1]}px  →  {CANVAS_W}x{CANVAS_H}px (cropped)")


def cmd_map(slot_dir: Path, mapping: dict, force: bool = False, lang: str = "en") -> None:
    """Download multiple Pinterest images from a {slide_num: url} mapping."""
    label = " [X]" if lang == "x" else ""
    print(f"\n  Saving {len(mapping)} backgrounds for {slot_dir.parent.name}/{slot_dir.name}{label}")
    print()

    for slide_num_str, url in mapping.items():
        slide_num = int(slide_num_str)
        cmd_save(slot_dir, slide_num, url, force=force, lang=lang)

    print()
    cmd_status(slot_dir, lang)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Download Pinterest images as slide backgrounds",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--slot-dir", required=True,
        help="Path to slot directory, e.g. posts/2026-03-30/0730",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="Print bgQuery values for Claude to search on Pinterest",
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Show which slides have backgrounds and which need them",
    )
    parser.add_argument(
        "--slide", type=int, default=None,
        help="Slide number to save (use with --url)",
    )
    parser.add_argument(
        "--url", default=None,
        help="Pinterest image URL to download (any resolution — upgraded automatically)",
    )
    parser.add_argument(
        "--map", default=None,
        help='JSON map of slide_num to URL: \'{"1": "https://...", "2": "https://..."}\'',
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Overwrite existing background files",
    )
    parser.add_argument(
        "--lang", default="en", choices=["en", "x"],
        help="Which slide set to target: 'en' = main 9 slides (shared EN/FR/ES), 'x' = X 4-slide synthesis (default: en)",
    )
    args = parser.parse_args()

    slot_dir = get_slot_dir(args.slot_dir)

    if args.list:
        cmd_list(slot_dir, lang=args.lang)

    elif args.status:
        cmd_status(slot_dir, lang=args.lang)

    elif args.map:
        try:
            mapping = json.loads(args.map)
        except json.JSONDecodeError as e:
            print(f"ERROR: invalid --map JSON: {e}")
            sys.exit(1)
        cmd_map(slot_dir, mapping, force=args.force, lang=args.lang)

    elif args.slide and args.url:
        cmd_save(slot_dir, args.slide, args.url, force=args.force, lang=args.lang)

    else:
        parser.print_help()
        print("\nTip: start with --list to see what to search on Pinterest.")


if __name__ == "__main__":
    main()
