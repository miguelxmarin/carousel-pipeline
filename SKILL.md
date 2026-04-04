---
name: carousel-pipeline
description: >
  Automated viral carousel content pipeline for personal brand creators.
  Stack: Claude Code (content brain) + Pinterest via Chrome (photography) + PostFast (scheduling).
  Generates carousel posts using The Carousel Method, real Pinterest photography,
  smart per-slide text overlays via Pillow, posts to TikTok/Instagram/LinkedIn/X via PostFast.
  Builds a PDF resource for every carousel CTA. Runs a self-improving analytics feedback loop.
  Multilingual: FR first, then EN (+60 min), then ES (+120 min) on TikTok and Instagram.
  LinkedIn and X post EN only. 2 slots/day × 8 platform-language combos = 16 publications/day.
  Use whenever a creator wants to automate social content, generate viral carousels,
  grow on TikTok or Instagram, or build a hands-free content machine.
  Trigger on: automate content, carousel posts, TikTok growth, Instagram reach,
  viral content, content pipeline, personal brand automation, build resource, PDF resource,
  analytics feedback loop, hook performance, learned rules.
---

# Carousel Pipeline -- White-Label Automated Content Machine

You are the content brain of this pipeline. You are not executing scripts.
You are applying the system below to generate content that consistently performs.
The scripts handle infrastructure. You handle intelligence.

---

## WHAT THIS SYSTEM DOES

This is a **daily automated content machine** for TikTok, Instagram, LinkedIn, and X carousels.

**The full stack — nothing else:**
- **Claude Code** — content brain (research, write carousel.json, X synthesis, FR/ES translation)
- **Pinterest** (Chrome browser) — real photography, one photo per slide
- **PostFast** — scheduling to all platforms via API

Every day it:
1. **Researches** fresh audience friction + trending AI topics via WebSearch
2. **Writes** 2 carousel posts (EN + FR + ES + X synthesis) using The Carousel Method — Claude Code writes carousel.json directly, no external AI API
3. **Builds** a branded PDF resource for every post's CTA ("Comment WORD — I'll send you the PDF")
4. **Fetches** real photography from Pinterest (9 photos per slot via Chrome browsing + `fetch_backgrounds.py`)
5. **Generates** slides with smart text overlays via Pillow (`generate_slides_py.py --lang en/fr/es/x`)
6. **Schedules** 16 posts/day via PostFast: FR first at slot time → EN +60 min → ES +120 min (TikTok + Instagram); LinkedIn EN only; X EN 4-slide synthesis
7. **Measures** performance via PostFast analytics
8. **Learns** which hooks, structures, and CTA words work — feeds rules back into tomorrow's content

**Output per day:**
- 2 topics × (TikTok FR+EN+ES + Instagram FR+EN+ES + LinkedIn EN + X EN) = **16 publications/day**
- Each with a PDF resource, all scheduled automatically

---

## WHO THIS IS FOR

**Any personal brand creator** in a high-value niche — finance, fitness, productivity, AI, business, tech — who posts carousel content on TikTok and Instagram and wants to systematize production.

**To set up for a new creator:**
Edit `config.json` — set creator profile, PostFast API key + account IDs, posting times and timezone.

**Platform routing:**
- TikTok + Instagram: FR first (slot time) → EN (+60 min) → ES (+120 min)
- LinkedIn: EN only (at slot time)
- X: EN only (4-slide original synthesis, at slot time)

**Posting offsets are in `config.json → postfast.languages.{lang}.offsetMinutes`.**

---

## IS IT FULLY AUTOMATIC?

**Partially.** Here is what is automated vs. what requires human input:

| Step | Automated? | Notes |
|------|-----------|-------|
| Research (2 topics/day) | YES | Claude uses WebSearch — no external API needed |
| Content writing | YES | Claude Code writes `carousel.json` directly in the conversation — EN + FR + ES + X synthesis |
| PDF resource build | YES | `build_resource.py` renders `resource.json` → `resource.pdf` per slot |
| Pinterest background fetch | SEMI | Claude browses Pinterest via Chrome browser extension, picks 9 photos/slot — `fetch_backgrounds.py` downloads them |
| Slide rendering | YES | `generate_slides_py.py` — Pillow overlays text on Pinterest photos (runs per lang: en, fr, es, x) |
| Google Drive PDF upload | YES | `upload_to_drive.py` — uploads resource.pdf, sets "Anyone with the link" sharing, saves link to carousel.json. One-time OAuth setup (~3 min). |
| Posting to all platforms | YES | `post_to_postfast.py` — PostFast API handles TikTok, Instagram, LinkedIn, X with correct offsets |
| Analytics pull | YES | `analytics_pull.py` — PostFast `/social-posts/analytics` |
| Feedback loop | YES | `hook-performance.json` auto-updates with learned rules for next day |
| Daily scheduling | YES | Claude scheduled task runs at 5:00 AM every day — fully hands-free |

---

## HOW TO RUN

