"""
research_sweep.py
-----------------
Three-source research sweep for the carousel pipeline.

Sources (all free, no API keys required):
  1. DuckDuckGo   -- general web coverage
  2. Reddit       -- audience voice, top comments, upvote-weighted engagement
  3. Hacker News  -- builder/maker friction via Algolia public API

Scoring:
  - Engagement score   : log(upvotes/points + 1) * 2 + log(comments + 1)
  - Recency score      : linear decay over 30 days (0.0 to 1.0)
  - Convergence score  : +2.0 per additional source covering the same theme
  - Final score        : sum of all three

Output: research/YYYY-MM-DD.json
  Includes: scoredTopics (ranked), bySource breakdown, convergenceSignals,
  rawHeadlines, and a summary block for quick reading.

Usage:
    python scripts/research_sweep.py
    python scripts/research_sweep.py --date 2026-03-30
    python scripts/research_sweep.py --force
    python scripts/research_sweep.py --quick     # fewer results, faster
"""

import argparse
import json
import math
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Force UTF-8 on Windows console to avoid UnicodeEncodeError
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT         = Path(__file__).resolve().parent.parent
CONFIG_PATH  = ROOT / "config.json"
RESEARCH_DIR = ROOT / "research"

# ---------------------------------------------------------------------------
# Query banks — targeting friction and aspiration, not news
# ---------------------------------------------------------------------------

WEB_QUERIES = [
    "AI tools not working expected results 2026",
    "make money with AI side hustle actually works",
    "vibe coding apps built with AI no code",
    "AI workflow automation income freelance",
    "AI tools wasting money not worth it",
    "how people are using AI to earn online",
]

# Reddit queries via DuckDuckGo site:reddit.com
# More reliable than direct Reddit API (which rate-limits aggressively).
# DDG caches Reddit content, returns title + snippet including comment excerpts.
REDDIT_QUERIES = [
    "site:reddit.com AI tools not working disappointing 2026",
    "site:reddit.com make money AI side hustle results",
    "site:reddit.com built app with AI vibe coding",
    "site:reddit.com AI automation income freelance",
    "site:reddit.com AI productivity workflow problems",
]

HN_QUERIES = [
    "AI productivity workflow",
    "built with AI side project",
    "AI tools income automation",
    "AI not working disappointing",
    "vibe coding AI app",
]

# How many results to fetch per query
MAX_WEB          = 8
MAX_REDDIT       = 5   # top posts per subreddit
MAX_HN           = 6
MAX_REDDIT_QUICK = 3
MAX_HN_QUICK     = 4

REDDIT_DELAY = 2.0   # seconds between Reddit requests (be polite)
HN_DELAY     = 1.0   # seconds between HN requests
WEB_DELAY    = 1.2   # seconds between DDG requests

RECENCY_DAYS = 30    # decay window
CONVERGENCE_BONUS = 2.0

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_config() -> dict:
    if not CONFIG_PATH.exists():
        print(f"[ERROR] config.json not found at {CONFIG_PATH}")
        sys.exit(1)
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def ensure_research_dir() -> None:
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)


def output_path(date_str: str) -> Path:
    return RESEARCH_DIR / f"{date_str}.json"


def bare_domain(url: str) -> str:
    try:
        host = urllib.parse.urlparse(url).netloc
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return url


