"""
daily_run.py
------------
Master orchestrator for the carousel pipeline.
Chains all steps in sequence with clear logging and error handling.

Steps:
  1. research_sweep.py    -- scrape today's topics
  2. [Claude Code]        -- generates carousel.json files directly (no script needed)
     generate_content.py  -- validate existing carousel.json files
  3. generate_slides_py.py -- fetch Pinterest backgrounds + Pillow overlays
                              (for multi-lang carousel.json: generates for each --lang)
  3.5 build_resource.py   -- build trilingual PDFs (EN + FR + ES) for each slot
  3.7 upload_to_drive.py  -- upload all 3 PDFs to Google Drive, save links to carousel.json
  4. post_to_postfast.py  -- schedule all posts (FR first, EN +60 min, ES +120 min)
  5. analytics_pull.py    -- update hook-performance.json (optional, --analytics flag)

Usage:
  python scripts/daily_run.py                       # run for today (all langs)
  python scripts/daily_run.py --date 2026-03-27     # run for specific date
  python scripts/daily_run.py --langs fr,en,es      # post all languages (default: FR first)
  python scripts/daily_run.py --skip-images         # skip image generation
  python scripts/daily_run.py --skip-research       # skip research sweep
  python scripts/daily_run.py --skip-resource       # skip PDF resource build + Drive upload
  python scripts/daily_run.py --skip-drive          # skip Drive upload only
  python scripts/daily_run.py --analytics           # run analytics pull at the end
  python scripts/daily_run.py --dry-run             # full run but do not post
"""

import argparse
import json
import subprocess
import sys
import time
import logging
from datetime import date, datetime
from pathlib import Path

# Force UTF-8 on Windows console to prevent UnicodeEncodeError from non-ASCII
# characters in subprocess output (e.g. em-dashes rendered as replacement chars).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
ROOT       = SCRIPT_DIR.parent
LOGS_DIR   = ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

SLOTS = ["0600", "0730", "0900", "1100", "1300", "1600", "1800", "1930", "2100", "2230"]

# ── Logging setup ─────────────────────────────────────────────────────────────

def setup_logging(target_date: date) -> logging.Logger:
    log_path = LOGS_DIR / f"{target_date.isoformat()}.log"

    logger = logging.getLogger("daily_run")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    # File handler -- full detail
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(fh)

    # Console handler -- info and above
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(ch)

    logger.info(f"Log file: {log_path}")
    return logger


# ── Step runner ────────────────────────────────────────────────────────────────

def run_step(
    step_num: int,
    total_steps: int,
    label: str,
    cmd: list[str],
    logger: logging.Logger,
    dry_run_passthrough: bool = False,
) -> bool:
    """
    Run a subprocess step. Returns True on success, False on failure.
    Streams output live to both console and log file.
    """
    header = f"[{step_num}/{total_steps}] {label}"
    separator = "=" * 60
    logger.info(f"\n{separator}")
    logger.info(header)
    logger.info(separator)
    logger.debug(f"Command: {' '.join(cmd)}")

    t0 = time.time()

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(ROOT),
        )

        # Stream output line by line
        for line in proc.stdout:
            line = line.rstrip()
            logger.info(line)

        proc.wait()
        elapsed = time.time() - t0

        if proc.returncode == 0:
            logger.info(f"\n  Completed in {elapsed:.1f}s")
            return True
        else:
            logger.error(
                f"\n  FAILED (exit code {proc.returncode}) after {elapsed:.1f}s"
            )
            return False

    except FileNotFoundError as e:
        logger.error(f"\n  FAILED: command not found -- {e}")
        return False
    except Exception as e:
        logger.error(f"\n  FAILED: unexpected error -- {e}")
        return False


# ── Slide generation (per slot) ────────────────────────────────────────────────

def _is_multilang_carousel(carousel_path: Path) -> bool:
    """Return True if the carousel.json uses the multi-lang format."""
    try:
        data = json.loads(carousel_path.read_text(encoding="utf-8"))
        return any(k in data for k in ("en", "fr", "es"))
    except Exception:
        return False


def _has_x_synthesis(carousel_path: Path) -> bool:
    """Return True if the carousel.json has an X synthesis block."""
    try:
        data = json.loads(carousel_path.read_text(encoding="utf-8"))
        return "x" in data
    except Exception:
        return False