```bash
# ── DAILY FLOW ──────────────────────────────────────────────────────────────

# Step 1 — Research (Claude WebSearch → research/YYYY-MM-DD.json)
python scripts/research_sweep.py --date YYYY-MM-DD

# Step 2 — Content (Claude Code writes carousel.json directly in this conversation)
#   Claude reads research, writes EN carousel + FR/ES translations + X synthesis
#   Output: posts/YYYY-MM-DD/0730/carousel.json  +  posts/YYYY-MM-DD/1300/carousel.json
#   Validate after writing:
python scripts/generate_content.py --date YYYY-MM-DD --validate

# Step 3 — Pinterest backgrounds (Claude opens Chrome, searches each bgQuery)
#   See what to search:
python scripts/fetch_backgrounds.py --slot-dir posts/YYYY-MM-DD/HHMM --list
python scripts/fetch_backgrounds.py --slot-dir posts/YYYY-MM-DD/HHMM --list --lang x
#   Save each image Claude finds:
python scripts/fetch_backgrounds.py --slot-dir posts/YYYY-MM-DD/HHMM --slide N --url https://i.pinimg.com/...
python scripts/fetch_backgrounds.py --slot-dir posts/YYYY-MM-DD/HHMM --slide N --url https://i.pinimg.com/... --lang x
#   Or save all at once from a JSON map:
python scripts/fetch_backgrounds.py --slot-dir posts/YYYY-MM-DD/HHMM --map '{"1":"https://...","2":"https://..."}'

# Step 4 — Generate slides (Pillow text overlays, one lang at a time)
python scripts/generate_slides_py.py posts/YYYY-MM-DD/HHMM --lang en
python scripts/generate_slides_py.py posts/YYYY-MM-DD/HHMM --lang fr
python scripts/generate_slides_py.py posts/YYYY-MM-DD/HHMM --lang es
python scripts/generate_slides_py.py posts/YYYY-MM-DD/HHMM --lang x

# Step 5 — Build PDF resource
python scripts/build_resource.py --slot-dir posts/YYYY-MM-DD/HHMM

# Step 5b — Upload PDF to Google Drive (get shareable link)
python scripts/upload_to_drive.py --slot-dir posts/YYYY-MM-DD/HHMM

# Step 6 — Post (all langs, scheduled — FR first, EN +60min, ES +120min)
python scripts/post_to_postfast.py --date YYYY-MM-DD --lang fr
python scripts/post_to_postfast.py --date YYYY-MM-DD --lang en
python scripts/post_to_postfast.py --date YYYY-MM-DD --lang es

# ── SHORTCUTS ───────────────────────────────────────────────────────────────

# Full pipeline run (steps 1-6 in one command)
python scripts/daily_run.py --date YYYY-MM-DD

# Dry run (everything except actual posting)
python scripts/daily_run.py --date YYYY-MM-DD --dry-run

# Skip research (content already written)
python scripts/daily_run.py --date YYYY-MM-DD --skip-research

# Skip slide generation (slides already exist)
python scripts/daily_run.py --date YYYY-MM-DD --skip-images

# Post one slot immediately (right now, no scheduling)
python scripts/post_to_postfast.py --slot 0730 --now --lang fr

# Post one specific slot for one language
python scripts/post_to_postfast.py --date YYYY-MM-DD --slot 0730 --lang en

# Pull analytics
python scripts/analytics_pull.py

# TESTING RULE: When asked to test the pipeline, use ONE slot only.
# One slot is enough to verify the full pipeline end to end.
```

---

## THE PIPELINE FLOW

```
research_sweep.py (WebSearch — audience friction + trending AI topics)
    → read hook-performance.json (learned rules from past posts)
        → Claude Code writes carousel.json (EN + FR + ES + X synthesis, 2 slots)
            → generate_content.py --validate (confirm structure is correct)
                → fetch_backgrounds.py --list (show bgQuery for each slide)
                    → Claude opens Pinterest in Chrome, finds best photo per slide
                        → fetch_backgrounds.py --slide N --url URL (download + crop)
                            → generate_slides_py.py --lang en/fr/es/x (Pillow overlays)
                                → build_resource.py (resource.json → resource.pdf)
                                    → upload_to_drive.py (upload PDF → shareable Drive link → saved to carousel.json)
                                        → post_to_postfast.py --lang fr (FR first at slot time)
                                    → post_to_postfast.py --lang en (EN +60 min)
                                    → post_to_postfast.py --lang es (ES +120 min)
                                        → analytics_pull.py (PostFast metrics)
                                            → update hook-performance.json
                                                → learned rules feed into tomorrow's session
```

**Platform schedule per slot:**
```
Slot time (e.g. 07:30)  →  TikTok FR + Instagram FR + LinkedIn EN + X EN
Slot time + 60 min      →  TikTok EN + Instagram EN
Slot time + 120 min     →  TikTok ES + Instagram ES
```
**Total: 2 slots × 8 publications = 16 posts/day**

**Three intelligence inputs feed every carousel:**
1. `research/YYYY-MM-DD.json` -- what the audience is saying right now
2. `hook-performance.json` -- what your posts have proven works (or not)
3. `config.json` -- creator niche, audience, voice, posting schedule

---

## BEFORE WRITING -- READ THE LEARNED RULES

Always read `hook-performance.json` before writing content for a new date.
The `learnedRules` array tells you exactly what to do differently.

**Current performance state (as of last analytics pull):**
- 18 posts tracked (all 2026-03-27), 16 with metrics
- Account baseline: 73 avg views, 0.00% save rate
- TikTok significantly outperforms Instagram (236-263 views vs 1-14)
- Best slot: 13:00 (263 TikTok views, 12 likes)
- Best CTA word so far: VALIDATE (71.9x more comments than SKILLS)
- All hook formulas currently below 1K threshold (early stage, account cold)

**What this means for content:**
- Optimize for TikTok first -- that is where the audience is landing
- Prioritize the 13:00 slot with your strongest hook
- Use VALIDATE or high-action CTA words over passive ones (SKILLS, SYSTEM)
- Save rate = 0% across the board -- slides 5-7 need stronger value delivery
- The limiting_belief formula (121 avg views) outperforms others by 2.5x -- lean on it

---

## RENDERER DESIGN RULES -- NEVER BREAK THESE

These rules live in `generate_slides_py.py` and were learned through real production.
Do not override them in content decisions. The renderer enforces them.

**Slide alternation:**
- Odd slides (1, 3, 5, 7, 9) = DARK (62% black overlay)
- Even slides (2, 4, 6, 8)   = LIGHT (65% cream overlay)
- Enforced by slide number, not by the `theme` field in JSON.

**Hook slide (slide 1) — special rules:**
- Gradient fade: photo bleeds into black starting at 38% height, fully black by 72%.
  No hard cut. No separator line.
- Headline: Anton font, centered on full 1080px width (not the 939px safe zone).
  Auto-sizes 112 → 96 → 84 → 74 → 64px until ≤ 2 lines.
- Last 2 words of last headline line are ALWAYS gold — no exceptions on hooks.
  This creates a 2-word CTA phrase ("FAIT PAYER", "GETS PAID", "MAKES MONEY").
- No slide counter (no "1/9") on the hook slide.
- Brand mark (@handle) centered below fade zone.
- "SWIPE FOR MORE ›" pill: transparent fill, white border, white text, centered, bottom.

