"""
analytics_pull.py
-----------------
Pulls post performance from PostFast /social-posts/analytics and updates
hook-performance.json to feed the carousel feedback loop.

What it does:
  1. Fetches published posts + metrics from PostFast /social-posts/analytics
     (returns likes, comments, shares, impressions, reach, clicks per post)
  2. Matches each post back to a carousel slot (by publishedAt time + date)
  3. Reads carousel.json for hookFormula, structure, ctaWord, topic
  4. Writes hook-performance.json with:
     - Per-post performance records
     - Aggregated stats by hookFormula, structure, ctaWord
     - Auto-generated learnedRules for Claude to read next session

Note: PostFast /social-posts/analytics returns metrics for both TikTok and
Instagram natively — no separate Instagram Graph API token needed.
Metrics may be null for very recent posts (<2h) while platforms index them.

Usage:
    python scripts/analytics_pull.py                       # pull last 30 days
    python scripts/analytics_pull.py --since 2026-03-26    # since a date
    python scripts/analytics_pull.py --dry-run             # show without writing
    python scripts/analytics_pull.py --force               # re-pull even if already tracked
"""

import argparse
import json
import math
import sys
import time
from datetime import datetime, timezone, date, timedelta
from pathlib import Path

import requests

# Force UTF-8 on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT               = Path(__file__).resolve().parent.parent
CONFIG_PATH        = ROOT / "config.json"
HOOK_PERF_PATH     = ROOT / "hook-performance.json"
POSTS_DIR          = ROOT / "posts"

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# PostFast: fetch published posts WITH metrics via /social-posts/analytics
# ---------------------------------------------------------------------------

BASE_URL = "https://api.postfa.st"


def fetch_postfast_analytics(
    api_key: str,
    start_date: date,
    end_date: date,
    social_media_ids: list[str] | None = None,
) -> list[dict]:
    """
    Fetch published posts with performance metrics from PostFast.

    Uses GET /social-posts/analytics which returns:
      likes, comments, shares, impressions, reach, clicks
    for every published post in the date range.

    All metric values come back as strings (bigint) — we parse them to int.
    latestMetric is None for posts that haven't been indexed yet (<2h old).
    """
    headers = {"pf-api-key": api_key}
    params: dict = {
        "startDate": start_date.strftime("%Y-%m-%dT00:00:00.000Z"),
        "endDate":   end_date.strftime("%Y-%m-%dT23:59:59.999Z"),
    }
    if social_media_ids:
        params["socialMediaIds"] = ",".join(social_media_ids)

    r = requests.get(
        f"{BASE_URL}/social-posts/analytics",
        headers=headers,
        params=params,
        timeout=20,
    )
    r.raise_for_status()

    raw = r.json()
    # Response may be a list or {"data": [...]}
    posts = raw if isinstance(raw, list) else raw.get("data", [])
    return posts


def normalize_metrics(latest_metric: dict | None) -> dict | None:
    """
    Convert PostFast latestMetric (all strings) to our normalized int dict.
    Returns None if latestMetric is null (post not yet indexed).
    """
    if not latest_metric:
        return None

    def to_int(val) -> int:
        try:
            return int(val or 0)
        except (ValueError, TypeError):
            return 0

    impressions = to_int(latest_metric.get("impressions"))
    reach       = to_int(latest_metric.get("reach"))
    extras      = latest_metric.get("extras") or {}

    # saves may live in extras for Instagram (platform-specific)
    saves = to_int(extras.get("saved") or extras.get("saves") or 0)

    return {
        "views":    impressions or reach,   # impressions = total views; fall back to reach
        "reach":    reach,
        "likes":    to_int(latest_metric.get("likes")),
        "comments": to_int(latest_metric.get("comments")),
        "shares":   to_int(latest_metric.get("shares")),
        "clicks":   to_int(latest_metric.get("clicks")),
        "saves":    saves,
        "fetchedAt": latest_metric.get("fetchedAt", ""),
    }


# ---------------------------------------------------------------------------
# Slot matching: map a PostFast post to a carousel slot directory
# ---------------------------------------------------------------------------

