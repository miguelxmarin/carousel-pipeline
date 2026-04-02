CREDENTIALS FOLDER
==================

This folder is intentionally almost empty.

Google Drive integration does NOT require API keys or OAuth tokens.
Claude uploads PDFs directly via Chrome — the same way it fetches
Pinterest backgrounds. No setup required.

How it works:
  1. Run: python scripts/upload_to_drive.py --slot-dir posts/YYYY-MM-DD/HHMM
  2. Claude opens drive.google.com in your Chrome browser
  3. Navigates to (or creates): CLAUDE AGENT CAROUSEL PDFS/
  4. Creates a subfolder for the post: {date} -- {topic} [{CTA_WORD}]
  5. Uploads resource.pdf
  6. Sets sharing to "Anyone with the link -- Viewer"
     Anyone in the world can view and download -- no Google login needed
  7. Returns the shareable link

REQUIREMENTS:
  - Chrome browser open and logged into Google Drive
  - That is it. No API keys. No tokens. No console.cloud.google.com.

SECURITY NOTE:
  This .gitignore excludes all *.json files in this folder as a safety net
  in case you ever add credentials for another integration.