**Gold text rendering — the stroke rule:**
- Dark slides: plain gold `(255, 252, 0)` — naturally crisp (high contrast vs black).
- Light slides: ALWAYS add 1px dark stroke before gold.
  Reason: gold and cream are both high-luminance. Anti-aliased edges between them
  produce a blurry, smeared appearance. The dark stroke defines glyph boundaries.
  Implementation: draw text at 8 offsets `(±1, ±1)` in `(25, 25, 25)` first, then gold on top.
- The stroke is invisible on dark slides (black on black), so this logic is always safe to apply.

**Non-hook gold logic:**
- Respect ALL CAPS marker in headline first (author intent).
- Fall back to last word of last line if no ALL CAPS word found.
- Never gold more than one word on non-hook slides.

**Text placement:**
- `TEXT_X = PAD` (left-aligned) for all non-hook slides.
- Right edge dead zone: last 13% of frame — platform UI buttons live there.
- Text block must fit above `H - 140px` footer reserve.

**Google Drive (API-based — fully automated):**

Uses Google Drive API v3 with OAuth2. No browser interaction required after one-time setup.

**One-time setup (~3 minutes):**
1. Go to https://console.cloud.google.com
2. Create a project → Enable the **Google Drive API**
   (APIs & Services → Library → search "Google Drive API" → Enable)
3. Create OAuth credentials:
   APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID → Desktop app → Download JSON
4. Save the downloaded file as: `credentials/google_oauth_credentials.json`
5. Run once: `python scripts/upload_to_drive.py --slot-dir posts/YYYY-MM-DD/HHMM`
   Browser opens → sign in → click Allow → `credentials/token.json` saved → done forever

**What it does automatically (every run after setup):**
1. Finds or creates root folder: `CLAUDE AGENT CAROUSEL PDFS`
2. Finds or creates subfolder: `YYYY-MM-DD -- topic-slug [CTAWORD]`
3. Uploads `resource.pdf`
4. Sets sharing to **"Anyone with the link — Viewer"** (no Google account needed to view or download)
5. Saves the shareable link to `carousel.json` under `meta.resourceLink`

**Sharing rule (non-negotiable):**
The link MUST be set to "Anyone with the link -- Viewer".
This ensures it can be sent to anyone (DM, comment reply, email) without requiring a Google login.

**After upload — always output the link for easy copy-paste:**
```
Resource PDF link (copy-paste ready):
https://drive.google.com/file/d/FILE_ID/view?usp=sharing
```

**Security:**
`credentials/google_oauth_credentials.json` and `credentials/token.json` are gitignored.
Never commit them. Never share them. The `credentials/.gitignore` excludes all `*.json`.

---

## THE AUDIENCE

People who want to use AI to build cool things and make money online.
Any industry. Any skill level. Side hustlers testing their first AI tool
to entrepreneurs scaling with automation.

What they share: they want to feel smarter every time they see the content.
They want an edge -- not theory, not hype, but real insight they can act on today.

**The Content Promise:**
Every piece of content makes the reader feel like they know something most people do not.
It connects to money -- either making it, saving it, or understanding how others are making it with AI.
Always practical. Always current. Always honest about what works and what does not.

---

## DAILY RESEARCH STANDARD

The goal is NOT to find news. The goal is to find evidence of friction and aspiration
in the audience right now -- specifically around using AI to make money, build things,
and get smarter.

**What to look for:**
- What is the audience already doing with AI that is not working?
- What AI opportunity are they aware of but have not acted on?
- What would make their next step toward making money with AI easier right now?
- Where is the gap between what AI promised them and what they actually got?

**NOT looking for:** announcements, product launches, benchmark scores, funding rounds,
or anything that requires the audience to care about something new.
The topic is always the vehicle. The feeling is always the hook.

**The 3-Question Research Filter -- every topic must pass all three:**
1. Does this connect to something the audience is already feeling -- not something we need to convince them to care about?
2. Can we turn this into a micro-improvement they feel immediately -- something that makes their next step toward making money or building with AI clearer or easier today?
3. Do we have a resource we can build that delivers on the promise of the carousel?

If it fails any one of these -- discard it. Go back to the sweep.

**Decision criteria before writing:**
- Does it feel true to what the audience is seeing and experiencing right now?
- Is the resource something worth genuinely sending to someone you respect?
- Does it connect to making money, building things, or getting smarter with AI?
- Does it fit where the audience is emotionally this week -- not just intellectually?
- Is it different from what was posted recently?

There are no fixed content territories. Find the best tensions from research each day.
The audience's reality sets the agenda -- not a predefined list of categories.

---

## RESOURCE FIRST -- THE MOST IMPORTANT RULE

**Build the resource before the carousel. Always.**

The carousel is a promise. The resource has to deliver on it.
If there is no resource that genuinely fixes the problem -- do not write the carousel.
The CTA is only as powerful as what it leads to.

**What a resource is:**
A tight, useful PDF that a person can open, read in under 10 minutes, and use today.
Built entirely from research. Not opinions. The best of what exists -- curated, filtered,
packaged with clarity.

**What a resource is NOT:**
- A news article link
- A product page
- A long-form essay
- A list of tools without context
- Anything that requires more than 10 minutes to get value from

**Resource formats (choose based on the micro-reward promised):**
- **The 3-tool stack guide** -- Tool name, what it does, when to use it, one concrete example. How the three connect.
- **The before/after workflow** -- Old process vs new process. Exactly what changes. Time or money saved.
- **The curated collection** -- Best examples, posts, or case studies around one theme. Organized by what they teach, not by source.
- **The swipe file** -- Copy-paste prompts, templates, or frameworks the person uses immediately.
- **The one-pager** -- One idea, explained fully, with one actionable next step.
- **The money map** -- Visual breakdown of an income model: cost, earnings, time, tools needed.

**How Claude builds the resource:**
1. Uses the research already gathered for the day
2. Finds the most useful, concrete, specific information on the topic
3. Structures it around the micro-reward promised in the carousel exactly -- delivers what the carousel hinted at
4. Writes in plain language: no jargon, no fluff, no padding
5. Saves it as `resource.json` in the slot directory -- `build_resource.py` renders it to PDF
6. Miguel reviews, approves, adds his own experience and perspective

