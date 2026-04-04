# Carousel Pipeline

A fully automated carousel content machine for TikTok and Instagram, built to run inside **Claude Code**.

Claude does the thinking. The scripts handle the infrastructure.

---

## What it does

Every day it:

1. **Researches** fresh audience friction and trending topics via web search
2. **Writes** carousel posts using The Carousel Method (9-slide structure, proven hook formulas)
3. **Browses Pinterest** to find real photography — 9 images per post
4. **Generates slides** with smart text overlays via Pillow (1080×1350px)
5. **Builds a PDF resource** for every post CTA ("Comment WORD — I'll send you the PDF")
6. **Uploads PDFs to Google Drive** automatically, organized by date and topic
7. **Posts to TikTok + Instagram** via PostFast with precise scheduling
8. **Pulls analytics** and learns which hooks, CTAs, and structures perform
9. **Feeds learnings** back into tomorrow's content automatically

Supports single-language or multilingual (EN + FR + ES) modes. Configure during onboarding.

---

## Requirements

- **Claude Code** — this pipeline runs as a Claude Code skill
- **Python 3.11+**
- **Node.js 18+**
- **PostFast account** — for posting to TikTok + Instagram ([app.postfa.st](https://app.postfa.st))
- **Google Drive** (optional) — for automatic PDF uploads. No API key needed — Claude uploads via Chrome.

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
npm install
```

### 2. Run onboarding

```bash
node scripts/onboarding.js
```

This asks you 10 questions and builds your `config.json`:
- Creator name, niche, audience, brand voice
- Language preference (EN / FR / ES / multilingual)
- Posts per day and posting schedule
- PostFast API key and account IDs
- Google Drive setup (optional)

### 3. Connect PostFast

PostFast handles both TikTok and Instagram from one dashboard.

1. Sign up at [app.postfa.st](https://app.postfa.st)
2. Connect your TikTok and Instagram accounts
3. Go to Settings → API Keys → copy your API key
4. Go to Settings → Connected Accounts → copy each account ID
5. Paste both into onboarding when prompted (or edit `config.json` directly)

### 4. (Optional) Connect Google Drive

Uses the Google Drive API v3 with OAuth2. One-time setup (~3 minutes), fully automated after that.

**Setup:**
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a project → Enable the **Google Drive API**
3. APIs & Services → Credentials → Create OAuth 2.0 Client ID → **Desktop app** → Download JSON
4. Save the downloaded file as `credentials/google_oauth_credentials.json`
5. Run once: `python scripts/upload_to_drive.py --slot-dir posts/YYYY-MM-DD/HHMM`
   — browser opens → sign in → `token.json` saved → done

All future uploads run fully automated. No browser. No Chrome. No session required.

**What it does:**
1. Finds or creates folder `CLAUDE AGENT CAROUSEL PDFS`
2. Creates subfolder `{date} -- {topic} [{CTA_WORD}]`
3. Uploads `resource.pdf`
4. Sets sharing to **"Anyone with the link — Viewer"** — no Google account needed to view or download
5. Saves the shareable link to `carousel.json` under `meta.resourceLink`

---

## Running the pipeline

```bash
# Daily run — Claude researches, writes, browses Pinterest, generates, posts
python scripts/daily_run.py

# Generate slides for a specific slot
python scripts/generate_slides_py.py posts/YYYY-MM-DD/HHMM --lang en

# Build the PDF resource
python scripts/build_resource.py --slot-dir posts/YYYY-MM-DD/HHMM

# Upload PDF to Google Drive
python scripts/upload_to_drive.py --slot-dir posts/YYYY-MM-DD/HHMM

# Post to TikTok + Instagram (uses config language by default)
python scripts/post_to_postfast.py --date YYYY-MM-DD --now

# Pull analytics and update learned rules
python scripts/analytics_pull.py

# Dry run — validate everything without posting
python scripts/daily_run.py --dry-run
```

---

## How Claude Code uses this skill

This repository includes `SKILL.md` — a full operating manual for Claude.

When you open this project in Claude Code, Claude reads `SKILL.md` and knows:
- The full pipeline flow
- The Carousel Method (9-slide structure, hook formulas, CTA rules)
- Renderer design rules (gold text, hook gradients, alternating dark/light)
- Current performance state and learned rules from `hook-performance.json`
- How to research, write content, browse Pinterest, and trigger each script

You talk to Claude in natural language. It handles the rest.

---

## Slide design

- **1080 × 1350px** portrait (4:5 — optimal for TikTok and Instagram carousels)
- **Odd slides** (1, 3, 5, 7, 9): dark — 62% black overlay on photo
- **Even slides** (2, 4, 6, 8): light — 65% cream overlay on photo
- **Hook slide** (slide 1): gradient fade from photo into black, Anton font, centered, no slide counter
- **Gold text**: last 2 words of hook headline always gold (CTA phrase feel). On light slides, 1px dark stroke ensures crisp edges against the cream background.
- **Real photography**: Claude browses Pinterest and picks one image per slide per post

---

## File structure

```
carousel-pipeline/
├── SKILL.md                    # Claude's operating manual
├── config.json                 # Your setup (gitignored — use config.example.json as template)
├── config.example.json         # Template — copy to config.json and fill in
├── hook-performance.json       # Learned rules from analytics (gitignored)
├── requirements.txt            # Python dependencies
├── scripts/
│   ├── onboarding.js           # First-time setup wizard
│   ├── generate_slides_py.py   # Slide renderer (Pillow)
│   ├── fetch_backgrounds.py    # Pinterest image downloader
│   ├── build_resource.py       # PDF resource builder
│   ├── upload_to_drive.py      # Google Drive uploader
│   ├── post_to_postfast.py     # PostFast scheduler
│   ├── analytics_pull.py       # Analytics puller + hook-performance updater
│   ├── daily_run.py            # Full daily pipeline runner
│   └── research_sweep.py       # Web research (Reddit, web search)
├── credentials/
│   ├── README.txt              # Google Drive setup instructions
│   └── .gitignore              # Protects credentials from being committed
├── fonts/                      # Auto-downloaded on first run
└── posts/                      # Generated content (gitignored)
    └── YYYY-MM-DD/
        └── HHMM/
            ├── carousel.json
            ├── resource.json
            ├── resource.pdf
            └── slides/
                ├── en/
                ├── fr/
                └── es/
```

---

## What you need (summary)

| Service | Required | Purpose | Cost |
|---------|----------|---------|------|
| Claude Code | Yes | Runs the pipeline | Anthropic subscription |
| PostFast | Yes | Posts to TikTok + Instagram | Paid plan |
| Pinterest | Yes | Background photography (browsed by Claude) | Free |
| Google Drive | Optional | PDF resource uploads (no API key — Claude uploads via Chrome) | Free |

No image generation API required. All slide backgrounds come from Pinterest photography.

---

## License

MIT — use it, adapt it, build on it.
