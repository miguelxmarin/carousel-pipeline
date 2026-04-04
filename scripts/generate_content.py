"""
generate_content.py
-------------------
Utility script for the carousel pipeline.

Content is generated directly by Claude Code in the conversation —
no external API needed. This script provides:
  - Carousel structure reference (slots, roles, formats)
  - validate_carousel()  — checks a carousel dict for errors
  - save_carousel()      — writes carousel.json in the correct multilang format
  - main()               — CLI to check/validate existing carousel.json files

Usage:
  python scripts/generate_content.py --validate --date 2026-04-04
  python scripts/generate_content.py --status
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
ROOT       = SCRIPT_DIR.parent
CONFIG_PATH = ROOT / "config.json"

with open(CONFIG_PATH, encoding="utf-8") as f:
    CONFIG = json.load(f)

# ── Constants ─────────────────────────────────────────────────────────────────
CREATOR  = CONFIG["creator"]
POSTING  = CONFIG["posting"]

# 2 posting slots per day — best performers from analytics (0730=258 views, 1300=263 views)
SLOTS = ["0730", "1300"]
TIMES = ["07:30", "13:00"]

STRUCTURES = [
    "Here's Why You're Stuck",
    "Myth to Truth",
    "Warning Sign",
    "The Method",
    "Before and After",
]

HOOK_FORMULAS = [
    'Everyone [does X]. Nobody [does Y].',
    'X years of [thing] taught me one thing:',
    'The [topic] nobody talks about:',
    'Stop [common action]. Start [better action].',
    'You are not [problem]. You are [reframe].',
]

SLIDE_ROLES = [
    "HOOK", "CREDIBILITY", "PROBLEM", "AGITATION",
    "INSIGHT", "PROOF", "METHOD", "LIFT", "LOOP", "CTA",
]

# ── Creator system prompt (reference for Claude Code to use directly) ─────────
CREATOR_HANDLE = "@" + CREATOR.get("name", "yourcreator").lstrip("@")

SYSTEM_PROMPT = f"""You are a world-class social media content strategist for {CREATOR_HANDLE}.

CREATOR PROFILE:
- Handle: {CREATOR_HANDLE}
- Niche: {CREATOR['niche']}
- Audience: {CREATOR['audience']}
- Core message: {CREATOR['coreMessage']}
- Brand voice: {CREATOR['brandVoice']}

THE CAROUSEL METHOD - MANDATORY RULES:

1. STRUCTURE (choose one per carousel):
   - "Here's Why You're Stuck"
   - "Myth to Truth"
   - "Warning Sign"
   - "The Method"
   - "Before and After"

2. HOOK FORMULAS (use exactly one per carousel):
   - "Everyone [does X]. Nobody [does Y]."
   - "X years of [thing] taught me one thing:"
   - "The [topic] nobody talks about:"
   - "Stop [common action]. Start [better action]."
   - "You are not [problem]. You are [reframe]."

3. SLIDE ROLES (exactly 9 slides in this order):
   1. HOOK
   2. TENSION
   3. SHIFT
   4. PROOF
   5. MICRO-REWARD
   6. BUILD
   7. EDGE
   8. CTA
   9. CLOSER

4. THEME ALTERNATION:
   - Odd slides (1, 3, 5, 7, 9): theme = "dark"
   - Even slides (2, 4, 6, 8, 10): theme = "light"

5. HOOK RULES (slide 1):
   - Start from FEELING not topic.
   - NEVER use news-reporting style.
   - Hook must create immediate tension or curiosity.
   - Match exactly one of the 5 hook formulas above.

6. LANGUAGE RULES:
   - NO em-dashes anywhere.
   - NO contractions anywhere (write "do not" not "don't").
   - Be direct. Short sentences. Active voice.
   - Each slide headline: maximum 12 words.
   - Each slide body: maximum 30 words.

7. CAPTION FORMAT:
   - Line 1: hook line (matches slide 1 energy)
   - Blank line
   - 1-2 lines of value tease
   - Blank line
   - CTA: "Comment [WORD] and I will [thing]."
   - Blank line
   - Exactly 5 relevant hashtags

8. BACKGROUND QUERY (bgQuery):
   - Every slide must have a bgQuery: 4-6 word Pinterest search phrase
   - Match the slide's visual mood and theme (dark/light)

9. X SYNTHESIS (4-slide condensed version):
   - Slide 1 HOOK (dark): sharp one-liner, instant tension
   - Slide 2 PROBLEM (light): core friction, plain words
   - Slide 3 SOLUTION (dark): key insight, concrete + actionable
   - Slide 4 CTA (light): direct call to action with CTA word
   - Caption: punchy, X-native, max 3 hashtags