**Resource JSON format (`resource.json`):**
```json
{
  "meta": {
    "slot": "0600",
    "date": "YYYY-MM-DD",
    "title": "Resource title",
    "format": "swipe_file | three_tool_stack | before_after | curated_collection | one_pager | money_map",
    "ctaWord": "CONTEXT",
    "language": "en"
  },
  "sections": [
    {
      "heading": "Section heading",
      "body": "Section body text. Plain language. No fluff.",
      "items": ["Item 1", "Item 2"]
    }
  ],
  "footer": "Drop a comment with CONTEXT on the post and I will send this to you."
}
```

---

## THE CAROUSEL METHOD -- Content Operating Manual

### THE CORE TRUTH

Carousels do not go viral because they look good.
They go viral because people cannot stop swiping.
Retention drives the algorithm. Hooks get the click. Retention drives the reach.

---

### HOOK PRINCIPLES

A hook is not a trendy sentence. A hook is:
- A powerful interpretation of a problem
- An uncomfortable truth
- A sharp perspective shift
- A promise or spark that creates instant emotion

Its only goal: stop the scroll and pull the viewer into slide 2.

**The 4 P's Test -- a hook must score 3 of 4:**
1. Precision -- one clear idea, not vague
2. Problem -- visible or implied pain/friction
3. Polarity -- fresh angle, unexpected truth, not generic advice
4. Perspective Shift -- changes how the reader sees something

**Hook formulas:**
1. "Everyone [does X]. Nobody [does Y]."
2. "[X] years of [thing] taught me one thing:"
3. "The [topic] nobody talks about:"
4. "Stop [common action]. Start [better action]."
5. "You are not [problem]. You are [reframe]."
6. "[Common action] does not make you [result]."
7. "The micro-shift that [result]."

**Non-negotiables:**
- Never start from the topic. Always start from the feeling.
- "You are not overwhelmed. You are unstructured." -- this is a hook.
- "Tips for being more productive" -- this is not a hook.
- Zero context on slide 1. Pure impact. The rest is explained later.
- After writing any hook: ask "Does this make the reader think about THEMSELVES or about the NEWS?"
  If the answer is "the news" -- rewrite it.

---

### THE 9-SLIDE STRUCTURE

The format is fixed at 9 slides. Each slide has a defined role.
Do not add slides because there is more to say.
Do not cut slides because one feels thin.
If a slide feels weak, make it stronger -- do not collapse the structure.

```
Slide 1 -- HOOK          Open loop. Stop the scroll. One sharp line. Pure impact.
Slide 2 -- TENSION       Make the problem real. The audience nods. "Yes, that is exactly it."
Slide 3 -- SHIFT         Break expectations. Reframe the problem. New perspective.
Slide 4 -- PROOF         One insight only. Short sentences. Evidence of the shift.
Slide 5 -- MICRO-REWARD  First payoff. Something they can use today. Makes them feel smarter.
Slide 6 -- BUILD         Goes deeper. Extends the insight. Never reveals the full payoff yet.
Slide 7 -- EDGE          The thing nobody says. Makes them feel they have privileged knowledge.
Slide 8 -- CTA           "Drop a comment. [WORD]." Last word is WORD in ALL CAPS = gold.
Slide 9 -- CLOSER        Echo slide 1. Give it more power. The loop closes. The hook gains force.
```

**Slide alternation rule (hard rule, no exceptions):**
- Odd slides (1, 3, 5, 7, 9) = DARK background
- Even slides (2, 4, 6, 8) = LIGHT (cream) background
- This is enforced by the renderer from the slide number. Theme field in JSON is informational only.

**Slide 9 -- The Closer (critical):**
- Echo slide 1 exactly. Give it more power.
- Slide 1: "Your consistency problem is not what you think."
- Slide 9: "Now you know exactly what it is."
- People re-read slide 1 before saving/sharing. The loop reinforces the hook.

**Slide 8 -- The CTA (critical rules):**
- CTA slide headline: "Comment WORD." — exactly this format. One sentence.
- CTA slide body: "to [get/access/unlock] the [resource] that [does X for them]."
- Together they read as one sentence: "Comment VALIDATE to get the filter that stops AI theater."
- The CTA word stays ALL CAPS in the JSON. Gold rendering is automatic.
- Body must describe the BENEFIT to the person, not just what you will send.
  BAD: "I will send you the 5-question filter."
  GOOD: "to get the 5-question filter that stops AI theater before it starts."

---

### CONTENT RULES -- NON-NEGOTIABLE

**Every slide:**
- 1 idea per slide. No lists. No stacking multiple concepts.
- Headline: maximum 8 words.
- Body: maximum 2 lines, maximum 10 words total. That is it.
- Let curiosity work. Do not over-explain.
- The gold word is always the last word of the headline. Always the emotional peak.
- Never start from the topic. Always start from the feeling.
- No product names. No tool names. No platform names. No specific solutions.
  (The carousel is the promise. The resource is the delivery. Tools live in the resource.)

**Writing voice:**
- Write from the audience's wallet, not from a research paper.
- "I am spending $200/month and making nothing back." -- this is how they talk.
- "Cognitive overload" -- this is how papers talk. Never use it.
- The data supports the feeling. It never replaces it.
- No em-dashes ever. Use a period or comma instead.
- No contractions in body text. "It is" not "It's". "Do not" not "Don't".
- Fewer words done right beats more words done wrong.

**Caption formula:**
1. One sentence naming the problem in the audience's voice
2. One sentence naming the reframe or micro-reward
3. "Drop a comment. [WORD] and I will send you [specific resource]."
4. 5 hashtags, relevant to the specific topic -- not generic AI tags.
   3 hashtags in the post language, adapted for that audience's search behavior.
   Hashtags go at the bottom, after the CTA.

---

### MULTI-LANGUAGE -- PRODUCE ALL THREE VERSIONS

Once the carousel is approved in English, produce French and Spanish in the same session.
Each version is a native adaptation, not a translation.

- **English** -- Default. Global audience of people using AI to build and earn.
- **French** -- Natural, contemporary French. Not formal. Speaks to the audience as 'tu'.
- **Spanish** -- Neutral Spanish. Works for Spain and Latin America. Speaks to the audience as 'tu'.

If a line does not work in French, rewrite it. Do not force a translation.
The emotional arc must land in each language independently.

