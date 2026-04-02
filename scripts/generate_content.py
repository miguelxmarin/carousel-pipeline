"""
generate_content.py
-------------------
Uses the OpenAI API to generate all 10 carousel JSON files for a given date
using The Carousel Method. Reads optional research input to inform topics.

Usage:
  python scripts/generate_content.py --date 2026-03-27
  python scripts/generate_content.py              # defaults to today
"""

import argparse
import json
import os
import sys
import time
from datetime import date, datetime
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("ERROR: openai package not installed. Run: pip install openai")
    sys.exit(1)

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
ROOT       = SCRIPT_DIR.parent
CONFIG_PATH = ROOT / "config.json"

with open(CONFIG_PATH, encoding="utf-8") as f:
    CONFIG = json.load(f)

# ── OpenAI key resolution ──────────────────────────────────────────────────────
def _resolve_openai_key() -> str:
    # Check nested path first: config.openai.apiKey
    nested = CONFIG.get("openai", {}).get("apiKey", "")
    if nested:
        return nested
    # Fall back to top-level field
    top_level = CONFIG.get("openaiApiKey", "") or CONFIG.get("openai_api_key", "")
    if top_level:
        return top_level
    # Last resort: environment variable
    env_key = os.environ.get("OPENAI_API_KEY", "")
    if env_key:
        return env_key
    print("ERROR: OpenAI API key not found. Add 'openai.apiKey' to config.json "
          "or set OPENAI_API_KEY environment variable.")
    sys.exit(1)

OPENAI_API_KEY = _resolve_openai_key()
client = OpenAI(api_key=OPENAI_API_KEY)

# ── Constants ─────────────────────────────────────────────────────────────────
CREATOR  = CONFIG["creator"]
POSTING  = CONFIG["posting"]

SLOTS = ["0600", "0730", "0900", "1100", "1300", "1600", "1800", "1930", "2100", "2230"]
TIMES = ["06:00", "07:30", "09:00", "11:00", "13:00", "16:00", "18:00", "19:30", "21:00", "22:30"]

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
    "HOOK",
    "CREDIBILITY",
    "PROBLEM",
    "AGITATION",
    "INSIGHT",
    "PROOF",
    "METHOD",
    "LIFT",
    "LOOP",
    "CTA",
]

# ── System prompt ─────────────────────────────────────────────────────────────

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

3. SLIDE ROLES (exactly 10 slides in this order):
   1. HOOK
   2. CREDIBILITY
   3. PROBLEM
   4. AGITATION
   5. INSIGHT
   6. PROOF
   7. METHOD
   8. LIFT
   9. LOOP
   10. CTA

4. THEME ALTERNATION:
   - Odd slides (1, 3, 5, 7, 9): theme = "dark"
   - Even slides (2, 4, 6, 8, 10): theme = "light"

5. HOOK RULES (slide 1):
   - Start from FEELING not topic.
   - NEVER use news-reporting style (e.g., never start with "Recently..." or "X just released...").
   - Hook must create immediate tension or curiosity.
   - Match exactly one of the 5 hook formulas above.

6. LANGUAGE RULES:
   - NO em-dashes anywhere. Not in headlines, not in body, not in captions.
   - NO contractions anywhere (write "do not" not "don't", "it is" not "it's", etc.).
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
   - Exactly 5 relevant hashtags (one line, space-separated)

8. CTA WORD: choose a single memorable uppercase word related to the topic.

9. TOPIC DIVERSITY: Each carousel slot must cover a distinctly different angle of the niche.
   Do not repeat topics across the 10 slots.

OUTPUT FORMAT:
Return a valid JSON array of 10 carousel objects. Each object:
{{
  "slot": "HHMM",
  "meta": {{
    "topic": "one-sentence topic description",
    "structure": "one of the 5 structures",
    "hookFormula": "snake_case formula key",
    "style": "Sharp Analytical",
    "ctaWord": "UPPERCASE_WORD"
  }},
  "slides": [
    {{
      "number": 1,
      "role": "HOOK",
      "theme": "dark",
      "headline": "...",
      "body": "..."
    }},
    ... (10 slides total)
  ],
  "caption": "full caption text"
}}

hookFormula keys: everyone_wrong, years_taught, nobody_talks, stop_start, not_problem_reframe

Return ONLY the JSON array. No markdown. No explanation. No code fences.
"""

USER_PROMPT_TEMPLATE = """Generate 10 carousels for {date_str} using The Carousel Method.

POSTING SLOTS AND TIMES:
{slots_info}

RESEARCH CONTEXT (use these signals to inform topics and hooks):
{research_context}

