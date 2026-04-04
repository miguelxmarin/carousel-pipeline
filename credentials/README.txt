CREDENTIALS FOLDER
==================

This folder stores your Google OAuth credentials for Drive uploads.
No other credentials are needed -- all other pipeline steps (PostFast, Pinterest)
are configured in config.json.


GOOGLE DRIVE SETUP (one-time, ~3 minutes)
------------------------------------------

1. Go to https://console.cloud.google.com

2. Create a project (or select an existing one)

3. Enable the Drive API:
   APIs & Services -> Library -> search "Google Drive API" -> Enable

4. Create OAuth credentials:
   APIs & Services -> Credentials -> + Create Credentials
   -> OAuth 2.0 Client ID -> Application type: Desktop app
   -> Name it anything (e.g. "Carousel Pipeline") -> Create
   -> Download JSON (the download icon on the right)

5. Rename the downloaded file to:
   credentials/google_oauth_credentials.json

6. Run the upload script once:
   python scripts/upload_to_drive.py --slot-dir posts/YYYY-MM-DD/HHMM

   Your browser will open -> sign into your Google account -> allow access.
   A token.json is saved here automatically.

7. Done. All future uploads run fully automated -- no browser needed.


FILES IN THIS FOLDER
---------------------
google_oauth_credentials.json  -- Your OAuth client secret (gitignored)
token.json                     -- Auto-saved auth token (gitignored)


SECURITY NOTE
--------------
Both files are gitignored. Never commit them to a public repo.
The .gitignore in this folder excludes all *.json files.

If your token expires (rare -- refresh tokens last indefinitely unless revoked),
just delete token.json and re-run the script. Browser opens once, done.