**carousel.json format for multi-language:**
```json
{
  "meta": { "date": "...", "slot": "...", "topic": "...", "hookFormula": "...", "ctaWord": "WORD" },
  "en": { "slides": [...], "caption": "..." },
  "fr": { "slides": [...], "caption": "..." },
  "es": { "slides": [...], "caption": "..." }
}
```

**Slides array format (each language):**
```json
{
  "slides": [
    {
      "number": 1,
      "role": "hook",
      "theme": "dark",
      "headline": "Last word is always the emotional PEAK.",
      "body": "Optional body. Max 2 lines, 10 words total.",
      "bgQuery": "fog blur unclear dark aesthetic"
    }
  ]
}
```

`bgQuery` is written by Claude at content time — 2-3 keywords that visually *are* the concept of that slide + dark/light + aesthetic.
The `bgQuery` lives on the EN slides only (since all languages share the same background image).

**Multi-language posting:** `post_to_postfast.py --lang en|fr|es`
- Languages with null account IDs in `config.postfast.languages` are silently skipped.
- FR and ES account IDs are placeholders -- add them in config.json when accounts are ready.

---

### THE RETENTION LOOP

Every slide must follow: **Curiosity -> Clarity -> Reward -> Next Curiosity**

Every slide must:
1. Answer something from the previous slide
2. Open something new that forces the next swipe

**The 7 Swipe Triggers:**
1. Curiosity Gap: Start slides with incomplete information. "Here is the part nobody mentions..."
2. The Not Yet Technique: Deliberately delay the answer 1-2 slides.
3. Micro-Dopamine Lines: Short lines that feel like mini-insights. "Read that again."
4. Pattern Interrupts: Sudden tone change. "Wait." "Let me be honest."
5. Emotional Anchors: Fear, Relief, Authority. "You might be doing this without knowing."
6. Slide 7 Edge: Re-engage anyone who slowed at slides 5-6. Privileged knowledge. Simple.
7. The Loop Effect: Slide 9 echoes slide 1. People re-read slide 1 before saving.

---

### THE 5 VIRAL STRUCTURES

**Choose structure FIRST, then select a compatible hook formula.**

**1. Myth to Truth** (best for: shares, reach)
Hook: shock/polarization or "everyone wrong"
Flow: Hook -> The myth -> What actually happens -> Why myth exists -> The truth ->
      Evidence -> What changes when you know this -> CTA -> Loop

**2. Here's Why You're Stuck** (best for: followers, comments, saves)
Hook: nobody_talks or clarity_eureka
Flow: Hook -> Symptom -> Misdiagnosis -> Root cause -> New insight ->
      Example -> Application -> CTA -> Loop

**3. Micro Lessons** (best for: saves, shares)
Hook: authority or "everyone wrong"
Flow: Hook -> Rule 1 -> Rule 2 -> Rule 3 -> Examples -> Reinforcement ->
      Micro-summary -> CTA -> Loop

**4. Before to After** (best for: followers, emotional connection)
Hook: clarity_eureka or limiting_belief
Flow: Hook -> BEFORE state -> Why it fails -> The shift -> AFTER state 1 ->
      AFTER state 2 -> Example -> CTA -> Loop

**5. Warning Sign** (best for: reach, virality, comments)
Hook: warning_hook or shock/polarization
Flow: Hook -> Sign 1 -> Why 1 harmful -> Sign 2 -> Why 2 harmful ->
      Sign 3 -> What to do instead -> CTA -> Loop

---

### THE VIRAL FEEDBACK LOOP

**Decision rules (Larry diagnostic framework):**

| Views | Saves | Diagnosis | Action |
|-------|-------|-----------|--------|
| High | High | Everything working | Scale -- use this format everywhere |
| High | Low | Hook works, content fails | Fix CTA + slides 5-7 value arc |
| Low | High | Content works, hook fails | Rewrite slide 1 with stronger pattern-interrupt |
| Low | Low | Nothing working | Full reset -- new angle, format, hook category |

**Thresholds (per hook formula, after 2+ posts with metrics):**
- 50K+ avg views -> Double down. Use in every available slot.
- 10K-50K avg views -> Healthy. Keep rotating, find the ceiling.
- <1K avg views (2+ posts) -> Drop. Stop using this formula.

**8 performance dimensions (run after each batch):**
1. Topic Fit -- did people care? (signal: views)
2. Hook Magnitude -- did hook create tension? (views vs expected)
3. Pacing -- did engagement hold? (save rate proxy)
4. Slide Density -- right amount per slide? (comment depth)
5. Value Arc -- did it build toward payoff? (save rate)
6. Save Trigger -- did slide 7-8 drive saves? (saves/views)
7. Share Trigger -- did it make people look smart? (shares/views)
8. CTA Placement -- did comment CTA work? (comments/views)

---

### THE SELF-IMPROVEMENT CYCLE

**How the system gets smarter every week:**

```
POST → WAIT 48H → PULL METRICS → DIAGNOSE → APPLY → REPEAT
```

**Step 1 — Post** (daily, automated)
Every carousel.json carries metadata: `hookFormula`, `structure`, `ctaWord`, `topic`.
This is the signal that analytics will later be matched against.

**Step 2 — Pull metrics (48h later)**
`python scripts/analytics_pull.py` fetches from PostFast `/social-posts/analytics`.
Each post is matched to its carousel slot → its hookFormula/structure/ctaWord is read.
`hook-performance.json` is updated with: per-post records, aggregated stats by formula,
learnedRules (plain English), and recommendations (what to do next).

**Step 3 — Diagnose with the 2×2 matrix**
The system auto-categorises every post into one of four buckets:
- HIGH views + HIGH saves → SCALE. Use this exact combo more.
- HIGH views + LOW saves → CTA PROBLEM. Fix slides 6-8, test new CTA word.
- LOW views + HIGH saves → HOOK PROBLEM. Rewrite slide 1. Same content, new hook.
- LOW views + LOW saves → RESET. New angle, new format, new hook category.

**Step 4 — Read before writing next batch**
Before writing ANY new carousel, Claude MUST read `hook-performance.json`.
Check `learnedRules` and `recommendations.nextHookFormula` + `recommendations.nextStructure`.
Write content that leans into what the data says works.
Avoid formulas listed in `recommendations.avoidFormulas`.

