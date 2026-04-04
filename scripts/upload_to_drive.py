"""
upload_to_drive.py
------------------
Uploads a carousel slot's PDF resource to Google Drive via the Drive API v3.

Uses OAuth2 (google-auth-oauthlib). No browser automation required.

SETUP (one-time, ~3 minutes):
  1. Go to https://console.cloud.google.com
  2. Create a project (or select an existing one)
  3. Enable the Drive API:
       APIs & Services -> Library -> search "Drive API" -> Enable
  4. Create credentials:
       APIs & Services -> Credentials -> Create Credentials
       -> OAuth 2.0 Client ID -> Desktop app -> Download JSON
  5. Rename the downloaded file to:
       credentials/google_oauth_credentials.json
  6. Run this script once -- your browser opens, you sign in, done.
     A token.json is saved to credentials/ for all future runs.

WHAT IT DOES:
  1. Reads carousel.json to get date, topic, and CTA word
  2. Finds or creates root folder: CLAUDE AGENT CAROUSEL PDFS
  3. Finds or creates subfolder:   {date} -- {topic-slug} [{CTA_WORD}]
  4. Uploads resource.pdf
  5. Sets sharing to: Anyone with the link -- Viewer (no login required)
  6. Returns the shareable link
  7. Saves the link to carousel.json under meta.resourceLink

USAGE:
  python scripts/upload_to_drive.py --slot-dir posts/2026-04-02/1300
  python scripts/upload_to_drive.py --slot-dir posts/2026-04-02/1300 --dry-run
"""

import argparse
import json
import re
import sys
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT             = Path(__file__).resolve().parent.parent
CREDS_DIR        = ROOT / "credentials"
OAUTH_CREDS_FILE = CREDS_DIR / "google_oauth_credentials.json"
TOKEN_FILE       = CREDS_DIR / "token.json"
DRIVE_ROOT_NAME  = "CLAUDE AGENT CAROUSEL PDFS"
SCOPES           = ["https://www.googleapis.com/auth/drive.file"]

# Force UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ── Auth ───────────────────────────────────────────────────────────────────────