def parse_postfast_dt(iso_str: str) -> datetime | None:
    """Parse PostFast ISO-8601 timestamp to UTC datetime."""
    if not iso_str:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            dt = datetime.strptime(iso_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            continue
    return None


SLOT_TIMES_UTC = {
    # Active slots (5 posts/day × 3 languages = 15 posts/day)
    "0730": (6, 30),
    "0900": (8, 0),
    "1300": (12, 0),
    "1800": (17, 0),
    "2100": (20, 0),
    # Legacy slots (kept for historical post matching — no longer in posting schedule)
    "0600": (5, 0),
    "1100": (10, 0),
    "1600": (15, 0),
    "1930": (18, 30),
    "2230": (21, 30),
}

# Allow ±35 min tolerance when matching scheduled time to slot
SLOT_TOLERANCE_MINUTES = 35


def find_slot_dir(scheduled_at_iso: str) -> Path | None:
    """
    Given a PostFast scheduledAt ISO string, find the matching slot directory.
    Tolerance: ±35 minutes around the expected slot UTC time.
    """
    dt = parse_postfast_dt(scheduled_at_iso)
    if not dt:
        return None

    post_date = dt.date()
    date_dir  = POSTS_DIR / post_date.isoformat()
    if not date_dir.exists():
        return None

    for slot, (utc_h, utc_m) in SLOT_TIMES_UTC.items():
        # Build a candidate UTC time (ignoring DST for matching — good enough for ±35m)
        expected = dt.replace(hour=utc_h, minute=utc_m, second=0, microsecond=0)
        diff_min = abs((dt - expected).total_seconds() / 60)
        if diff_min <= SLOT_TOLERANCE_MINUTES:
            slot_dir = date_dir / slot
            if slot_dir.exists() and (slot_dir / "carousel.json").exists():
                return slot_dir

    return None


# ---------------------------------------------------------------------------
# Carousel meta extraction
# ---------------------------------------------------------------------------

def read_carousel_meta(slot_dir: Path) -> dict:
    """Extract hook formula, structure, ctaWord, topic from carousel.json."""
    carousel_path = slot_dir / "carousel.json"
    if not carousel_path.exists():
        return {}
    try:
        data = json.loads(carousel_path.read_text(encoding="utf-8"))
        meta = data.get("meta", {})
        return {
            "hookFormula": meta.get("hookFormula", "unknown"),
            "structure":   meta.get("structure", meta.get("hookFormula", "unknown")),
            "ctaWord":     meta.get("ctaWord", ""),
            "topic":       meta.get("topic", ""),
        }
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# hook-performance.json: load + save
# ---------------------------------------------------------------------------

EMPTY_HOOK_PERF = {
    "lastUpdated":      "",
    "totalPostsTracked": 0,
    "analyticsNote":    "",
    "learnedRules":     [],
    "byHookFormula":    {},
    "byStructure":      {},
    "byCtaWord":        {},
    "posts":            [],
}


def load_hook_perf() -> dict:
    if HOOK_PERF_PATH.exists():
        try:
            return json.loads(HOOK_PERF_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return dict(EMPTY_HOOK_PERF)


def save_hook_perf(data: dict, dry_run: bool = False) -> None:
    data["lastUpdated"] = datetime.now(timezone.utc).isoformat()
    if dry_run:
        print("\n[DRY-RUN] hook-performance.json would be written:")
        print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])
    else:
        HOOK_PERF_PATH.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"\n  Saved: {HOOK_PERF_PATH}")


# ---------------------------------------------------------------------------
# Aggregation: build byHookFormula / byStructure / byCtaWord
# ---------------------------------------------------------------------------

def _safe_avg(values: list) -> float:
    vals = [v for v in values if v is not None and v >= 0]
    return round(sum(vals) / len(vals), 1) if vals else 0.0