**The compound effect:**
- Week 1-2: Baseline data, first patterns emerge.
- Week 3-4: Double down on working combos, A/B test variations.
- Month 2: 2-3 high-performing combinations identified, scaled.
- Month 3+: Viral candidates appear. Target: 50K+ views (TikTok) or 2%+ save rate (Instagram).

**Key insight — saves beat raw views:**
The algorithm interprets saves as "this person wants to come back." A post with 5K views
and 3% save rate will outperform a 50K view post with 0.1% save rate over 30 days.
The analytics loop targets both together: hook stops the scroll (views), content earns the save.

---

## VISUAL IDENTITY

**Every slide must follow this exactly. No deviations.**

| Element | Specification |
|---------|---------------|
| Canvas | 1080 x 1350px, JPEG quality 96 |
| Fonts | Poppins Bold (headlines), Poppins Light (body), Poppins Medium (labels), IBM Plex Mono (footer/counter) |
| Black | RGB(8, 8, 8) -- dark slides |
| Cream | RGB(237, 232, 223) -- light slides |
| **Gold** | **RGB(200, 168, 75) -- accent word and footer rule. Always. No other shade.** |
| White | RGB(245, 240, 232) -- body text on dark slides |
| Dim | RGB(175, 170, 162) -- secondary text, handle, slide counter |
| Slide alternation | Odd slides (1,3,5,7,9) = dark. Even slides (2,4,6,8) = light. Hard rule. Enforced by renderer from slide number. |
| Footer | Gold rule 50x4px, @handle (from config) below in Dim. Every slide. |

---

## SLIDE GENERATION RULES -- NON-NEGOTIABLE

These apply to every image generated. Never break them.

1. **Slide alternation is enforced by the renderer, not the JSON.**
   The `theme` field in carousel.json is informational only. The renderer sets
   dark/light based on `slide.number % 2 == 1`. Odd = dark. Even = light.

2. **Gold is always RGB(200, 168, 75). Non-negotiable.**
   This is the ONLY gold. Never change it. Every accent word and footer rule uses it.

3. **Full-image single overlay system. Non-negotiable.**
   One uniform color tint over the ENTIRE photo — no zone-specific treatment.
   - **Dark slides:** 62% black overlay → deep dark canvas, white text pops clean.
   - **Light slides:** 65% cream overlay → warm light canvas, black text pops clean.
   Applied via `Image.blend(img, tint, BASE_ALPHA)`. The photo shows through consistently
   everywhere. This is the ONLY contrast layer. No secondary zone treatment.

4. **Zone analysis = text placement only (NOT contrast).**
   After the full overlay is applied, zone analysis finds the compositionally "open" area:
   - Dark slides: find darkest zone (most open/empty space in the photo).
   - Light slides: find lightest zone (most open/empty space in the photo).
   Text is placed in that zone for good composition. Contrast is already handled by rule 3.
   Quality check runs as a safety net — if brightness somehow fails threshold,
   an emergency 20% tint pass is added automatically.

5. **Respect the platform safe zone.**
   Never place text or key visuals in the last 13% of the frame width.
   All text stays within left 87% (x < 939px on 1080px canvas).

6. **Every slide gets individual treatment.**
   Text Y-position decided per slide from zone analysis. No carry-over.

7. **Gold word = ALL CAPS word in the headline. Falls back to last word.**
   The emotional peak word is written in ALL CAPS in carousel.json (e.g. "Start SHIPPING.").
   The renderer detects this before lowercasing, tracks it, and applies gold to it inline —
   even if it is not the last word. If no ALL CAPS word is found, last word of last line gets gold.
   Gold words are drawn WITHOUT text shadow to keep the color clean and vibrant.
   Regular text (white/black) gets a 2px shadow for extra crispness. Gold never does.
   CTA slide role="cta": headline stays unchanged (preserves ALL CAPS), gold auto-applied.

8. **Background priority order:**
   1st: Pinterest photo (slide-XX-raw.jpg already in slot directory) — always. Topic-specific real photography.
   2nd: Flat color (BLACK or CREAM from theme) — last resort, still looks clean.
   Pinterest is the ONLY background source. Kie.ai is no longer used.

9. **Image composition principles for Pinterest bgQuery selection.**
   The overlay handles contrast — the photo handles composition and mood.
   When selecting or writing bgQuery, apply these principles:
   - **Open space rule:** The photo must have a naturally clear area (empty space, gradients,
     plain backgrounds) in the zone where text will sit (top, middle, or bottom third).
   - **Subject placement:** The main subject of the photo should be in the OPPOSITE area
     from where text is expected. Text zone = empty. Subject zone = visual anchor.
   - **Dark slide photos:** Should have naturally dark zones (shadows, depth, negative space)
     even before the overlay — the 62% overlay amplifies darkness, not creates it from light.
   - **Light slide photos:** Should have naturally light/open zones (sky, clean surfaces,
     minimalist backgrounds) — the 65% cream overlay amplifies warmth, not creates it from dark.
   - **The magazine test:** "If I put this photo on a magazine cover and added the headline
     in the expected text zone, would it look intentional?" If yes — good photo.
   - **Reject:** Photos where the main subject fills 100% of the frame (no open zone).
     Photos that fight the overlay color (e.g. neon-colored photo on cream overlay).

---

## PINTEREST BACKGROUNDS -- The Visual Layer

Real photography replaces AI-generated abstract textures.
One photo per slide that visually *is* what the slide is talking about.
Same background shared across EN/FR/ES versions — only text + auto-music vary.

**How it works:**
1. Claude writes `bgQuery` per slide in `carousel.json` (EN slides only)
2. Claude searches Pinterest for each query, picks the best matching photo
3. `fetch_backgrounds.py` downloads + crops to 1080×1350px
4. `generate_slides_py.py` sees raw files exist → skips Kie.ai → overlays text

**Writing bgQuery values — the rule:**

Read the slide headline. Find the 2-3 most visual, concrete words or concepts in it.
That is the query. Every slide gets a different, topic-specific query.
The photo should make someone feel the concept before they read a single word.

Formula: `{2-3 concrete visual words from THIS slide's headline} {dark or light} aesthetic`

**Good — specific to what the slide actually says:**