def _run_slot_slides(slot_dir: Path, script: Path, lang: str, logger: logging.Logger) -> bool:
    """Run generate_slides_py.py for one slot and one language. Returns True on success."""
    slot = slot_dir.name
    try:
        proc = subprocess.Popen(
            [sys.executable, str(script), str(slot_dir), "--lang", lang],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(ROOT),
        )
        for line in proc.stdout:
            logger.info("    " + line.rstrip())
        proc.wait()
        if proc.returncode == 0:
            return True
        else:
            logger.error(f"    Slot {slot} lang={lang} FAILED (exit code {proc.returncode})")
            return False
    except Exception as e:
        logger.error(f"    Slot {slot} lang={lang} FAILED: {e}")
        return False


def run_image_generation(
    target_date: date,
    step_num: int,
    total_steps: int,
    logger: logging.Logger,
    langs: list[str] | None = None,
) -> bool:
    """
    Run generate_slides_py.py once per slot directory.
    For multi-lang carousel.json, runs for each language in `langs`.
    Raw backgrounds are generated only for EN and reused for FR/ES.
    Returns True if all slots succeed (or no slots are found).
    """
    if langs is None:
        langs = ["en"]
    header = f"[{step_num}/{total_steps}] IMAGE GENERATION"
    separator = "=" * 60
    logger.info(f"\n{separator}")
    logger.info(header)
    logger.info(separator)

    date_str = target_date.isoformat()
    posts_dir = ROOT / "posts" / date_str
    script = SCRIPT_DIR / "generate_slides_py.py"

    if not posts_dir.exists():
        logger.error(f"  Posts directory not found: {posts_dir}")
        return False

    slot_dirs = sorted(
        d for d in posts_dir.iterdir()
        if d.is_dir() and (d / "carousel.json").exists()
    )

    if not slot_dirs:
        logger.error(f"  No carousel.json files found under {posts_dir}")
        return False

    logger.info(f"  Generating slides for {len(slot_dirs)} slots...\n")

    all_ok = True
    for i, slot_dir in enumerate(slot_dirs, 1):
        slot = slot_dir.name
        multilang = _is_multilang_carousel(slot_dir / "carousel.json")

        if multilang:
            slot_langs = list(langs)  # fr, en, es
            # Always add x if there is an X synthesis block
            if _has_x_synthesis(slot_dir / "carousel.json") and "x" not in slot_langs:
                slot_langs.append("x")
            logger.info(f"  [{i}/{len(slot_dirs)}] Slot {slot} (langs: {', '.join(slot_langs)})")
        else:
            slot_langs = ["en"]
            logger.info(f"  [{i}/{len(slot_dirs)}] Slot {slot}")

        t0 = time.time()
        slot_ok = True
        for lang in slot_langs:
            if multilang:
                logger.info(f"    Language: {lang.upper()}")
            ok = _run_slot_slides(slot_dir, script, lang, logger)
            if not ok:
                slot_ok = False
                all_ok = False

        elapsed = time.time() - t0
        if slot_ok:
            logger.info(f"    Slot {slot} done in {elapsed:.1f}s")
        else:
            logger.error(f"    Slot {slot} had failures after {elapsed:.1f}s")

    if all_ok:
        logger.info(f"\n  All slots completed.")
    else:
        logger.error(f"\n  Some slots failed during image generation.")

    return all_ok


# ── Resource PDF build (per slot) ─────────────────────────────────────────────