def aggregate(posts: list[dict]) -> tuple[dict, dict, dict]:
    """Compute aggregated stats grouped by hookFormula, structure, ctaWord."""
    def group(key_fn):
        groups: dict[str, list] = {}
        for p in posts:
            if not p.get("metrics"):
                continue
            k = key_fn(p)
            if not k:
                continue
            groups.setdefault(k, []).append(p)
        return groups

    def stats(group_posts: list) -> dict:
        metrics_list = [p["metrics"] for p in group_posts if p.get("metrics")]
        n = len(metrics_list)
        if not n:
            return {"posts": len(group_posts), "metricsAvailable": 0}

        views    = [m.get("views", 0)    for m in metrics_list]
        likes    = [m.get("likes", 0)    for m in metrics_list]
        comments = [m.get("comments", 0) for m in metrics_list]
        saves    = [m.get("saves", 0)    for m in metrics_list]
        shares   = [m.get("shares", 0)   for m in metrics_list]

        avg_views = _safe_avg(views)
        result = {
            "posts":            len(group_posts),
            "metricsAvailable": n,
            "avg": {
                "views":    avg_views,
                "likes":    _safe_avg(likes),
                "comments": _safe_avg(comments),
                "saves":    _safe_avg(saves),
                "shares":   _safe_avg(shares),
            },
            "saveRate":    round(_safe_avg(saves)    / max(avg_views, 1), 5),
            "commentRate": round(_safe_avg(comments) / max(avg_views, 1), 5),
        }
        return result

    by_hook      = {k: stats(v) for k, v in group(lambda p: p.get("hookFormula")).items()}
    by_structure = {k: stats(v) for k, v in group(lambda p: p.get("structure")).items()}
    by_cta       = {k: stats(v) for k, v in group(lambda p: p.get("ctaWord")).items()}

    return by_hook, by_structure, by_cta


# ---------------------------------------------------------------------------
# Auto-generate learnedRules from aggregated data
# ---------------------------------------------------------------------------

