"""
post_to_postiz.py
-----------------
Upload carousel images + caption to Postiz and schedule them
on TikTok and Instagram.

Usage:
  python scripts/post_to_postiz.py                     # post all today's slots
  python scripts/post_to_postiz.py --slot 0600         # post one slot
  python scripts/post_to_postiz.py --date 2026-03-26   # post specific date
  python scripts/post_to_postiz.py --dry-run           # validate without posting
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

# ── Paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
ROOT = SCRIPT_DIR.parent
CONFIG_PATH = ROOT / "config.json"

# ── Load config ─────────────────────────────────────────────────────────────
with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)

POSTIZ_KEY   = CONFIG["postiz"]["apiKey"]
BASE_URL     = CONFIG["postiz"]["baseUrl"]
TZ           = ZoneInfo(CONFIG["posting"]["timezone"])

TIKTOK_ID    = CONFIG["postiz"]["integrations"]["tiktok"]["id"]
INSTAGRAM_ID = CONFIG["postiz"]["integrations"]["instagram"]["id"]

AUTH_HEADERS = {"Authorization": POSTIZ_KEY}


# ── Postiz API helpers ───────────────────────────────────────────────────────

def upload_image(image_path: Path) -> dict:
    """
    Upload a single image to Postiz.
    Returns dict with 'id' and 'path' (public CDN URL).
    """
    url = f"{BASE_URL}/upload"
    with open(image_path, "rb") as fh:
        resp = requests.post(
            url,
            headers=AUTH_HEADERS,
            files={"file": (image_path.name, fh, "image/jpeg")},
        )
    resp.raise_for_status()
    data = resp.json()
    # Postiz returns something like {"id": "...", "path": "https://uploads.postiz.com/..."}
    result = {
        "id":   data.get("id")   or data.get("mediaId") or "",
        "path": data.get("path") or data.get("url")     or "",
    }
    if not result["id"] and not result["path"]:
        raise ValueError(f"Unexpected upload response: {data}")
    print(f"  Uploaded {image_path.name} -> id={result['id']}")
    return result


def build_tiktok_payload(media: list[dict], caption: str, scheduled_dt: datetime) -> dict:
    """TikTok: scheduled, auto music, public."""
    return {
        "type":      "schedule",
        "date":      scheduled_dt.isoformat(),
        "shortLink": False,
        "tags":      [],
        "posts": [
            {
                "integration": {"id": TIKTOK_ID},
                "value": [{"content": caption, "image": media}],
                "settings": {
                    "__type":                 "tiktok",
                    "privacy_level":          "SELF_ONLY",
                    "comment":                True,
                    "duet":                   False,
                    "stitch":                 False,
                    "autoAddMusic":           "no",
                    "video_made_with_ai":     True,
                    "brand_content_toggle":   False,
                    "brand_organic_toggle":   False,
                    "content_posting_method": "UPLOAD",
                },
            }
        ],
    }


def build_instagram_draft_payload(media: list[dict], caption: str, scheduled_dt: datetime) -> dict:
    """Instagram: scheduled, no music (API limitation for carousels)."""
    return {
        "type":      "schedule",
        "date":      scheduled_dt.isoformat(),
        "shortLink": False,
        "tags":      [],
        "posts": [
            {
                "integration": {"id": INSTAGRAM_ID},
                "value": [{"content": caption, "image": media}],
                "settings": {"__type": "instagram-standalone", "post_type": "post"},
            }
        ],
    }


def _post(payload: dict, label: str, dry_run: bool) -> dict:
    """POST one payload to /posts, or print it in dry-run mode."""
    if dry_run:
        print(f"\n  [DRY-RUN] {label}:")
        print(json.dumps(payload, indent=2, default=str))
        return {"dry_run": True}
    resp = requests.post(
        f"{BASE_URL}/posts",
        headers={**AUTH_HEADERS, "Content-Type": "application/json"},
        json=payload,
    )
    resp.raise_for_status()
    return resp.json()


def schedule_posts(
    media_items: list[dict],
    caption: str,
    scheduled_dt: datetime,
    post_now: bool = False,
    dry_run: bool = False,
) -> dict:
    """
    Two separate calls:
      1. TikTok  — scheduled + autoAddMusic (or immediate if post_now=True)
      2. Instagram — scheduled, no music
    """
    tiktok_payload   = build_tiktok_payload(media_items, caption, scheduled_dt)
    instagram_payload = build_instagram_draft_payload(media_items, caption, scheduled_dt)

    if post_now:
        tiktok_payload["type"]    = "now"
        instagram_payload["type"] = "now"

    tiktok_result = _post(tiktok_payload, "TikTok (NOW, autoAddMusic=yes)", dry_run)
    instagram_result = _post(instagram_payload, "Instagram (NOW, no music)", dry_run)
    return {"tiktok": tiktok_result, "instagram": instagram_result}


# ── Slot logic ───────────────────────────────────────────────────────────────

def get_scheduled_datetime(target_date: date, slot: str) -> datetime:
    """Convert a slot like '0600' to a timezone-aware datetime."""
    hour   = int(slot[:2])
    minute = int(slot[2:])
    naive  = datetime(target_date.year, target_date.month, target_date.day, hour, minute)
    return naive.replace(tzinfo=TZ)


def post_slot(slot_dir: Path, target_date: date, dry_run: bool = False, post_now: bool = False):
    """Upload images + schedule post for one time-slot directory."""
    carousel_json = slot_dir / "carousel.json"
    if not carousel_json.exists():
        print(f"  Skipping {slot_dir.name} — no carousel.json")
        return

    with open(carousel_json) as f:
        carousel = json.load(f)

    caption = carousel.get("caption", "")
    slot    = slot_dir.name  # e.g. "0600"

    # Collect final slide images in order (slides/ subfolder, -final.jpg naming)
    slides_dir = slot_dir / "slides"
    if slides_dir.exists():
        image_files = sorted(slides_dir.glob("slide-*-final.jpg"))
        if not image_files:
            image_files = sorted(slides_dir.glob("slide_*.jpg"))
    else:
        image_files = sorted(slot_dir.glob("slide_*.jpg"))

    if not image_files:
        print(f"  Skipping {slot_dir.name} — no slide images found (run generate_slides_py.py first)")
        return

    print(f"\n{'='*60}")
    print(f"Slot {slot}  ({len(image_files)} slides)")
    print(f"{'='*60}")

    # Upload all images
    print("Uploading images to Postiz CDN...")
    media_items = []
    for img in image_files:
        if dry_run:
            media_items.append({"id": f"dry-id-{img.stem}", "path": f"https://uploads.postiz.com/dry/{img.name}"})
        else:
            item = upload_image(img)
            media_items.append(item)
            time.sleep(0.3)  # gentle on the API

    scheduled_dt = get_scheduled_datetime(target_date, slot)
    now_paris    = datetime.now(TZ)

    # Auto-detect past slots — post immediately instead of scheduling in the past
    if not post_now and scheduled_dt < now_paris:
        print(f"Slot {slot} is in the past ({scheduled_dt.strftime('%H:%M')} Paris) — posting NOW instead")
        post_now = True

    if post_now:
        print(f"Posting NOW  (Paris time: {now_paris.strftime('%H:%M')})")
        print("  TikTok:    NOW — autoAddMusic=yes, PUBLIC")
        print("  Instagram: NOW — no music")
    else:
        print(f"Scheduling for {scheduled_dt.isoformat()}")
        print("  TikTok:    SCHEDULED — autoAddMusic=yes, PUBLIC")
        print("  Instagram: SCHEDULED — no music")

    try:
        result = schedule_posts(media_items, caption, scheduled_dt, post_now=post_now, dry_run=dry_run)
        if dry_run:
            return
        print(f"\nPostiz response:")
        print(json.dumps(result, indent=2, default=str))
    except requests.HTTPError as e:
        print(f"\nERROR {e.response.status_code}: {e.response.text}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Post carousels to Postiz")
    parser.add_argument("--date",    default=None, help="Date YYYY-MM-DD (default: today)")
    parser.add_argument("--slot",    default=None, help="Single slot e.g. 0600 (default: all)")
    parser.add_argument("--dry-run", action="store_true", help="Validate without posting")
    parser.add_argument("--now",     action="store_true", help="Post immediately (ignore scheduled time)")
    args = parser.parse_args()

    target_date = date.fromisoformat(args.date) if args.date else date.today()
    posts_dir   = ROOT / "posts" / target_date.isoformat()

    if not posts_dir.exists():
        print(f"No posts directory for {target_date}: {posts_dir}")
        sys.exit(1)

    if args.slot:
        slot_dirs = [posts_dir / args.slot]
    else:
        slot_dirs = sorted(d for d in posts_dir.iterdir() if d.is_dir())

    if args.dry_run:
        print("[DRY-RUN MODE] No posts will be created.\n")

    for slot_dir in slot_dirs:
        if not slot_dir.exists():
            print(f"Slot directory not found: {slot_dir}")
            continue
        post_slot(slot_dir, target_date, dry_run=args.dry_run, post_now=args.now)

    print("\nDone.")


if __name__ == "__main__":
    main()