def run_resource_build(
    target_date: date,
    step_num: int,
    total_steps: int,
    logger: logging.Logger,
) -> bool:
    """
    Run build_resource.py --lang all for each slot that has a carousel.json.
    Builds resource_en.pdf + resource_fr.pdf + resource_es.pdf.
    Non-blocking: if a slot fails, log and continue. Returns True if all succeed.
    """
    header = f"[{step_num}/{total_steps}] BUILD RESOURCE PDF (EN + FR + ES)"
    separator = "=" * 60
    logger.info(f"\n{separator}")
    logger.info(header)
    logger.info(separator)

    date_str = target_date.isoformat()
    posts_dir = ROOT / "posts" / date_str
    script = SCRIPT_DIR / "build_resource.py"

    if not script.exists():
        logger.warning(f"  build_resource.py not found at {script} — skipping resource build.")
        return True

    if not posts_dir.exists():
        logger.error(f"  Posts directory not found: {posts_dir}")
        return False

    slot_dirs = sorted(
        d for d in posts_dir.iterdir()
        if d.is_dir() and (d / "carousel.json").exists()
    )

    if not slot_dirs:
        logger.warning(f"  No carousel.json files found — nothing to build resources for.")
        return True

    logger.info(f"  Building trilingual PDF resources for {len(slot_dirs)} slots...\n")

    all_ok = True
    for i, slot_dir in enumerate(slot_dirs, 1):
        slot = slot_dir.name

        # Check if all three language PDFs already exist
        existing = [l for l in ("en", "fr", "es") if (slot_dir / f"resource_{l}.pdf").exists()]
        if len(existing) == 3:
            logger.info(f"  [{i}/{len(slot_dirs)}] Slot {slot} — all 3 PDFs already exist, skipping.")
            continue

        missing = [l for l in ("en", "fr", "es") if l not in existing]
        logger.info(f"  [{i}/{len(slot_dirs)}] Slot {slot} — building {', '.join(missing).upper()}...")
        t0 = time.time()

        try:
            proc = subprocess.Popen(
                [sys.executable, str(script), "--slot-dir", str(slot_dir), "--lang", "all"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=str(ROOT),
            )
            for line in proc.stdout:
                logger.info("    " + line.rstrip())
            proc.wait()
            elapsed = time.time() - t0

            if proc.returncode == 0:
                logger.info(f"    Slot {slot} resource done in {elapsed:.1f}s")
            else:
                logger.error(f"    Slot {slot} resource FAILED (exit code {proc.returncode}) — continuing")
                all_ok = False

        except Exception as e:
            logger.error(f"    Slot {slot} resource FAILED: {e} — continuing")
            all_ok = False

    if all_ok:
        logger.info(f"\n  All resource PDFs completed.")
    else:
        logger.warning(f"\n  Some resource PDFs failed (non-blocking — posting will continue).")

    return all_ok


def run_drive_upload(
    target_date: date,
    step_num: int,
    total_steps: int,
    logger: logging.Logger,
    dry_run: bool = False,
) -> bool:
    """
    Run upload_to_drive.py --all for each slot that has resource PDFs.
    Uploads EN + FR + ES to the same Google Drive subfolder.
    Non-blocking: if a slot fails, log and continue.
    """
    header = f"[{step_num}/{total_steps}] UPLOAD TO GOOGLE DRIVE (EN + FR + ES)"
    separator = "=" * 60
    logger.info(f"\n{separator}")
    logger.info(header)
    logger.info(separator)

    date_str = target_date.isoformat()
    posts_dir = ROOT / "posts" / date_str
    script = SCRIPT_DIR / "upload_to_drive.py"

    if not script.exists():
        logger.warning(f"  upload_to_drive.py not found — skipping Drive upload.")
        return True

    if not posts_dir.exists():
        logger.error(f"  Posts directory not found: {posts_dir}")
        return False

    slot_dirs = sorted(
        d for d in posts_dir.iterdir()
        if d.is_dir() and any((d / f"resource_{l}.pdf").exists() for l in ("en", "fr", "es"))
    )

    if not slot_dirs:
        logger.warning(f"  No resource PDFs found — nothing to upload to Drive.")
        return True

    logger.info(f"  Uploading PDFs for {len(slot_dirs)} slots...\n")

    all_ok = True
    for i, slot_dir in enumerate(slot_dirs, 1):
        slot = slot_dir.name
        logger.info(f"  [{i}/{len(slot_dirs)}] Slot {slot}...")
        t0 = time.time()

        cmd = [sys.executable, str(script), "--slot-dir", str(slot_dir), "--all"]
        if dry_run:
            cmd.append("--dry-run")

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=str(ROOT),
            )
            for line in proc.stdout:
                logger.info("    " + line.rstrip())
            proc.wait()
            elapsed = time.time() - t0

            if proc.returncode == 0:
                logger.info(f"    Slot {slot} Drive upload done in {elapsed:.1f}s")
            else:
                logger.error(f"    Slot {slot} Drive upload FAILED (exit code {proc.returncode}) — continuing")
                all_ok = False

        except Exception as e:
            logger.error(f"    Slot {slot} Drive upload FAILED: {e} — continuing")
            all_ok = False

    if all_ok:
        logger.info(f"\n  All Drive uploads completed.")
    else:
        logger.warning(f"\n  Some Drive uploads failed (non-blocking — posting will continue).")

    return all_ok


# ── Pipeline summary ──────────────────────────────────────────────────────────