def generate_learned_rules(
    by_hook: dict,
    by_structure: dict,
    by_cta: dict,
    posts: list[dict],
) -> list[str]:
    """
    Auto-generate plain-English rules for Claude based on performance data.

    Diagnostic framework (from Larry):
      High views + High saves  -> Scale immediately, this format is working
      High views + Low saves   -> Hook catches attention but content/CTA fails to land
      Low views  + High saves  -> Content resonates; hook is the bottleneck — test new hooks
      Low views  + Low saves   -> Full reset — new angle, format, hook category

    Decision thresholds (adapted from Larry for Instagram carousels):
      50K+ views  -> Double down on this hook formula immediately
      10K-50K     -> Healthy; keep rotating to find ceiling
      <1K (2x)    -> Drop the hook formula — not working
    """
    rules: list[str] = []
    posts_with_metrics = [p for p in posts if p.get("metrics")]

    if not posts_with_metrics:
        rules.append(
            "Not enough data yet to generate rules. Run analytics_pull.py again after posts accumulate metrics."
        )
        return rules

    # ── Account-level baseline ────────────────────────────────────────────────
    all_views = [p["metrics"].get("views", 0) for p in posts_with_metrics]
    all_saves = [p["metrics"].get("saves", 0) for p in posts_with_metrics]
    avg_views = sum(all_views) / len(all_views) if all_views else 0
    avg_saves = sum(all_saves) / len(all_saves) if all_saves else 0
    avg_save_rate = avg_saves / max(avg_views, 1)

    rules.append(
        f"Account baseline: {int(avg_views):,} avg views, {int(avg_saves):,} avg saves "
        f"({avg_save_rate*100:.2f}% save rate) across {len(posts_with_metrics)} posts with metrics."
    )

    # ── 2x2 Diagnostic: views vs saves (saves = proxy for content resonance) ─
    view_threshold = max(avg_views * 0.8, 1)   # above baseline = "high views"
    save_threshold = max(avg_save_rate * 0.8, 0.0001)  # above baseline = "high saves"

    high_v_high_s = [p for p in posts_with_metrics
                     if p["metrics"].get("views", 0) >= view_threshold
                     and p["metrics"].get("saves", 0) / max(p["metrics"].get("views", 1), 1) >= save_threshold]
    high_v_low_s  = [p for p in posts_with_metrics
                     if p["metrics"].get("views", 0) >= view_threshold
                     and p["metrics"].get("saves", 0) / max(p["metrics"].get("views", 1), 1) < save_threshold]
    low_v_high_s  = [p for p in posts_with_metrics
                     if p["metrics"].get("views", 0) < view_threshold
                     and p["metrics"].get("saves", 0) / max(p["metrics"].get("views", 1), 1) >= save_threshold]
    low_v_low_s   = [p for p in posts_with_metrics
                     if p["metrics"].get("views", 0) < view_threshold
                     and p["metrics"].get("saves", 0) / max(p["metrics"].get("views", 1), 1) < save_threshold]

    if high_v_high_s:
        hooks = list({p.get("hookFormula", "?") for p in high_v_high_s})
        rules.append(
            f"SCALE: {len(high_v_high_s)} post(s) have high views AND high save rate "
            f"(hook formulas: {', '.join(hooks)}). These are working — use them more."
        )
    if high_v_low_s:
        hooks = list({p.get("hookFormula", "?") for p in high_v_low_s})
        ctas  = list({p.get("ctaWord", "?") for p in high_v_low_s})
        rules.append(
            f"CTA PROBLEM: {len(high_v_low_s)} post(s) get views but low saves "
            f"(hooks: {', '.join(hooks)} | CTAs: {', '.join(ctas)}). "
            f"Hook is catching attention but content/CTA not landing — rotate CTAs, strengthen slides 6-8."
        )
    if low_v_high_s:
        hooks = list({p.get("hookFormula", "?") for p in low_v_high_s})
        rules.append(
            f"HOOK PROBLEM: {len(low_v_high_s)} post(s) have low views but high save rate "
            f"(hooks: {', '.join(hooks)}). Content resonates but hook isn't grabbing attention — "
            f"rewrite slide 1 with a stronger pattern-interrupt."
        )
    if low_v_low_s and len(low_v_low_s) >= 3:
        hooks = list({p.get("hookFormula", "?") for p in low_v_low_s})
        rules.append(
            f"RESET NEEDED: {len(low_v_low_s)} post(s) have both low views and low saves "
            f"(hooks: {', '.join(hooks)}). These formats are not working — try a new angle entirely."
        )

    # ── Hook formula rules (Larry thresholds: 50K double-down, <1K twice = drop) ──
    hook_with_data = {k: v for k, v in by_hook.items() if v.get("metricsAvailable", 0) >= 2}
    if hook_with_data:
        sorted_hooks = sorted(hook_with_data.items(), key=lambda x: x[1]["avg"]["views"], reverse=True)

        # Double-down candidates
        double_down = [(k, v) for k, v in sorted_hooks if v["avg"]["views"] >= 50_000]
        if double_down:
            for name, stats in double_down:
                rules.append(
                    f"DOUBLE DOWN: '{name}' averages {int(stats['avg']['views']):,} views (50K+ threshold). "
                    f"Use this hook formula in every available slot."
                )

        # Healthy rotation zone
        rotating = [(k, v) for k, v in sorted_hooks if 10_000 <= v["avg"]["views"] < 50_000]
        if rotating:
            names = ", ".join(f"'{k}'" for k, _ in rotating)
            rules.append(
                f"KEEP ROTATING: {names} — averaging 10K-50K views. Solid but not viral yet. "
                f"Keep testing variations of these hooks to find the ceiling."
            )

        # Drop candidates — low views, multiple posts
        drop = [(k, v) for k, v in hook_with_data.items()
                if v["avg"]["views"] < 1_000 and v.get("metricsAvailable", 0) >= 2]
        if drop:
            for name, stats in drop:
                rules.append(
                    f"DROP: '{name}' has averaged {int(stats['avg']['views']):,} views across "
                    f"{stats['metricsAvailable']} posts (below 1K threshold). Stop using this formula."
                )

        # Best vs worst comparison
        if len(sorted_hooks) >= 2:
            best, worst = sorted_hooks[0], sorted_hooks[-1]
            best_views  = best[1]["avg"]["views"]
            worst_views = worst[1]["avg"]["views"]
            if best_views > 0 and worst_views > 0:
                ratio = round(best_views / max(worst_views, 1), 1)
                rules.append(
                    f"Best hook formula: '{best[0]}' ({int(best_views):,} avg views) "
                    f"vs worst: '{worst[0]}' ({int(worst_views):,} avg views) — {ratio}x gap."
                )

        # Save rate leader
        sorted_by_save = sorted(hook_with_data.items(), key=lambda x: x[1].get("saveRate", 0), reverse=True)
        if sorted_by_save[0][1].get("saveRate", 0) > 0:
            top = sorted_by_save[0]
            rules.append(
                f"Highest save rate: '{top[0]}' hooks ({top[1].get('saveRate', 0)*100:.2f}% saves/views). "
                f"Use when the goal is bookmarks and DMs over raw reach."
            )

    # ── Structure rules ───────────────────────────────────────────────────────
    struct_with_data = {k: v for k, v in by_structure.items() if v.get("metricsAvailable", 0) >= 2}
    if len(struct_with_data) >= 2:
        sorted_struct = sorted(struct_with_data.items(), key=lambda x: x[1]["avg"]["views"], reverse=True)
        best_struct = sorted_struct[0]
        rules.append(
            f"Top structure: '{best_struct[0]}' — {int(best_struct[1]['avg']['views']):,} avg views. "
            f"Use as the default structure unless testing a new format."
        )

    # ── CTA word rules ────────────────────────────────────────────────────────
    cta_with_data = {k: v for k, v in by_cta.items() if v.get("metricsAvailable", 0) >= 2}
    if len(cta_with_data) >= 2:
        sorted_cta = sorted(cta_with_data.items(), key=lambda x: x[1].get("commentRate", 0), reverse=True)
        best_cta  = sorted_cta[0]
        worst_cta = sorted_cta[-1]
        best_rate  = best_cta[1].get("commentRate", 0)
        worst_rate = worst_cta[1].get("commentRate", 0)
        if best_rate > 0:
            ratio = round(best_rate / max(worst_rate, 0.0001), 1)
            rules.append(
                f"Best CTA word: '{best_cta[0]}' drives {ratio}x more comments than '{worst_cta[0]}'. "
                f"Use '{best_cta[0]}' when optimising for DM volume and comment engagement."
            )

    # ── Save rate benchmark ───────────────────────────────────────────────────
    rules.append(
        f"Save rate benchmark: {avg_save_rate*100:.2f}% account average. "
        f"Posts below this need stronger value delivery in slides 5-7 (the save-trigger zone)."
    )

    return rules