REQUIREMENTS:
- Each carousel covers a different topic angle within the niche
- Topics should range across: AI tools, productivity, building apps, making money with AI, career shifts, mindset, specific tool tutorials, case studies
- Slot 06:00 gets the strongest hook (largest morning audience)
- Slot 13:00 and 18:00 are peak engagement slots (use bold hooks)
- Return exactly 10 carousel objects in a JSON array, ordered by slot
- No em-dashes. No contractions. Hooks start from feeling, not topic.
"""

# ── Research loader ────────────────────────────────────────────────────────────

def load_research(target_date: date) -> str:
    date_str = target_date.isoformat()

    # Primary: dated research file
    dated_path = ROOT / "research" / f"{date_str}.json"
    if dated_path.exists():
        try:
            data = json.loads(dated_path.read_text(encoding="utf-8"))
            return _format_research(data)
        except Exception as e:
            print(f"  [WARN] Could not parse {dated_path}: {e}")

    # Fallback: root research-sweep.json (from research-sweep.js)
    sweep_path = ROOT / "research-sweep.json"
    if sweep_path.exists():
        try:
            data = json.loads(sweep_path.read_text(encoding="utf-8"))
            return _format_research(data)
        except Exception as e:
            print(f"  [WARN] Could not parse {sweep_path}: {e}")

    return "No research data available. Generate topics from creator niche and current AI trends."


def _format_research(data: dict) -> str:
    parts = []

    hook_angles = data.get("hookAngles", [])
    if hook_angles:
        parts.append("TOP HOOK ANGLES:")
        for i, angle in enumerate(hook_angles[:6], 1):
            a = angle.get("angle", "")
            direction = angle.get("hookDirection", "")
            parts.append(f"  {i}. {a}")
            if direction:
                parts.append(f"     Direction: {direction}")

    friction = data.get("signals", {}).get("friction", [])
    if friction:
        parts.append("\nAUDIENCE FRICTION SIGNALS (real audience language):")
        for item in friction[:8]:
            text = item.get("text", "") if isinstance(item, dict) else str(item)
            if text:
                parts.append(f"  - {text[:120]}")

    aspiration = data.get("signals", {}).get("aspiration", [])
    if aspiration:
        parts.append("\nASPIRATION SIGNALS (what worked for them):")
        for item in aspiration[:5]:
            text = item.get("text", "") if isinstance(item, dict) else str(item)
            if text:
                parts.append(f"  - {text[:120]}")

    raw_phrases = data.get("signals", {}).get("rawPhrases", [])
    if raw_phrases:
        parts.append("\nRAW AUDIENCE PHRASES (verbatim hook material):")
        for item in raw_phrases[:5]:
            phrase = item.get("phrase", "") if isinstance(item, dict) else str(item)
            if phrase:
                parts.append(f"  - \"{phrase[:100]}\"")

    if not parts:
        return "Research data present but no structured signals found. Use current AI trends."

    return "\n".join(parts)


# ── OpenAI call ────────────────────────────────────────────────────────────────

def generate_carousels(target_date: date, research_context: str) -> list[dict]:
    date_str = target_date.isoformat()

    slots_info_lines = []
    for slot, time_str in zip(SLOTS, TIMES):
        slots_info_lines.append(f"  {slot} -> {time_str}")
    slots_info = "\n".join(slots_info_lines)

    user_prompt = USER_PROMPT_TEMPLATE.format(
        date_str=date_str,
        slots_info=slots_info,
        research_context=research_context,
    )

    print("  Calling OpenAI API (this may take 30-90 seconds)...")
    t0 = time.time()

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=0.8,
        max_tokens=8000,
        response_format={"type": "json_object"},
    )

    elapsed = time.time() - t0
    print(f"  API responded in {elapsed:.1f}s")

    raw = response.choices[0].message.content.strip()

    # The response_format json_object may wrap in an object; unwrap if needed
    parsed = json.loads(raw)
    if isinstance(parsed, list):
        return parsed
    # Look for the array inside a wrapper object
    for key in parsed:
        if isinstance(parsed[key], list):
            return parsed[key]

    raise ValueError(f"Unexpected JSON shape from API. Keys: {list(parsed.keys())}")


# ── Validation ────────────────────────────────────────────────────────────────

def validate_carousel(obj: dict, slot: str) -> list[str]:
    errors = []

    if "meta" not in obj:
        errors.append("missing 'meta'")
    if "slides" not in obj:
        errors.append("missing 'slides'")
        return errors
    if "caption" not in obj:
        errors.append("missing 'caption'")

    slides = obj["slides"]
    if len(slides) != 10:
        errors.append(f"expected 10 slides, got {len(slides)}")

    for i, slide in enumerate(slides, 1):
        for field in ("number", "role", "theme", "headline", "body"):
            if field not in slide:
                errors.append(f"slide {i} missing '{field}'")
        if slide.get("theme") not in ("dark", "light"):
            errors.append(f"slide {i} invalid theme: {slide.get('theme')}")

    caption = obj.get("caption", "")
    if "--" in caption or "\u2014" in caption:
        errors.append("caption contains em-dash")

    return errors


# ── Save carousels ────────────────────────────────────────────────────────────

def save_carousel(carousel_data: dict, target_date: date, slot: str):
    date_str = target_date.isoformat()
    slot_dir = ROOT / "posts" / date_str / slot
    slot_dir.mkdir(parents=True, exist_ok=True)

    # Build the canonical carousel.json structure
    output = {
        "meta": {
            "date":        date_str,
            "slot":        slot,
            "structure":   carousel_data.get("meta", {}).get("structure", ""),
            "hookFormula": carousel_data.get("meta", {}).get("hookFormula", ""),
            "style":       carousel_data.get("meta", {}).get("style", "Sharp Analytical"),
            "topic":       carousel_data.get("meta", {}).get("topic", ""),
            "ctaWord":     carousel_data.get("meta", {}).get("ctaWord", ""),
        },
        "slides":  carousel_data["slides"],
        "caption": carousel_data.get("caption", ""),
    }

    out_path = slot_dir / "carousel.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_path


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate 10 carousel JSON files using The Carousel Method."
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Target date in YYYY-MM-DD format (default: today)",
    )
    parser.add_argument(
        "--retry",
        action="store_true",
        help="Retry generation even if carousel.json files already exist",
    )
    args = parser.parse_args()

    target_date = date.fromisoformat(args.date) if args.date else date.today()
    date_str = target_date.isoformat()

    print(f"\n{'='*60}")
    print(f"GENERATE CONTENT  |  {date_str}")
    print(f"{'='*60}")

    # Check if already generated
    posts_dir = ROOT / "posts" / date_str
    existing_slots = []
    if posts_dir.exists():
        for slot in SLOTS:
            if (posts_dir / slot / "carousel.json").exists():
                existing_slots.append(slot)

    if existing_slots and not args.retry:
        print(f"  Found existing carousel.json for {len(existing_slots)}/10 slots.")
        if len(existing_slots) == 10:
            print("  All 10 carousels already exist. Use --retry to regenerate.")
            return
        print(f"  Missing slots: {[s for s in SLOTS if s not in existing_slots]}")

    # Load research
    print("\n  Loading research data...")
    research_context = load_research(target_date)
    research_lines = research_context.count("\n") + 1
    print(f"  Research context: {research_lines} lines loaded.")

    # Generate
    print("\n  Generating 10 carousels via OpenAI GPT-4o...")
    try:
        carousels = generate_carousels(target_date, research_context)
    except Exception as e:
        print(f"\nERROR generating carousels: {e}")
        sys.exit(1)

    if len(carousels) != 10:
        print(f"  [WARN] API returned {len(carousels)} carousels instead of 10.")

    # Map by slot position
    slot_order = {slot: i for i, slot in enumerate(SLOTS)}

    # Try to match returned carousels to slots
    # API should return them in order; use index as fallback
    saved = []
    errors_total = []

    for idx, carousel in enumerate(carousels):
        # Determine slot
        returned_slot = str(carousel.get("slot", "")).replace(":", "")
        if returned_slot in SLOTS:
            slot = returned_slot
        elif idx < len(SLOTS):
            slot = SLOTS[idx]
            print(f"  [WARN] Carousel {idx+1} had slot '{carousel.get('slot')}', "
                  f"mapping to {slot}")
        else:
            print(f"  [WARN] No slot mapping for carousel {idx+1}, skipping.")
            continue

        # Skip if already exists and not retrying
        if slot in existing_slots and not args.retry:
            print(f"  [SKIP] {slot} already exists.")
            continue

        # Validate
        errs = validate_carousel(carousel, slot)
        if errs:
            print(f"  [WARN] {slot} validation issues: {'; '.join(errs)}")
            errors_total.extend([f"{slot}: {e}" for e in errs])

        # Save
        try:
            out_path = save_carousel(carousel, target_date, slot)
            topic = carousel.get("meta", {}).get("topic", "")[:55]
            hook_line = carousel.get("slides", [{}])[0].get("headline", "")[:50]
            print(f"  [OK] {slot}  |  {hook_line}")
            saved.append(slot)
        except Exception as e:
            print(f"  [ERR] {slot} failed to save: {e}")
            errors_total.append(f"{slot}: save error: {e}")

    print(f"\n{'='*60}")
    print(f"  Saved {len(saved)}/10 carousel files.")
    if errors_total:
        print(f"  Warnings/errors ({len(errors_total)}):")
        for err in errors_total:
            print(f"    - {err}")
    print(f"  Output: posts/{date_str}/HHMM/carousel.json")
    print(f"{'='*60}\n")

    if len(saved) == 0 and len(carousels) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