def normalize_text(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def title_tokens(title: str) -> set[str]:
    """Return meaningful words from a title (stop-words removed)."""
    STOP = {
        "a","an","the","and","or","but","in","on","at","to","for","of","with",
        "is","are","was","were","be","been","has","have","had","do","does",
        "this","that","it","its","by","from","as","not","no","how","what",
        "why","when","who","i","my","we","you","your","their","they",
        "can","will","would","could","should","may","might","2026","2025",
    }
    words = normalize_text(title).split()
    return {w for w in words if len(w) > 2 and w not in STOP}


def jaccard_similarity(set_a: set, set_b: set) -> float:
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def days_old(timestamp_str: str) -> float:
    """Return age in days from an ISO-8601 string or Unix timestamp string."""
    now = datetime.now(timezone.utc)
    if not timestamp_str:
        return RECENCY_DAYS  # unknown date = treat as old

    # Unix integer timestamp
    try:
        ts = int(timestamp_str)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        return max(0.0, (now - dt).total_seconds() / 86400)
    except (ValueError, TypeError, OSError):
        pass

    # ISO-8601 string
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(timestamp_str[:19], fmt[:len(fmt)])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return max(0.0, (now - dt).total_seconds() / 86400)
        except ValueError:
            continue

    return RECENCY_DAYS


def recency_score(age_days: float) -> float:
    """Linear decay: 1.0 today, 0.0 at RECENCY_DAYS days old."""
    return max(0.0, 1.0 - age_days / RECENCY_DAYS)


def engagement_score(upvotes: int, comments: int) -> float:
    return math.log(upvotes + 1) * 2 + math.log(comments + 1)


def http_get(url: str, timeout: int = 15, reddit: bool = False) -> dict | list | None:
    """Simple JSON GET. Uses a Reddit-compatible User-Agent when reddit=True."""
    if reddit:
        # Reddit requires a non-browser, descriptive User-Agent
        ua = "python:carousel-pipeline:v2.0 (by /u/carousel-pipeline-bot)"
    else:
        ua = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": ua,
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def deduplicate_by_url(items: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for item in items:
        url = item.get("url", "")
        if url and url not in seen:
            seen.add(url)
            out.append(item)
    return out


# ---------------------------------------------------------------------------
# Source 1: DuckDuckGo web
# ---------------------------------------------------------------------------

def search_web(query: str, max_results: int) -> list[dict]:
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS  # fallback to old package name
        except ImportError:
            print("  [WARN] ddgs not installed. Run: pip install ddgs")
            return []

    results: list[dict] = []
    try:
        with DDGS() as ddgs:
            raw = ddgs.text(query, max_results=max_results, safesearch="off")
            for item in (raw or []):
                url = (item.get("href") or item.get("url") or "").strip()
                if not url:
                    continue
                results.append({
                    "source":    "web",
                    "title":     (item.get("title") or "").strip(),
                    "url":       url,
                    "snippet":   (item.get("body") or item.get("snippet") or "").strip(),
                    "domain":    bare_domain(url),
                    "upvotes":   0,
                    "comments":  0,
                    "timestamp": (item.get("published") or item.get("date") or ""),
                    "subreddit": "",
                    "top_comment": "",
                })
    except Exception as exc:
        print(f"  [WARN] DDG query failed: {query!r} -> {exc}")
    return results


# ---------------------------------------------------------------------------
# Source 2: Reddit via DuckDuckGo site:reddit.com
# (Direct Reddit API blocks without OAuth; DDG is more reliable)
# ---------------------------------------------------------------------------

def search_reddit_via_ddg(query: str, max_results: int) -> list[dict]:
    """
    Search Reddit using DuckDuckGo's site:reddit.com filter.
    Returns results that look like Reddit posts with subreddit as domain.
    No engagement scores — Reddit items receive a fixed engagement bonus
    to reflect that Reddit discussions are inherently high-signal.
    """
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return []

    results: list[dict] = []
    try:
        with DDGS() as ddgs:
            raw = ddgs.text(query, max_results=max_results, safesearch="off")
            for item in (raw or []):
                url     = (item.get("href") or item.get("url") or "").strip()
                title   = (item.get("title") or "").strip()
                snippet = (item.get("body") or item.get("snippet") or "").strip()

                if not url or "reddit.com" not in url:
                    continue

                # Extract subreddit from URL: /r/SubName/...
                sub_match = re.search(r"reddit\.com/r/([^/]+)", url)
                subreddit = f"r/{sub_match.group(1)}" if sub_match else "r/reddit"

                results.append({
                    "source":      "reddit",
                    "title":       title,
                    "url":         url,
                    "snippet":     snippet,
                    "domain":      subreddit,
                    "upvotes":     10,    # fixed signal weight for Reddit posts
                    "comments":    5,
                    "timestamp":   (item.get("published") or item.get("date") or ""),
                    "subreddit":   subreddit,
                    "top_comment": snippet,  # DDG snippet often contains comment text
                })
    except Exception as exc:
        print(f"  [WARN] Reddit/DDG query failed: {query!r} -> {exc}")

    return results


# ---------------------------------------------------------------------------
# Source 3: Hacker News via Algolia public API
# ---------------------------------------------------------------------------

def search_hn(query: str, max_results: int) -> list[dict]:
    """
    Search Hacker News stories via Algolia (free, no API key).
    Filters to last 30 days.
    """
    cutoff = int((datetime.now(timezone.utc) - timedelta(days=30)).timestamp())
    params = urllib.parse.urlencode({
        "query":          query,
        "tags":           "story",
        "numericFilters": f"created_at_i>{cutoff}",
        "hitsPerPage":    max_results,
    })
    url = f"https://hn.algolia.com/api/v1/search?{params}"
    data = http_get(url)

    results: list[dict] = []
    if not data:
        return results

    for hit in (data.get("hits") or []):
        title    = (hit.get("title") or "").strip()
        story_id = hit.get("objectID", "")
        hn_url   = f"https://news.ycombinator.com/item?id={story_id}"
        ext_url  = hit.get("url") or hn_url
        points   = int(hit.get("points") or 0)
        comments = int(hit.get("num_comments") or 0)
        created  = str(hit.get("created_at_i") or 0)
        author   = hit.get("author") or ""

        results.append({
            "source":      "hn",
            "title":       title,
            "url":         hn_url,
            "external_url": ext_url,
            "snippet":     f"by {author} | HN" if author else "HN",
            "domain":      bare_domain(ext_url) if ext_url != hn_url else "news.ycombinator.com",
            "upvotes":     points,
            "comments":    comments,
            "timestamp":   created,
            "subreddit":   "",
            "top_comment": "",
        })

    return results


# ---------------------------------------------------------------------------
# Convergence detection
# ---------------------------------------------------------------------------

def compute_convergence(items: list[dict]) -> list[dict]:
    """
    For every item, count how many other items (from DIFFERENT sources)
    have a Jaccard token similarity >= 0.25 with it.
    Stores the count as item["convergence"] (0 = unique, 1+ = cross-platform).
    Also collects convergenceSignals for the summary.
    """
    token_sets = [title_tokens(item["title"]) for item in items]
    signals: list[dict] = []

    for i, item in enumerate(items):
        matches = []
        for j, other in enumerate(items):
            if i == j:
                continue
            if other["source"] == item["source"]:
                continue
            sim = jaccard_similarity(token_sets[i], token_sets[j])
            if sim >= 0.25:
                matches.append({"title": other["title"], "source": other["source"], "sim": round(sim, 2)})

        item["convergence"] = len(set(m["source"] for m in matches))
        if item["convergence"] >= 1:
            signals.append({
                "title":   item["title"],
                "sources": list({item["source"]} | {m["source"] for m in matches}),
                "score":   item["convergence"],
            })

    # Deduplicate convergence signals by title similarity
    seen: list[set] = []
    unique_signals: list[dict] = []
    for sig in sorted(signals, key=lambda x: -x["score"]):
        t = title_tokens(sig["title"])
        if not any(jaccard_similarity(t, s) >= 0.4 for s in seen):
            seen.append(t)
            unique_signals.append(sig)

    return unique_signals[:10]


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_item(item: dict) -> float:
    eng  = engagement_score(item.get("upvotes", 0), item.get("comments", 0))
    age  = days_old(item.get("timestamp", ""))
    rec  = recency_score(age)
    conv = item.get("convergence", 0) * CONVERGENCE_BONUS
    return round(eng + rec + conv, 3)


# ---------------------------------------------------------------------------
# Main sweep
# ---------------------------------------------------------------------------

def run_sweep(date_str: str, force: bool = False, quick: bool = False) -> dict:
    ensure_research_dir()
    out_path = output_path(date_str)

    if out_path.exists() and not force:
        print(f"[INFO] Research already exists for {date_str}. Use --force to redo.")
        with open(out_path, encoding="utf-8") as f:
            return json.load(f)

    load_config()  # validate config exists

    max_reddit = MAX_REDDIT_QUICK if quick else MAX_REDDIT
    max_hn     = MAX_HN_QUICK     if quick else MAX_HN

    print(f"\n{'='*60}")
    print(f"  Research sweep  |  {date_str}  {'(quick)' if quick else ''}")
    print(f"{'='*60}")

    all_items: list[dict] = []
    by_source: dict = {"web": [], "reddit": [], "hn": []}

    # ── DuckDuckGo ─────────────────────────────────────────────────────────
    print(f"\n[1/3] DuckDuckGo web  ({len(WEB_QUERIES)} queries)")
    for i, q in enumerate(WEB_QUERIES, 1):
        print(f"  [{i}/{len(WEB_QUERIES)}] {q!r} ...", end=" ", flush=True)
        results = search_web(q, MAX_WEB)
        print(f"{len(results)} results")
        by_source["web"].extend(results)
        if i < len(WEB_QUERIES):
            time.sleep(WEB_DELAY)

    # ── Reddit (via DDG site:reddit.com) ───────────────────────────────────
    print(f"\n[2/3] Reddit via DuckDuckGo  ({len(REDDIT_QUERIES)} queries)")
    reddit_raw: list[dict] = []
    for i, q in enumerate(REDDIT_QUERIES, 1):
        print(f"  [{i}/{len(REDDIT_QUERIES)}] {q[:60]!r} ...", end=" ", flush=True)
        results = search_reddit_via_ddg(q, max_reddit)
        print(f"{len(results)} posts")
        reddit_raw.extend(results)
        if i < len(REDDIT_QUERIES):
            time.sleep(REDDIT_DELAY)

    by_source["reddit"] = deduplicate_by_url(reddit_raw)

    # ── Hacker News ────────────────────────────────────────────────────────
    print(f"\n[3/3] Hacker News (Algolia)  ({len(HN_QUERIES)} queries)")
    for i, q in enumerate(HN_QUERIES, 1):
        print(f"  [{i}/{len(HN_QUERIES)}] {q!r} ...", end=" ", flush=True)
        results = search_hn(q, max_hn)
        print(f"{len(results)} stories")
        by_source["hn"].extend(results)
        if i < len(HN_QUERIES):
            time.sleep(HN_DELAY)

    # ── Deduplicate each source ────────────────────────────────────────────
    for src in by_source:
        by_source[src] = deduplicate_by_url(by_source[src])

    # ── Merge all items ────────────────────────────────────────────────────
    for src_items in by_source.values():
        all_items.extend(src_items)

    # ── Convergence detection ─────────────────────────────────────────────
    print("\n  Computing cross-platform convergence...")
    convergence_signals = compute_convergence(all_items)
    print(f"  Convergence signals: {len(convergence_signals)}")

    # ── Score and rank ─────────────────────────────────────────────────────
    for item in all_items:
        item["finalScore"] = score_item(item)

    scored = sorted(all_items, key=lambda x: x["finalScore"], reverse=True)

    # Keep top 40 for Claude to read
    scored_top = scored[:40]

    # ── Raw headlines list (backward compatibility) ───────────────────────
    raw_headlines = [
        item["title"] for item in scored_top if item.get("title")
    ]

    # ── Summary ───────────────────────────────────────────────────────────
    summary = {
        "totalResults": len(all_items),
        "sourceCounts": {
            "web":    len(by_source["web"]),
            "reddit": len(by_source["reddit"]),
            "hn":     len(by_source["hn"]),
        },
        "topScoredTitles": raw_headlines[:10],
        "convergenceSignalCount": len(convergence_signals),
        "highestEngagementPost": (
            max(all_items, key=lambda x: x.get("upvotes", 0), default={})
            .get("title", "")
        ),
    }

    payload = {
        "date":                date_str,
        "generatedAt":         datetime.now(timezone.utc).isoformat(),
        "summary":             summary,
        "scoredTopics":        scored_top,
        "convergenceSignals":  convergence_signals,
        "bySource":            by_source,
        "rawHeadlines":        raw_headlines,   # kept for daily_run.py compat
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    # ── Print summary ──────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  Saved: {out_path}")
    print(f"  Web results:    {summary['sourceCounts']['web']}")
    print(f"  Reddit posts:   {summary['sourceCounts']['reddit']}")
    print(f"  HN stories:     {summary['sourceCounts']['hn']}")
    print(f"  Total unique:   {summary['totalResults']}")
    print(f"  Convergence:    {len(convergence_signals)} cross-platform signals")
    print()

    if convergence_signals:
        print("  Top convergence signals (same topic, multiple sources):")
        for sig in convergence_signals[:5]:
            sources_str = " + ".join(sig["sources"])
            print(f"    [{sources_str}] {sig['title'][:80]}")
        print()

    print("  Top 10 scored topics:")
    for i, item in enumerate(scored_top[:10], 1):
        src = item["source"].upper().ljust(6)
        score = f"{item['finalScore']:.1f}"
        upv   = item.get("upvotes", 0)
        cmt   = item.get("comments", 0)
        conv  = item.get("convergence", 0)
        conv_tag = f" [x-platform]" if conv > 0 else ""
        print(f"    {i:>2}. [{src} {score:>5}] (up:{upv} cmt:{cmt}){conv_tag}")
        print(f"        {item['title'][:90]}")

    print(f"\n{'='*60}\n")

    return payload


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Three-source research sweep: DuckDuckGo + Reddit + HN"
    )
    parser.add_argument(
        "--date",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="Target date YYYY-MM-DD (default: today)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing research file",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Fewer results per query, faster run",
    )
    args = parser.parse_args()

    run_sweep(date_str=args.date, force=args.force, quick=args.quick)


if __name__ == "__main__":
    main()
