"""
upload_to_drive.py
------------------
Prepares the Google Drive upload info for a carousel slot's PDF resource.

This script does NOT require any API keys or OAuth tokens.
Claude uploads the PDF via Chrome (same approach as Pinterest background fetching).

What this script does:
  1. Reads carousel.json to get date, topic, and CTA word
  2. Calculates the target folder structure in Google Drive
  3. Prints a ready-to-use upload brief for Claude to act on in Chrome

After running this script, Claude will:
  1. Open drive.google.com in Chrome
  2. Find or create the root folder: CLAUDE AGENT CAROUSEL PDFS
  3. Create a subfolder named:  {date} -- {topic-slug} [{CTA_WORD}]
  4. Upload the PDF from the local path printed below
  5. Set sharing to: Anyone with the link -- Viewer (no login required)
  6. Return the shareable view link + direct download link

Usage:
  python scripts/upload_to_drive.py --slot-dir posts/2026-04-02/1300
  python scripts/upload_to_drive.py --slot-dir posts/2026-04-02/1300 --dry-run
"""

import argparse
import json
import re
import sys
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT            = Path(__file__).resolve().parent.parent
DRIVE_ROOT_NAME = "CLAUDE AGENT CAROUSEL PDFS"

# Force UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def slug(text: str, max_words: int = 5) -> str:
    """Convert a topic string to a short readable slug for folder naming."""
    text  = re.sub(r"[^\w\s-]", "", text.lower())
    words = text.split()[:max_words]
    return "-".join(words)


def run(slot_dir: Path, dry_run: bool = False) -> None:
    """Read slot metadata and print the Drive upload brief."""

    # ── Validate ───────────────────────────────────────────────────────────────
    pdf_path = slot_dir / "resource.pdf"
    if not pdf_path.exists():
        print(f"\nERROR: resource.pdf not found at {pdf_path}")
        print("Run first:  python scripts/build_resource.py --slot-dir " + str(slot_dir.relative_to(ROOT)))
        sys.exit(1)

    # ── Read carousel metadata ─────────────────────────────────────────────────
    carousel_path = slot_dir / "carousel.json"
    date_str      = slot_dir.parent.name      # e.g. 2026-04-02
    topic         = "carousel"
    cta_word      = ""

    if carousel_path.exists():
        data     = json.loads(carousel_path.read_text(encoding="utf-8"))
        meta     = data.get("meta", {})
        topic    = meta.get("topic", "carousel")
        cta_word = meta.get("ctaWord", "")

    topic_slug     = slug(topic)
    subfolder_name = f"{date_str} -- {topic_slug}"
    if cta_word:
        subfolder_name += f" [{cta_word}]"

    pdf_size_kb = pdf_path.stat().st_size / 1024

    # ── Print upload brief ─────────────────────────────────────────────────────
    print(f"\n{'='*62}")
    print(f"  GOOGLE DRIVE UPLOAD BRIEF")
    print(f"{'='*62}")
    print(f"  Local PDF   : {pdf_path}")
    print(f"  Size        : {pdf_size_kb:.1f} KB")
    print(f"  Root folder : {DRIVE_ROOT_NAME}")
    print(f"  Subfolder   : {subfolder_name}")
    print(f"{'='*62}")
    print()
    print("  Claude will now open drive.google.com in Chrome and:")
    print(f"  1. Find or create: {DRIVE_ROOT_NAME}/")
    print(f"  2. Create subfolder: {subfolder_name}/")
    print(f"  3. Upload: {pdf_path.name}")
    print(f"  4. Set sharing: Anyone with the link -- Viewer")
    print(f"     (no Google login required to view or download)")
    print(f"  5. Return the shareable link")
    print()

    if dry_run:
        print("  [DRY RUN] No upload performed.")
        return

    # ── Emit machine-readable block for Claude to parse ───────────────────────
    print("DRIVE_UPLOAD_READY")
    print(f"PDF_PATH={pdf_path}")
    print(f"ROOT_FOLDER={DRIVE_ROOT_NAME}")
    print(f"SUBFOLDER={subfolder_name}")
    print(f"FILENAME={pdf_path.name}")


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Prepare Google Drive upload info for a carousel PDF resource.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--slot-dir", required=True,
        help="Path to slot directory, e.g. posts/2026-04-02/1300",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be uploaded without opening Chrome",
    )
    args = parser.parse_args()

    slot_dir = Path(args.slot_dir)
    if not slot_dir.is_absolute():
        slot_dir = ROOT / slot_dir
    if not slot_dir.exists():
        print(f"ERROR: slot directory not found: {slot_dir}")
        sys.exit(1)

    run(slot_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