def generate_improvement_recommendations(
    by_hook: dict,
    by_structure: dict,
    posts: list[dict],
) -> dict:
    """
    Generate specific, actionable recommendations for the NEXT carousel batch.
    Returns a dict with 'nextHookFormula', 'nextStructure', 'avoidFormulas',
    'slideToImprove', and 'weeklyNote'.
    """
    posts_with_metrics = [p for p in posts if p.get("metrics")]
    if not posts_with_metrics:
        return {
            "nextHookFormula": "limiting_belief",
            "nextStructure":   "heres_why_youre_stuck",
            "avoidFormulas":   [],
            "slideToImprove":  "slide 1 hook",
            "weeklyNote":      "Not enough data yet — run again after 48h."
        }

    # Best hook formula by views
    hook_with_data = {k: v for k, v in by_hook.items() if v.get("metricsAvailable", 0) >= 1}
    sorted_hooks   = sorted(hook_with_data.items(), key=lambda x: x[1]["avg"]["views"], reverse=True)
    best_hook      = sorted_hooks[0][0] if sorted_hooks else "limiting_belief"
    avoid_hooks    = [k for k, v in hook_with_data.items()
                      if v["avg"]["views"] < 500 and v.get("metricsAvailable", 0) >= 2]

    # Best structure by save rate
    struct_with_data = {k: v for k, v in by_structure.items() if v.get("metricsAvailable", 0) >= 1}
    sorted_struct    = sorted(struct_with_data.items(), key=lambda x: x[1].get("saveRate", 0), reverse=True)
    best_struct      = sorted_struct[0][0] if sorted_struct else "heres_why_youre_stuck"

    # Identify which slide position is the weakest (by save rate proxy)
    # High views but low saves → CTA / value slides (6-8) need work
    all_views = [p["metrics"].get("views", 0) for p in posts_with_metrics]
    all_saves = [p["metrics"].get("saves", 0) for p in posts_with_metrics]
    avg_v = sum(all_views) / len(all_views) if all_views else 1
    avg_s = sum(all_saves) / len(all_saves) if all_saves else 0
    save_rate = avg_s / max(avg_v, 1)

    if save_rate < 0.01:
        slide_to_improve = "slides 5-8 (value + CTA) — save rate is below 1%, content not resonating"
    elif avg_v < 1000:
        slide_to_improve = "slide 1 (hook) — views are low, hook is not stopping the scroll"
    else:
        slide_to_improve = "slide 8 (CTA) — test a stronger call-to-action word"

    # Weekly note
    total = len(posts_with_metrics)
    weekly_note = (
        f"Based on {total} posts with metrics: "
        f"lean into '{best_hook}' hooks with '{best_struct}' structure. "
        f"Focus improvement on {slide_to_improve}."
    )

    return {
        "nextHookFormula": best_hook,
        "nextStructure":   best_struct,
        "avoidFormulas":   avoid_hooks,
        "slideToImprove":  slide_to_improve,
        "weeklyNote":      weekly_note,
    }


