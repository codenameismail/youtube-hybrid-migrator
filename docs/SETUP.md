# Setup guide

You do this once. It takes about 15 minutes.

## Part 1: Python and the project

1. Install **Python 3.11 or newer** from <https://www.python.org/downloads/>. On Windows, tick **"Add Python to PATH"** in the installer. (3.10 still works but prints a deprecation warning from Google's libraries.)
2. Open a terminal in the project folder and create a virtual environment:
    ```bash
    python -m venv .venv
    ```
    (If `python` isn't found, try `py` on Windows or `python3` on Mac/Linux.)
3. Activate it. You must do this in every new terminal:
    - Windows cmd/PowerShell: `.venv\Scripts\activate`
    - Git Bash: `source .venv/Scripts/activate`
    - Mac/Linux: `source .venv/bin/activate`
4. Install the dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Part 2: Google Cloud credentials (official API access)

The tool needs permission to use the official YouTube API on **both** accounts: it reads the OLD one and writes YouTube-only playlists to the NEW one.

1. Go to <https://console.cloud.google.com/> and sign in. Use your **NEW** account if you want the project to survive deleting the old one. Either works.
2. Create a project (name it anything, e.g. "YouTube Migrator").
3. In the top search bar, find **YouTube Data API v3** and click **Enable**.
4. Open **Google Auth Platform** (or **APIs & Services > OAuth consent screen**) and set it up:
    - User type / audience: **External**
    - Fill in an app name and your email
    - Under **Audience**, add **both** your OLD and NEW Google accounts as **Test users**
5. Go to **Clients** (or **APIs & Services > Credentials**) and click **Create client**, then pick **Desktop app**.
6. Download the JSON file and save it as **`secrets/client_secret.json`** (create the `secrets` folder if it doesn't exist; the tool also creates it the first time you run it).

**Important when logging in via the browser popup:**

- On first login, Google shows **"Google hasn't verified this app"**. Click **Advanced**, then **Go to (app name)**, then **Continue**.
- If your Google account has **multiple YouTube channels / Brand Accounts** (even if two share the same name), Google shows a second screen asking which channel to pick. Make sure you click the exact channel (`@handle`) that holds your data.

## Part 3: Browser cookies (where to log in with what)

You capture two cookie files—one for each account, from **two different websites**.

> **Rule:** Always use a fresh **Firefox Private Window** with **only one Google account signed in at a time** (check that `X-Goog-AuthUser` is `0`). If two accounts are signed into the same window, cookies can mix up or fail with `HTTP 400`. Never share or paste these headers anywhere—they act like live passwords.

### 3A. NEW account cookies -> from `music.youtube.com` (`secrets/new_headers.json`)

Used to write likes, subscriptions, and music playlists without using API quota.

1. Open a fresh Firefox **Private Window**, go to <https://music.youtube.com>, and log into your **NEW** account only.
2. Press **F12** -> **Network** tab -> filter by `browse`.
3. Click **Library** in YouTube Music. Right-click the `POST` request named `browse?...` -> **Copy** -> **Copy Request Headers**.
4. In your terminal (venv active), run:
    ```bash
    ytmusicapi browser --file secrets/new_headers.json
    ```
5. Paste the headers, press Enter, then **Ctrl+Z** (Windows) or **Ctrl+D** (Mac/Linux), then Enter.
6. Close the Private Window **without** clicking "Sign out" (signing out kills the cookie).

### 3B. OLD account cookies -> from `www.youtube.com/feed/channels` (`secrets/old_headers.json`)

Google's official API hides many subscriptions (often returning only a fraction of your channels). Capturing cookies from `www.youtube.com` lets the script read your full subscription list directly from YouTube.

1. Open a new Firefox **Private Window**, go to <https://www.youtube.com/feed/channels>, and log into your **OLD** account only (if you have multiple channels, switch to the right `@handle` in the top-right menu).
2. Press **F12** -> **Network** tab -> filter by `browse`.
3. Scroll down the page (or click **Subscriptions** in the left menu) until a `POST` request to `browse?...` appears under `www.youtube.com`.
4. Right-click it -> **Copy** -> **Copy Request Headers**.
5. In your terminal, run:
    ```bash
    ytmusicapi browser --file secrets/old_headers.json
    ```
6. Paste the headers, press Enter, then **Ctrl+Z** (Windows) or **Ctrl+D** (Mac/Linux), then Enter.
7. Close the Private Window **without** clicking "Sign out".

## Part 4: Run it

```bash
python migrate.py
```

1. The OLD account's browser login opens first (first run only). Log in as the **OLD** account and select the right channel.
2. You'll see both account names. Check that they're right and type `YES`.
3. Likes and subscriptions run (slowly, by design).
4. For playlists, the tool writes `state/playlist_types.txt` and stops. Open it, fix any wrong MUSIC/YOUTUBE guess, and save.
5. Run `python migrate.py playlists --only "<title of a small YouTube playlist>"` as a test. When it needs the NEW account's official-API login, log in as the **NEW** account. Check in YouTube Music (close and reopen the app) that this playlist does **not** appear there.
6. Run `python migrate.py playlists` for the rest. If it stops at the daily quota, run the same command the next day.

Then follow the checklist in the [README](../README.md#before-you-delete-the-old-account).