def get_drive_service():
    """Authenticate and return a Google Drive API v3 service client."""
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        print("\nERROR: Google API libraries not installed.")
        print("Run:  pip install google-auth-oauthlib google-api-python-client")
        sys.exit(1)

    creds = None

    # Load saved token if it exists
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    # Refresh or run OAuth flow if needed
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                print("  Auth token refreshed.")
            except Exception as e:
                print(f"  Token refresh failed ({e}), re-authorizing...")
                creds = None

        if not creds:
            if not OAUTH_CREDS_FILE.exists():
                print(f"\nERROR: OAuth credentials file not found:")
                print(f"  Expected: {OAUTH_CREDS_FILE}")
                print()
                print("SETUP (one-time, ~3 minutes):")
                print("  1. Go to https://console.cloud.google.com")
                print("  2. Create/select a project")
                print("  3. APIs & Services -> Library -> search 'Drive API' -> Enable")
                print("  4. APIs & Services -> Credentials -> Create Credentials")
                print("     -> OAuth 2.0 Client ID -> Desktop app -> Download JSON")
                print(f"  5. Save the downloaded file as:")
                print(f"     {OAUTH_CREDS_FILE}")
                print("  6. Re-run this script -- browser opens, sign in, done.")
                sys.exit(1)

            flow  = InstalledAppFlow.from_client_secrets_file(str(OAUTH_CREDS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
            print("  OAuth consent complete.")

        # Save token for future runs
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        print(f"  Token saved: {TOKEN_FILE.relative_to(ROOT)}")

    return build("drive", "v3", credentials=creds)


# ── Drive helpers ──────────────────────────────────────────────────────────────

def get_or_create_folder(service, name: str, parent_id: str = None) -> str:
    """Return folder ID -- finds existing folder or creates it."""
    q = (
        f"name='{name}' and mimeType='application/vnd.google-apps.folder'"
        " and trashed=false"
    )
    if parent_id:
        q += f" and '{parent_id}' in parents"

    results = service.files().list(q=q, fields="files(id, name)").execute()
    files   = results.get("files", [])

    if files:
        return files[0]["id"]

    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        meta["parents"] = [parent_id]

    folder = service.files().create(body=meta, fields="id").execute()
    print(f"  Created folder: {name}")
    return folder["id"]


def upload_pdf(service, pdf_path: Path, folder_id: str, filename: str = "") -> dict:
    """Upload PDF to the specified folder. Returns file metadata."""
    try:
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        print("ERROR: google-api-python-client not installed.")
        sys.exit(1)

    file_meta = {"name": filename or pdf_path.name, "parents": [folder_id]}
    media     = MediaFileUpload(str(pdf_path), mimetype="application/pdf", resumable=True)
    file      = service.files().create(
        body=file_meta, media_body=media, fields="id,name,webViewLink"
    ).execute()
    return file


def set_public_sharing(service, file_id: str) -> None:
    """Set file sharing to: Anyone with the link -- Viewer."""
    service.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"},
    ).execute()


# ── Helpers ────────────────────────────────────────────────────────────────────

def slug(text: str, max_words: int = 5) -> str:
    """Convert a topic string to a short readable slug for folder naming."""
    text  = re.sub(r"[^\w\s-]", "", text.lower())
    words = text.split()[:max_words]
    return "-".join(words)


# ── Main ───────────────────────────────────────────────────────────────────────

def run(slot_dir: Path, dry_run: bool = False, lang: str = "") -> None:
    """Upload the PDF resource for a slot to Google Drive.

    All language versions (EN/FR/ES) upload to the SAME subfolder.
    When --lang is provided the file is stored as resource_en.pdf etc.
    so multiple languages can coexist without overwriting each other.
    """

    # ── Validate ───────────────────────────────────────────────────────────────
    pdf_path = slot_dir / "resource.pdf"
    if not pdf_path.exists():
        print(f"\nERROR: resource.pdf not found at {pdf_path}")
        print("Run first:  python scripts/build_resource.py --slot-dir " + str(slot_dir.relative_to(ROOT)))
        sys.exit(1)

    # Drive filename — language-tagged when --lang is supplied
    drive_filename = f"resource_{lang}.pdf" if lang else "resource.pdf"

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

    # ── Print summary ──────────────────────────────────────────────────────────
    print(f"\n{'='*62}")
    print(f"  GOOGLE DRIVE UPLOAD")
    print(f"{'='*62}")
    print(f"  Local PDF   : {pdf_path}")
    print(f"  Drive name  : {drive_filename}")
    print(f"  Size        : {pdf_size_kb:.1f} KB")
    print(f"  Root folder : {DRIVE_ROOT_NAME}")
    print(f"  Subfolder   : {subfolder_name}")
    print(f"{'='*62}\n")

    if dry_run:
        print("  [DRY RUN] No upload performed.")
        return

    # ── Authenticate ───────────────────────────────────────────────────────────
    print("  Authenticating...")
    service = get_drive_service()

    # ── Folders ────────────────────────────────────────────────────────────────
    print(f"  Finding/creating: {DRIVE_ROOT_NAME}/")
    root_id = get_or_create_folder(service, DRIVE_ROOT_NAME)

    print(f"  Finding/creating: {subfolder_name}/")
    sub_id  = get_or_create_folder(service, subfolder_name, parent_id=root_id)

    # ── Upload ─────────────────────────────────────────────────────────────────
    print(f"  Uploading {drive_filename} ({pdf_size_kb:.1f} KB)...")
    file    = upload_pdf(service, pdf_path, sub_id, filename=drive_filename)
    file_id = file["id"]

    # ── Share ──────────────────────────────────────────────────────────────────
    print("  Setting sharing: Anyone with the link -- Viewer")
    set_public_sharing(service, file_id)

    # ── Output ─────────────────────────────────────────────────────────────────
    view_link     = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
    download_link = f"https://drive.google.com/uc?export=download&id={file_id}"

    print(f"\n  Upload complete.")
    print(f"  Download link : {download_link}")

    # ── Save link to carousel.json ─────────────────────────────────────────────
    if carousel_path.exists():
        data = json.loads(carousel_path.read_text(encoding="utf-8"))
        data.setdefault("meta", {})["resourceLink"] = view_link
        carousel_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"  Saved to carousel.json: meta.resourceLink")

    # ── Copy-paste ready output ────────────────────────────────────────────────
    print(f"\n{'='*62}")
    print(f"  RESOURCE PDF LINK (copy-paste ready):")
    print(f"  {view_link}")
    print(f"{'='*62}\n")


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Upload carousel PDF resource to Google Drive.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--slot-dir", required=True,
        help="Path to slot directory, e.g. posts/2026-04-02/1300",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be uploaded without uploading",
    )
    parser.add_argument(
        "--lang", default="", choices=["", "en", "fr", "es"],
        help="Language tag for the filename (e.g. en → resource_en.pdf). "
             "All languages go to the same Drive subfolder.",
    )
    args = parser.parse_args()

    slot_dir = Path(args.slot_dir)
    if not slot_dir.is_absolute():
        slot_dir = ROOT / slot_dir
    if not slot_dir.exists():
        print(f"ERROR: slot directory not found: {slot_dir}")
        sys.exit(1)

    run(slot_dir, dry_run=args.dry_run, lang=args.lang)


if __name__ == "__main__":
    main()