| Slide headline | bgQuery |
|----------------|---------|
| "You have watched 300 tutorials. Built zero products." | `abandoned notebook stack dark aesthetic` |
| "Everyone prompts AI like a Google search." | `search bar typing scattered light aesthetic` |
| "AI does not read minds. It reads what you give it." | `blank page empty input dark aesthetic` |
| "Weak: write me an email. Strong: who, fear, outcome." | `two paths split contrast light aesthetic` |
| "Same AI. Different context. One closes deals." | `before after transformation dark aesthetic` |
| "Role. Goal. Constraint. Audience." | `four objects arranged desk light aesthetic` |
| "The edge is not intelligence. It is specificity." | `sharp focus lens precision dark aesthetic` |
| "Drop a comment. CONTEXT." | `open envelope invitation warm light aesthetic` |
| "Now you know exactly what it is." | `clarity reveal window light dark aesthetic` |

**Bad — generic mood, not specific to the slide:**
- `dark abstract minimal aesthetic` — could be any slide, matches nothing specific
- `fog blur aesthetic dark` — mood only, not the concept of this slide

**The test:** Could this photo appear on a magazine cover story about exactly what this slide says?
If yes — good query. If it is just "looks dark and moody" — rewrite it.

**Pinterest workflow (per slot):**
```bash
# 1. See what to search
python scripts/fetch_backgrounds.py --slot-dir posts/YYYY-MM-DD/HHMM --list

# 2. Search each query on Pinterest, pick best photo
#    Claude opens: https://www.pinterest.com/search/pins/?q=QUERY
#    Claude picks the image that best matches the slide concept

# 3. Save each photo (auto-upgrades to highest resolution, crops to 1080x1350)
python scripts/fetch_backgrounds.py --slot-dir posts/YYYY-MM-DD/HHMM --slide 1 --url https://i.pinimg.com/...

# 4. Save all slides at once
python scripts/fetch_backgrounds.py --slot-dir posts/YYYY-MM-DD/HHMM --map '{"1":"url","2":"url",...}'

# 5. Check progress
python scripts/fetch_backgrounds.py --slot-dir posts/YYYY-MM-DD/HHMM --status

# 6. Generate slides (Kie.ai skipped — uses Pinterest backgrounds directly)
python scripts/generate_slides_py.py posts/YYYY-MM-DD/HHMM
```

**URL handling:**
- Any Pinterest URL resolution is auto-upgraded to `/originals/` (full quality)
- Falls back to `/736x/` if originals is unavailable
- Center-crop applied to fit 1080×1350 (4:5 portrait canvas)

**Fallback:**
If no Pinterest background for a slide, Kie.ai generates an abstract texture as before.
Slides with and without Pinterest backgrounds can be mixed in the same slot.

---

## KIE.AI IMAGE GENERATION (fallback)

**Correct endpoints (never use any other):**
- Submit task: `POST https://api.kie.ai/api/v1/jobs/createTask`
- Poll result: `GET  https://api.kie.ai/api/v1/jobs/recordInfo?taskId={taskId}`

**Model:** `nano-banana-2`

**Polling:**
- State = `success` means `resultJson.resultUrls[0]` is ready
- Takes 40-120s. Poll timeout: 360s
- Submit ALL tasks in parallel first. Poll all in parallel second.
- Code 433 = credits exhausted for the day. Use fallback (reuse existing raw or flat color).

**Image prompt structure (Abstract Editorial Textures -- no photography):**
- Dark slides: deep near-black abstract textures -- ink washes, geometric noise, grain, charcoal gradients
- Light slides: warm cream/ivory abstract textures -- soft gradients, paper grain, geometric shapes, paint washes
- Always: no text, no people, no faces, no logos, no watermarks, no photography, no recognisable scenes
- Textures rotate through 7 dark variants and 7 light variants, indexed by slide number
- All prompts end with: "Minimal. Clean. No text, no people, no logos. Abstract texture only. Premium editorial feel. 4:5 ratio."

---

## POSTFAST -- Posting Layer

**Base URL:** `https://api.postfa.st`
**Auth header:** `pf-api-key: {apiKey}`
**TikTok account ID:** from `config.postfast.accounts.tiktok.id`
**Instagram account ID:** from `config.postfast.accounts.instagram.id`

**Upload flow (2 steps):**
1. `POST /file/get-signed-upload-urls` with `{contentType: "image/jpeg", count: 1}`
2. `PUT` raw file bytes to the signed S3 URL

**Rate limit:** Space uploads 1.5s apart. Retry on 429 with exponential backoff (15s base, doubles each attempt, max 8 retries).

**Post payload:**
```json
{
  "posts": [
    {"socialMediaId": "TIKTOK_ID", "content": "caption", "mediaItems": [...], "scheduledAt": "ISO"},
    {"socialMediaId": "INSTAGRAM_ID", "content": "caption", "mediaItems": [...], "scheduledAt": "ISO"}
  ],
  "controls": {
    "tiktokPrivacy": "PUBLIC",
    "tiktokAllowComments": true,
    "tiktokAutoAddMusic": true,
    "instagramPublishType": "TIMELINE"
  }
}
```

**Posting times (Paris / Europe/Paris timezone):**
07:30, 09:00, 13:00, 18:00, 21:00
(5 slots × 3 languages = 15 posts/day total across TikTok + Instagram)

**Cancel a post:** `DELETE /social-posts/{id}` returns `{"deleted": true}`

**Multi-language posting (same accounts, staggered times):**
All 3 languages post to the same TikTok + Instagram accounts (from config).
Each language is a separate post, staggered so they don't hit the algorithm simultaneously:
- `en`: slot time + 0 min (e.g. 07:30)
- `fr`: slot time + 3 min (e.g. 07:33)
- `es`: slot time + 6 min (e.g. 07:36)
Result per slot: 3 posts (EN/FR/ES) × 2 platforms = 6 PostFast posts scheduled.

---

## ANALYTICS -- Feedback Loop

**Source:** PostFast `GET /social-posts/analytics`
No separate Instagram Graph API token needed. PostFast returns metrics for both TikTok and Instagram natively.

**Endpoint parameters:**
- `startDate` (ISO 8601, required) -- e.g. `2026-01-01T00:00:00.000Z`
- `endDate` (ISO 8601, required)
- `socialMediaIds` (comma-separated UUIDs, optional) -- filter by account