OUTPUT FORMAT for carousel.json:
{{
  "meta": {{ "date": "YYYY-MM-DD", "slot": "HHMM", "topic": "...", "hookFormula": "...", "structure": "...", "ctaWord": "WORD" }},
  "en": {{
    "slides": [ {{ "number": 1, "role": "hook", "theme": "dark", "headline": "...", "body": "...", "bgQuery": "..." }}, ... ],
    "caption": "..."
  }},
  "fr": {{ "slides": [...], "caption": "..." }},
  "es": {{ "slides": [...], "caption": "..." }},
  "x": {{
    "slides": [ {{ "number": 1, "role": "HOOK", "theme": "dark", "headline": "...", "body": "...", "bgQuery": "..." }}, ... (4 slides) ],
    "caption": "...",
    "ctaWord": "WORD"
  }}
}}
"""

TRANSLATION_NOTES = {
    "fr": "Write natural conversational French as a francophone content creator would. "
          "Do NOT translate literally. Rewrite idioms as French equivalents. "
          "Ask yourself: 'Would a native French speaker say this naturally?' If not, rewrite.",
    "es": "Write natural conversational Spanish as a hispanophone content creator would. "
          "Do NOT translate literally. Rewrite idioms as Spanish equivalents. "
          "Ask yourself: 'Would a native Spanish speaker say this naturally?' If not, rewrite.",
}


# ── Validation ────────────────────────────────────────────────────────────────

def validate_carousel(obj: dict, slot: str) -> list[str]:
    errors = []

    if "en" not in obj and "slides" not in obj:
        errors.append("missing 'en' key (or flat 'slides')")
        return errors

    lang_data = obj.get("en", obj)
    slides = lang_data.get("slides", [])

    if len(slides) not in (9, 10):
        errors.append(f"expected 9 slides, got {len(slides)}")

    for i, slide in enumerate(slides, 1):
        for field in ("number", "role", "theme", "headline"):
            if field not in slide:
                errors.append(f"slide {i} missing '{field}'")
        if slide.get("theme") not in ("dark", "light"):
            errors.append(f"slide {i} invalid theme: {slide.get('theme')}")
        if not slide.get("bgQuery"):
            errors.append(f"slide {i} missing bgQuery")

    caption = lang_data.get("caption", "")
    if not caption:
        errors.append("missing caption")
    if "--" in caption or "\u2014" in caption:
        errors.append("caption contains em-dash")

    # Validate X synthesis if present
    x = obj.get("x", {})
    if x:
        x_slides = x.get("slides", [])
        if len(x_slides) != 4:
            errors.append(f"x synthesis: expected 4 slides, got {len(x_slides)}")

    return errors


# ── Save carousel ─────────────────────────────────────────────────────────────

def _build_lang_block(data: dict, lang: str, date_str: str, slot: str) -> dict:
    return {
        "meta": {
            "date":        date_str,
            "slot":        slot,
            "lang":        lang,
            "structure":   data.get("meta", {}).get("structure", ""),
            "hookFormula": data.get("meta", {}).get("hookFormula", ""),
            "style":       data.get("meta", {}).get("style", "Sharp Analytical"),
            "topic":       data.get("meta", {}).get("topic", ""),
            "ctaWord":     data.get("meta", {}).get("ctaWord", ""),
        },
        "slides":  data.get("slides", []),
        "caption": data.get("caption", ""),
    }


def save_carousel(carousel_en: dict, target_date: date, slot: str,
                  translations: dict | None = None,
                  x_synthesis: dict | None = None):
    """
    Save carousel.json in multilang format.
    translations: {"fr": {...}, "es": {...}}
    x_synthesis:  {"slides": [...4 slides...], "caption": "...", "ctaWord": "..."}
    """
    date_str = target_date.isoformat()
    slot_dir = ROOT / "posts" / date_str / slot
    slot_dir.mkdir(parents=True, exist_ok=True)

    output = {"en": _build_lang_block(carousel_en, "en", date_str, slot)}
    for lang, data in (translations or {}).items():
        if data:
            output[lang] = _build_lang_block(data, lang, date_str, slot)
    if x_synthesis:
        output["x"] = x_synthesis  # already in final format

    out_path = slot_dir / "carousel.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_path


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Validate carousel.json files for a given date.",
    )
    parser.add_argument("--date", default=None, help="Target date YYYY-MM-DD (default: today)")
    parser.add_argument("--validate", action="store_true", help="Validate all carousel.json files")
    parser.add_argument("--status", action="store_true", help="Show which slots have content")
    args = parser.parse_args()

    target_date = date.fromisoformat(args.date) if args.date else date.today()
    date_str = target_date.isoformat()
    posts_dir = ROOT / "posts" / date_str

    print(f"\n{'='*60}")
    print(f"CONTENT STATUS  |  {date_str}")
    print(f"{'='*60}")

    if not posts_dir.exists():
        print(f"  No posts directory for {date_str}")
        sys.exit(0)

    all_ok = True
    for slot in SLOTS:
        carousel_path = posts_dir / slot / "carousel.json"
        if not carousel_path.exists():
            print(f"  [{slot}] MISSING carousel.json")
            all_ok = False
            continue

        carousel = json.loads(carousel_path.read_text(encoding="utf-8"))
        langs = [k for k in ("en", "fr", "es", "x") if k in carousel]
        has_x = "x" in carousel

        if args.validate:
            errs = validate_carousel(carousel, slot)
            status = "OK" if not errs else f"ERRORS: {'; '.join(errs)}"
            print(f"  [{slot}] langs={langs}  x={has_x}  {status}")
            if errs:
                all_ok = False
        else:
            print(f"  [{slot}] langs={langs}  x={has_x}")

    print(f"{'='*60}\n")
    if not all_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