def print_summary(target_date: date, results: dict, logger: logging.Logger):
    date_str = target_date.isoformat()
    separator = "=" * 60
    logger.info(f"\n{separator}")
    logger.info("PIPELINE SUMMARY")
    logger.info(separator)

    all_ok = True
    for step_label, ok in results.items():
        status = "OK" if ok else "FAILED"
        logger.info(f"  {step_label:<30} {status}")
        if not ok:
            all_ok = False

    posts_dir = ROOT / "posts" / date_str
    if posts_dir.exists():
        slot_dirs = sorted(d for d in posts_dir.iterdir() if d.is_dir())
        logger.info(f"\n  Slots processed: {len(slot_dirs)}")
        for slot_dir in slot_dirs:
            has_carousel = (slot_dir / "carousel.json").exists()
            slides_dir = slot_dir / "slides"
            slide_count = len(list(slides_dir.glob("slide-*-final.jpg"))) if slides_dir.exists() else 0
            status_parts = []
            if has_carousel:
                status_parts.append("carousel.json")
            if slide_count:
                status_parts.append(f"{slide_count} slides")
            status_str = ", ".join(status_parts) if status_parts else "empty"
            logger.info(f"    {slot_dir.name}: {status_str}")

    logger.info(f"\n  Log: logs/{date_str}.log")
    logger.info(separator)

    if all_ok:
        logger.info("  Pipeline completed successfully.")
    else:
        logger.info("  Pipeline finished with errors. Check log above.")
    logger.info(f"{separator}\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Daily orchestrator for the carousel pipeline."
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Target date YYYY-MM-DD (default: today)",
    )
    parser.add_argument(
        "--skip-research",
        action="store_true",
        help="Skip step 1 (research_sweep.py); use existing research data",
    )
    parser.add_argument(
        "--skip-images",
        action="store_true",
        help="Skip step 3 (generate_slides_py.py); use existing slide images",
    )
    parser.add_argument(
        "--skip-resource",
        action="store_true",
        help="Skip step 3.5 (build_resource.py); do not build PDF resources",
    )
    parser.add_argument(
        "--skip-drive",
        action="store_true",
        help="Skip step 3.7 (upload_to_drive.py); do not upload PDFs to Google Drive",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Full pipeline run but pass --dry-run to posting step (no actual posts)",
    )
    parser.add_argument(
        "--langs",
        default="fr,en,es",
        help="Comma-separated languages for slides + posting (default: fr,en,es). "
             "Order controls posting sequence: FR posts first at slot time, EN +60 min, ES +120 min. "
             "LinkedIn and X always post EN only regardless of this setting.",
    )
    parser.add_argument(
        "--analytics",
        action="store_true",
        help="Run analytics_pull.py at the end to update hook-performance.json",
    )
    args = parser.parse_args()

    # Parse langs into a list
    args.langs_list = [l.strip().lower() for l in args.langs.split(",") if l.strip()]

    target_date = date.fromisoformat(args.date) if args.date else date.today()
    date_str = target_date.isoformat()

    logger = setup_logging(target_date)

    logger.info(f"\n{'#'*60}")
    logger.info(f"  CAROUSEL PIPELINE  |  {date_str}")
    if args.dry_run:
        logger.info("  MODE: DRY RUN (no posts will be created)")
    logger.info(f"{'#'*60}")

    pipeline_start = time.time()
    results = {}

    # Determine total active steps
    active_steps = []
    if not args.skip_research:
        active_steps.append("research")
    active_steps.append("content")  # validate carousel.json files
    if not args.skip_images:
        active_steps.append("images")
    if not args.skip_resource:
        active_steps.append("resource")
    if not args.skip_resource and not args.skip_drive:
        active_steps.append("drive")
    active_steps.append("post")
    if args.analytics:
        active_steps.append("analytics")
    total = len(active_steps)
    step_num = 0

    # ── Step 1: Research sweep ────────────────────────────────────────────────
    if not args.skip_research:
        step_num += 1
        # Try Python version first; fall back to Node.js version
        research_py = SCRIPT_DIR / "research_sweep.py"
        research_js = SCRIPT_DIR / "research-sweep.js"

        if research_py.exists():
            cmd = [sys.executable, str(research_py), "--date", date_str]
        elif research_js.exists():
            cmd = ["node", str(research_js)]
        else:
            logger.warning("  [WARN] No research_sweep script found. Skipping research step.")
            results["[1] Research Sweep"] = True
            step_num -= 1
            total -= 1
            args.skip_research = True

        if not args.skip_research:
            ok = run_step(
                step_num, total,
                "RESEARCH SWEEP",
                cmd,
                logger,
            )
            results["[1] Research Sweep"] = ok
            if not ok:
                logger.error("\nPipeline stopped at research sweep.")
                print_summary(target_date, results, logger)
                sys.exit(1)
    else:
        logger.info("\n[SKIPPED] Research sweep (--skip-research)")
        results["[1] Research Sweep"] = True

    # ── Step 2: Validate content (generated by Claude Code directly) ─────────
    step_num += 1
    validate_cmd = [
        sys.executable, str(SCRIPT_DIR / "generate_content.py"),
        "--date", date_str,
        "--validate",
    ]
    ok = run_step(
        step_num, total,
        "VALIDATE CONTENT (carousel.json files)",
        validate_cmd,
        logger,
    )
    results["[2] Validate Content"] = ok
    if not ok:
        logger.error("\nContent validation failed — run Claude Code to generate carousel.json files first.")
        print_summary(target_date, results, logger)
        sys.exit(1)

    # ── Step 3: Generate slides (images) ─────────────────────────────────────
    if not args.skip_images:
        step_num += 1
        ok = run_image_generation(target_date, step_num, total, logger, langs=args.langs_list)
        results["[3] Generate Slides"] = ok
        if not ok:
            logger.error("\nPipeline stopped at image generation.")
            print_summary(target_date, results, logger)
            sys.exit(1)
    else:
        logger.info("\n[SKIPPED] Image generation (--skip-images)")
        results["[3] Generate Slides"] = True

    # ── Step 3.5: Build resource PDFs ────────────────────────────────────────
    if not args.skip_resource:
        step_num += 1
        ok = run_resource_build(target_date, step_num, total, logger)
        results["[3.5] Build Resource PDF"] = ok
        # Non-blocking: do not sys.exit on failure, continue to posting
        if not ok:
            logger.warning("\n  Resource build had errors — pipeline continues.")
    else:
        logger.info("\n[SKIPPED] Resource PDF build (--skip-resource)")
        results["[3.5] Build Resource PDF"] = True

    # ── Step 3.7: Upload PDFs to Google Drive ────────────────────────────────
    if not args.skip_resource and not args.skip_drive:
        step_num += 1
        ok = run_drive_upload(target_date, step_num, total, logger, dry_run=args.dry_run)
        results["[3.7] Upload to Google Drive"] = ok
        if not ok:
            logger.warning("\n  Drive upload had errors — pipeline continues to posting.")
    else:
        reason = "--skip-resource" if args.skip_resource else "--skip-drive"
        logger.info(f"\n[SKIPPED] Google Drive upload ({reason})")
        results["[3.7] Upload to Google Drive"] = True

    # ── Step 4: Post to PostFast (one run per language) ──────────────────────
    step_num += 1
    post_ok = True
    for lang in args.langs_list:
        post_cmd = [
            sys.executable,
            str(SCRIPT_DIR / "post_to_postfast.py"),
            "--date", date_str,
            "--lang", lang,
        ]
        # Do NOT pass --now; let postfast schedule at the configured times
        if args.dry_run:
            post_cmd.append("--dry-run")

        lang_ok = run_step(
            step_num, total,
            f"POST TO POSTFAST (scheduled) [{lang.upper()}]",
            post_cmd,
            logger,
        )
        if not lang_ok:
            post_ok = False
            logger.error(f"\n  Posting failed for lang={lang} — slides are safe; retry with --lang {lang}")

    results["[4] Post to PostFast"] = post_ok

    # ── Step 5: Analytics pull (optional) ────────────────────────────────────
    if args.analytics:
        step_num += 1
        analytics_cmd = [
            sys.executable,
            str(SCRIPT_DIR / "analytics_pull.py"),
        ]
        if args.dry_run:
            analytics_cmd.append("--dry-run")

        ok = run_step(
            step_num, total,
            "ANALYTICS PULL (hook-performance.json)",
            analytics_cmd,
            logger,
        )
        results["[5] Analytics Pull"] = ok
        if not ok:
            logger.warning("\n  Analytics pull failed — pipeline continues.")

    # ── Summary ───────────────────────────────────────────────────────────────
    total_elapsed = time.time() - pipeline_start
    logger.info(f"\n  Total elapsed: {total_elapsed:.0f}s ({total_elapsed/60:.1f} min)")
    print_summary(target_date, results, logger)

    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