**Metrics returned per post (all as strings -- parse to int):**
- `impressions` -- total views (use as primary views metric)
- `reach` -- unique accounts reached
- `likes`, `comments`, `shares`, `clicks`
- `extras.saved` -- saves (Instagram-specific, lives in extras object)

**Implementation notes:**
- Posts published <2 hours ago are skipped (TikTok/Instagram indexing delay -- metrics unreliable)
- Run `analytics_pull.py --force` to re-pull existing records with fresh metrics
- Default range: last 30 days. Override with `--since YYYY-MM-DD`
- `hook-performance.json` is updated after every pull with new `learnedRules`

**`hook-performance.json` structure:**
```json
{
  "lastUpdated": "ISO timestamp",
  "totalPostsTracked": 18,
  "metricsAvailable": 16,
  "analyticsNote": "Human-readable status",
  "learnedRules": ["Plain-English rules for Claude to read before writing"],
  "byHookFormula": { "formula_name": { "posts": N, "avg": { "views": X, ... } } },
  "byStructure":   { "structure_name": { ... } },
  "byCtaWord":     { "WORD": { ... } },
  "posts": [ { "date", "slot", "platform", "hookFormula", "ctaWord", "metrics", ... } ]
}
```

**Read `learnedRules` every session before writing new content.**
The rules engine auto-generates plain-English guidance:
- SCALE: which formulas have 50K+ views (double down)
- KEEP ROTATING: which are in the 10K-50K healthy zone
- DROP: which have <1K views across 2+ posts
- CTA PROBLEM / HOOK PROBLEM / RESET NEEDED: 2x2 diagnostic signals
- Best save rate formula, best comment-driving CTA word

---

## COMMON ISSUES

| Problem | Fix |
|---------|-----|
| Kie.ai polling returns 404 | Use GET /api/v1/jobs/recordInfo -- never /getTaskDetail |
| Image gen timeout | Nano Banana 2 takes 40-120s. Timeout 360s. Submit all first, poll all in parallel. |
| Kie.ai code 433 | Credits exhausted for the day. Reuse existing raws or use flat color fallback. |
| Em-dash renders as garbled text | Never use em-dashes. Use period or comma. Rule is permanent. |
| Hook sounds like news | Apply 4 P's test. If it does not score 3/4, rewrite starting from emotion not event. |
| Text over subject in image | Analyze image first. Find dark/empty zone. Place text only there. |
| CTA word not gold/uppercase | headline in slide 8 must end with ctaWord ALL CAPS. Renderer skips lowercase on CTA slides. |
| Wrong gold shade | Gold is always RGB(200, 168, 75). No other shade ever. |
| PostFast 429 rate limit | Upload is paced at 1.5s/image. Retry with exponential backoff built into upload_image(). |
| PostFast 400 "scheduledAt required" | Always include scheduledAt. For immediate posts, use current ISO timestamp. |
| Past-time slots | post_to_postfast.py auto-detects past slots and posts immediately instead. |
| TikTok stuck in QUEUE forever | This was a Postiz limitation. We use PostFast -- fully supports TikTok photo carousels. |
| build_resource.py not found | Script lives at scripts/build_resource.py. Reads resource.json from slot dir, renders PDF. |
| Analytics returning 0 metrics | Run with --force to re-pull. PostFast may take up to 24h to fetch first metrics on a post. |
| analytics_pull.py skipping posts | Posts <2h old are skipped intentionally (indexing delay). Run again later. |
| FR/ES posts not scheduling | Account IDs are null in config.postfast.languages -- add real IDs when accounts are created. |
| hook-performance.json says "not enough data" | Need 2+ posts with real metrics per hook formula. Keep posting and re-pull after 48h. |

---

## FILE MAP

```
carousel-pipeline/
+-- SKILL.md                       <- this file (full system documentation)
+-- config.json                    <- creator profile, API credentials, posting schedule
+-- hook-performance.json          <- performance history + learned rules (read before every session)
+-- preview.html                   <- browser-based carousel slide preview
+-- scripts/
|   +-- daily_run.py               <- master orchestrator (chain all steps)
|   +-- research_sweep.py          <- 3-source research: DuckDuckGo + Reddit + HN (no API key)
|   +-- fetch_backgrounds.py        <- Pinterest image search + download (per slide bgQuery)
|   +-- generate_slides_py.py      <- text overlay (uses Pinterest bg if exists, else Kie.ai)
|   +-- build_resource.py          <- renders resource.json to branded PDF
|   +-- post_to_postfast.py        <- PostFast: upload + schedule TikTok + Instagram
|   +-- analytics_pull.py          <- PostFast /social-posts/analytics -> hook-performance.json
|   +-- generate_content.py        <- OpenAI-based content gen (backup / headless mode)
|   +-- write_carousels.py         <- standalone carousel writer (older helper, less used)
|   +-- post_to_postiz.py          <- DEPRECATED: Postiz had TikTok queue bug, replaced by PostFast
+-- research/
|   +-- YYYY-MM-DD.json            <- daily research sweep output (topics, scores, convergence signals)
+-- posts/YYYY-MM-DD/HHMM/
|   +-- carousel.json              <- EN/FR/ES carousel content (Claude writes this)
|   +-- resource.json              <- resource content (Claude writes this)
|   +-- resource.pdf               <- rendered PDF (build_resource.py output)
|   +-- slides/
|       +-- en/                    <- language-specific slides (multi-lang mode)
|       |   +-- slide-01-final.jpg ... slide-09-final.jpg
|       +-- slide-01-raw.jpg       <- Kie.ai background (untouched, flat mode)
|       +-- slide-01-final.jpg     <- final with text overlay (flat mode)
+-- logs/
|   +-- YYYY-MM-DD.log             <- daily run logs (verbose, per step)
+-- fonts/
|   +-- Poppins-Bold.ttf
|   +-- Poppins-Light.ttf
|   +-- Poppins-Medium.ttf
|   +-- IBMPlexMono-Regular.ttf
+-- references/
    +-- hooks.md                   <- 110 hook examples + 7 formulas
    +-- structures.md              <- 5 viral structures with flow diagrams
    +-- templates.md               <- slide copy templates
```
