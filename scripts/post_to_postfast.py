"""
post_to_postfast.py
-------------------
Upload carousel slides to PostFast and schedule them on TikTok + Instagram.

Usage:
  python scripts/post_to_postfast.py                     # all today's slots
  python scripts/post_to_postfast.py --slot 0600         # one slot
  python scripts/post_to_postfast.py --date 2026-03-27   # specific date
  python scripts/post_to_postfast.py --now               # post immediately
  python scripts/post_to_postfast.py --dry-run           # validate only
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
ROOT       = SCRIPT_DIR.parent
CONFIG_PATH = ROOT / "config.json"

with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)

API_KEY  = CONFIG["postfast"]["apiKey"]
BASE_URL = "https://api.postfa.st"
TZ       = ZoneInfo(CONFIG["posting"]["timezone"])


def get_account_ids(lang: str = "en") -> tuple[str | None, str | None, int]:
    """
    Return (tiktok_id, instagram_id, offset_minutes) for a given language.
    All languages post to the same accounts (configured in config.postfast.languages).
    offsetMinutes staggers EN/FR/ES so they don't hit the algorithm simultaneously:
      EN = slot time + 0 min
      FR = slot time + 3 min
      ES = slot time + 6 min
    Falls back to EN accounts + 0 offset if the language block is missing.
    """
    lang_cfg = CONFIG.get("postfast", {}).get("languages", {}).get(lang, {})
    if not lang_cfg:
        # Fallback: use default EN accounts
        default = CONFIG["postfast"]["accounts"]
        return default["tiktok"]["id"], default["instagram"]["id"], 0
    return lang_cfg.get("tiktok"), lang_cfg.get("instagram"), lang_cfg.get("offsetMinutes", 0)

HEADERS = {"pf-api-key": API_KEY, "Content-Type": "application/json"}


# ── Upload ──────────────────────────────────────────────────────────────────

def upload_image(image_path: Path) -> str:
    """
    Two-step S3 upload.
    1. Get a signed URL from PostFast (with retry on 429).
    2. PUT the file bytes directly to S3.
    Returns the key to use in the post payload.
    """
    # Step 1 — request signed URL (retry up to 8 times on 429)
    MAX_RETRIES = 8
    BACKOFF_BASE = 15  # seconds; doubles each attempt
    for attempt in range(MAX_RETRIES):
        resp = requests.post(
            f"{BASE_URL}/file/get-signed-upload-urls",
            headers=HEADERS,
            json={"contentType": "image/jpeg", "count": 1},
        )
        if resp.status_code == 429:
            wait = BACKOFF_BASE * (2 ** attempt)
            print(f"  [429] Rate limited on {image_path.name}. Waiting {wait}s... (attempt {attempt+1}/{MAX_RETRIES})")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        break
    else:
        raise RuntimeError(f"Upload failed after {MAX_RETRIES} retries (persistent 429 rate limit)")
    data     = resp.json()
    entry    = data[0] if isinstance(data, list) else data["urls"][0]
    key      = entry["key"]
    signed   = entry["signedUrl"]

    # Step 2 — PUT raw bytes to S3
    with open(image_path, "rb") as fh:
        put_resp = requests.put(
            signed,
            data=fh,
            headers={"Content-Type": "image/jpeg"},
        )
    put_resp.raise_for_status()

    print(f"  Uploaded {image_path.name} -> {key}")
    return key


# ── Post creation ───────────────────────────────────────────────────────────

def build_payload(
    tiktok_keys: list[str],
    instagram_keys: list[str],
    caption: str,
    scheduled_at: str,
    post_now: bool,
    tiktok_id: str | None = None,
    instagram_id: str | None = None,
) -> dict:
    status = "SCHEDULED"
    sched  = scheduled_at

    posts = []

    if tiktok_id and tiktok_keys:
        tiktok_media = [{"key": k, "type": "IMAGE", "sortOrder": i} for i, k in enumerate(tiktok_keys)]
        posts.append({
            "socialMediaId": tiktok_id,
            "content":       caption,
            "mediaItems":    tiktok_media,
            "status":        status,
            **({"scheduledAt": sched} if sched else {}),
        })

    if instagram_id and instagram_keys:
        instagram_media = [{"key": k, "type": "IMAGE", "sortOrder": i} for i, k in enumerate(instagram_keys)]
        posts.append({
            "socialMediaId":        instagram_id,
            "content":              caption,
            "mediaItems":           instagram_media,
            "status":               status,
            **({"scheduledAt": sched} if sched else {}),
        })

    return {
        "posts": posts,
        "controls": {
            "tiktokPrivacy":        "PUBLIC",
            "tiktokAllowComments":  True,
            "tiktokAutoAddMusic":   True,
            "instagramPublishType": "TIMELINE",
        },
    }


def create_posts(payload: dict, dry_run: bool) -> dict:
    if dry_run:
        print("\n[DRY-RUN] Would POST to /social-posts:")
        print(json.dumps(payload, indent=2, default=str))
        return {"dry_run": True}

    resp = requests.post(
        f"{BASE_URL}/social-posts",
        headers=HEADERS,
        json=payload,
    )
    resp.raise_for_status()
    return resp.json()


# ── Slot logic ───────────────────────────────────────────────────────────────

def get_scheduled_dt(target_date: date, slot: str) -> datetime:
    hour, minute = int(slot[:2]), int(slot[2:])
    naive = datetime(target_date.year, target_date.month, target_date.day, hour, minute)
    return naive.replace(tzinfo=TZ)


def post_slot(slot_dir: Path, target_date: date, dry_run=False, post_now=False, lang="en"):
    carousel_json = slot_dir / "carousel.json"
    if not carousel_json.exists():
        print(f"  Skipping {slot_dir.name} — no carousel.json")
        return

    with open(carousel_json) as f:
        carousel = json.load(f)

    # Support both multi-lang format (has "en"/"fr"/"es" keys) and old flat format
    is_multilang = "en" in carousel or "fr" in carousel or "es" in carousel
    if is_multilang:
        lang_data = carousel.get(lang, carousel.get("en", {}))
        caption   = lang_data.get("caption", "")
    else:
        caption = carousel.get("caption", "")

    slot = slot_dir.name

    # Find slides: for multi-lang look in slides/{lang}/ first, then fall back to slides/
    slides_dir = slot_dir / "slides"
    if is_multilang:
        lang_slides_dir = slides_dir / lang
        if lang_slides_dir.exists():
            image_files = sorted(lang_slides_dir.glob("slide-*-final.jpg"))
        else:
            # Fall back to flat slides dir
            image_files = sorted(slides_dir.glob("slide-*-final.jpg")) if slides_dir.exists() else []
    else:
        search_dir  = slides_dir if slides_dir.exists() else slot_dir
        image_files = sorted(search_dir.glob("slide-*-final.jpg")) or \
                      sorted(search_dir.glob("slide_*.jpg"))

    if not image_files:
        print(f"  Skipping {slot_dir.name} — no slide images (run generate_slides_py.py first)")
        return

    tiktok_id, instagram_id, offset_minutes = get_account_ids(lang)

    if not tiktok_id and not instagram_id:
        print(f"  Skipping {slot_dir.name} (lang={lang}) — no accounts configured for this language")
        return

    print(f"\n{'='*60}")
    print(f"Slot {slot}  |  lang={lang.upper()}  |  {len(image_files)} slides")
    if tiktok_id:    print(f"  TikTok:    {tiktok_id}")
    if instagram_id: print(f"  Instagram: {instagram_id}")
    if offset_minutes: print(f"  Offset:    +{offset_minutes} min (staggered from EN)")
    print(f"{'='*60}")

    # Upload all slides
    print("Uploading to PostFast CDN...")
    keys = []
    for img in image_files:
        if dry_run:
            keys.append(f"image/dry-{img.stem}.jpg")
        else:
            key = upload_image(img)
            keys.append(key)
            time.sleep(1.5)  # pace uploads to avoid 429 rate limit

    # Timing — apply per-language offset so EN/FR/ES don't post simultaneously
    from datetime import timedelta
    scheduled_dt = get_scheduled_dt(target_date, slot) + timedelta(minutes=offset_minutes)
    now_paris    = datetime.now(TZ)
    if not post_now and scheduled_dt < now_paris:
        print(f"Slot {slot} ({lang.upper()}) already passed — posting NOW")
        post_now = True

    scheduled_iso = now_paris.isoformat() if post_now else scheduled_dt.isoformat()

    if post_now:
        print(f"Posting NOW  (Paris: {now_paris.strftime('%H:%M')})")
    else:
        print(f"Scheduled:   {scheduled_dt.strftime('%Y-%m-%d %H:%M')} Paris  [{lang.upper()}]")

    print("  TikTok:    PUBLIC + autoAddMusic")
    print("  Instagram: TIMELINE carousel")

    payload = build_payload(keys, keys, caption, scheduled_iso, post_now,
                            tiktok_id=tiktok_id, instagram_id=instagram_id)

    try:
        result = create_posts(payload, dry_run)
        if not dry_run:
            print("\nPostFast response:")
            print(json.dumps(result, indent=2, default=str))
    except requests.HTTPError as e:
        print(f"\nERROR {e.response.status_code}: {e.response.text}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date",    default=None)
    parser.add_argument("--slot",    default=None)
    parser.add_argument("--now",     action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    # Default language comes from config (set during onboarding).
    # --lang overrides it for one-off runs.
    _config_lang = CONFIG.get("posting", {}).get("postingLanguage", "en")
    parser.add_argument("--lang", default=_config_lang, choices=["en", "fr", "es"],
                        help=f"Language version to post (default from config: {_config_lang})")
    args = parser.parse_args()

    target_date = date.fromisoformat(args.date) if args.date else date.today()
    posts_dir   = ROOT / "posts" / target_date.isoformat()

    if not posts_dir.exists():
        print(f"No posts directory for {target_date}")
        sys.exit(1)

    slot_dirs = [posts_dir / args.slot] if args.slot else \
                sorted(d for d in posts_dir.iterdir() if d.is_dir())

    if args.dry_run:
        print("[DRY-RUN] No posts will be created.\n")

    for slot_dir in slot_dirs:
        if not slot_dir.exists():
            print(f"Slot not found: {slot_dir}")
            continue
        post_slot(slot_dir, target_date, dry_run=args.dry_run, post_now=args.now, lang=args.lang)

    print("\nDone.")


if __name__ == "__main__":
    main()