# ---------------------------------------------------------------------------
# Main pull logic
# ---------------------------------------------------------------------------

def run_pull(since_date: date | None, dry_run: bool, force: bool) -> None:
    config = load_config()

    pf_api_key = config["postfast"]["apiKey"]
    ig_acct_id = config["postfast"]["accounts"]["instagram"]["id"]

    # Date range: since_date → today, or last 30 days by default
    end_date   = date.today()
    start_date = since_date or (end_date - timedelta(days=30))

    hook_perf = load_hook_perf()
    already_tracked = {p["postfastId"] for p in hook_perf.get("posts", [])}

    print(f"\n{'='*60}")
    print(f"  Analytics pull  |  {'dry-run' if dry_run else 'live'}")
    print(f"  Range: {start_date} → {end_date}")
    print(f"{'='*60}")

    # 1. Fetch posts + metrics from PostFast /social-posts/analytics
    print("\n[1/3] Fetching analytics from PostFast /social-posts/analytics...")
    try:
        pf_posts = fetch_postfast_analytics(pf_api_key, start_date, end_date)
    except requests.HTTPError as e:
        print(f"  ERROR fetching analytics: {e.response.status_code} {e.response.text}")
        return

    print(f"  Posts returned: {len(pf_posts)}")

    # Skip posts published < 2 hours ago (platforms take time to index metrics)
    now_utc = datetime.now(timezone.utc)
    INDEXING_DELAY = timedelta(hours=2)
    mature_posts, skipped_fresh = [], 0
    for p in pf_posts:
        dt = parse_postfast_dt(p.get("publishedAt") or p.get("scheduledAt") or "")
        if dt and (now_utc - dt) < INDEXING_DELAY:
            skipped_fresh += 1
        else:
            mature_posts.append(p)
    pf_posts = mature_posts
    if skipped_fresh:
        print(f"  Skipped {skipped_fresh} post(s) published <2h ago (indexing delay — run again later)")

    # 2. Match each post to a carousel slot + build records
    print(f"\n[2/3] Matching {len(pf_posts)} posts to carousel slots...")
    new_records: list[dict] = []
    updated_records: list[dict] = []
    unmatched = 0
    with_metrics = 0

    for pf_post in pf_posts:
        post_id  = pf_post.get("id", "")
        platform = "instagram" if pf_post.get("socialMediaId") == ig_acct_id else "tiktok"
        pub_at   = pf_post.get("publishedAt") or pf_post.get("scheduledAt") or ""

        # Skip already tracked (unless --force)
        if post_id in already_tracked and not force:
            continue

        # Match to slot directory
        slot_dir = find_slot_dir(pub_at)
        if not slot_dir:
            unmatched += 1
            continue

        post_date = parse_postfast_dt(pub_at).date().isoformat() if parse_postfast_dt(pub_at) else "unknown"
        slot      = slot_dir.name

        # Read carousel meta
        meta = read_carousel_meta(slot_dir)

        # Normalise metrics from PostFast latestMetric
        metrics = normalize_metrics(pf_post.get("latestMetric"))
        if metrics:
            with_metrics += 1
            views = metrics.get("views", 0)
            likes = metrics.get("likes", 0)
            saves = metrics.get("saves", 0)
            print(f"  [{platform.upper()}] {post_date}/{slot}  views={views:,}  likes={likes:,}  saves={saves:,}")
        else:
            print(f"  [{platform.upper()}] {post_date}/{slot}  (metrics not yet available)")

        record = {
            "date":           post_date,
            "slot":           slot,
            "platform":       platform,
            "postfastId":     post_id,
            "platformPostId": pf_post.get("platformPostId", ""),
            "hookFormula":    meta.get("hookFormula", "unknown"),
            "structure":      meta.get("structure", "unknown"),
            "ctaWord":        meta.get("ctaWord", ""),
            "topic":          meta.get("topic", "")[:120],
            "metrics":        metrics,
            "publishedAt":    pub_at,
            "pulledAt":       datetime.now(timezone.utc).isoformat(),
        }

        if post_id in already_tracked:
            updated_records.append(record)
        else:
            new_records.append(record)

    print(f"\n  New records:         {len(new_records)}")
    print(f"  Updated records:     {len(updated_records)}")
    print(f"  With metrics:        {with_metrics}")
    print(f"  Unmatched:           {unmatched}")

    # 3. Update hook-performance.json
    print("\n[3/3] Updating hook-performance.json...")

    existing  = [p for p in hook_perf.get("posts", [])
                 if p["postfastId"] not in {r["postfastId"] for r in updated_records}]
    all_posts = existing + new_records + updated_records
    all_posts.sort(key=lambda p: (p.get("date", ""), p.get("slot", "")))

    by_hook, by_structure, by_cta = aggregate(all_posts)
    learned_rules = generate_learned_rules(by_hook, by_structure, by_cta, all_posts)
    recommendations = generate_improvement_recommendations(by_hook, by_structure, all_posts)

    posts_with_metrics = sum(1 for p in all_posts if p.get("metrics"))

    hook_perf.update({
        "totalPostsTracked":  len(all_posts),
        "metricsAvailable":   posts_with_metrics,
        "analyticsNote":      (
            f"Metrics pulled directly from PostFast /social-posts/analytics. "
            f"Last range: {start_date} to {end_date}. "
            f"{posts_with_metrics}/{len(all_posts)} posts have metrics."
        ),
        "learnedRules":       learned_rules,
        "recommendations":    recommendations,
        "byHookFormula":      by_hook,
        "byStructure":        by_structure,
        "byCtaWord":          by_cta,
        "posts":              all_posts,
    })

    save_hook_perf(hook_perf, dry_run=dry_run)

    print(f"\n  Posts tracked:       {len(all_posts)}")
    print(f"  Posts with metrics:  {posts_with_metrics}")
    print(f"\n  Learned rules:")
    for rule in learned_rules:
        print(f"    - {rule[:120]}")

    print(f"\n{'='*60}\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Pull analytics and update hook-performance.json")
    parser.add_argument("--since",   default=None, help="Pull posts since YYYY-MM-DD (default: last 30 days)")
    parser.add_argument("--dry-run", action="store_true", help="Show output without writing")
    parser.add_argument("--force",   action="store_true", help="Re-pull even if already tracked")
    args = parser.parse_args()

    since = date.fromisoformat(args.since) if args.since else None
    run_pull(since_date=since, dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    main()
