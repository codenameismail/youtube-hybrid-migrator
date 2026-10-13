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

On first login for each account, Google shows **"Google hasn't verified this app"**. That's expected for your own test app. Click **Advanced**, then **Go to (app name)**, then **Continue**.

The app stays in "Testing" mode, so Google may ask you to log in again if more than a week passes between runs.

## Part 3: NEW account cookies (YouTube Music access)

Likes, subscriptions and music playlists are written through YouTube Music using your browser session.

1. Open **Firefox** in a **Private Window** (Chrome and Edge make cookie extraction harder).
2. Go to <https://music.youtube.com> and log into your **NEW** account only.
3. Press **F12**, open the **Network** tab, and type `browse` in the filter box.
4. Click **Library** in YouTube Music. A request named `browse?...` appears.
5. Right-click it, then **Copy**, then **Copy Request Headers**.
6. In your terminal (venv active), run:
   ```bash
   ytmusicapi browser --file secrets/new_headers.json
   ```
7. Paste the copied text, press Enter, then **Ctrl+Z** (Windows) or **Ctrl+D** (Mac/Linux), then Enter.

Cookies expire. If you come back after a while and get authentication errors, repeat this part.

## Part 4: Run it

```bash
python migrate.py
```

1. The OLD account's browser login opens first (first run only). Log in as the **OLD** account.
2. You'll see both account names. Check that they're right and type `YES`.
3. Likes and subscriptions run (slowly, by design).
4. For playlists, the tool writes `state/playlist_types.txt` and stops. Open it, fix any wrong MUSIC/YOUTUBE guess, and save.
5. Run `python migrate.py playlists --only "<title of a small YouTube playlist>"` as a test. When it needs the NEW account's official-API login, log in as the **NEW** account. Check in YouTube Music (close and reopen the app) that this playlist does **not** appear there.
6. Run `python migrate.py playlists` for the rest. If it stops at the daily quota, run the same command the next day.

Then follow the checklist in the [README](../README.md#before-you-delete-the-old-account).
