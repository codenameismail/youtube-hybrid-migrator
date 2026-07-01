# 🚀 YouTube Ultimate Migrator

A bulletproof, hybrid Python script to transfer your entire YouTube life (Liked Videos, Subscriptions, and Playlists) from an old account to a new one.

### 🧠 Why This Script Exists (The "Hybrid" Magic)

If you try to use the official YouTube API to migrate an account, Google will cut you off after about 200 "Likes" because of their strict daily quota limits (10,000 units/day).

This script uses a **Hybrid Approach** to bypass that completely:

1. **The Reader (Official API):** It logs into your OLD account using the official Google API to perfectly read 100% of your data (including non-music videos, tutorials, memes, etc.). *Reading costs almost zero quota.*
2. **The Writer (Browser Cookies):** It logs into your NEW account by mimicking your web browser via `ytmusicapi`. *Writing this way costs ZERO quota,* allowing you to transfer thousands of items in one sitting.

---

## 🛠️ Prerequisites

Before you begin, you need to have **Python** installed on your computer.

1. Download Python from [python.org](https://www.python.org/downloads/).
2. **IMPORTANT FOR WINDOWS USERS:** When running the installer, make sure to check the box that says **"Add Python to PATH"** before clicking Install.

You will also need a web browser. **Firefox is highly recommended** for this process, as Chrome/Edge encrypt their cookies in a way that makes extracting them annoying.

---

## 📦 Step 1: Environment Setup

1. **Download the project:** Clone this repository or download it as a ZIP and extract it.
2. **Open your terminal:** (Command Prompt on Windows, Terminal on Mac) and navigate to this folder.
3. **Create a Virtual Environment:** This creates an isolated bubble for the project so it doesn't mess with other Python apps on your computer.
```bash
python -m venv .venv

```


*(Note: If `python` doesn't work, try `py -m venv .venv` on Windows or `python3 -m venv .venv` on Mac).*
4. **Activate the Virtual Environment:**
* **Windows:** `.venv\Scripts\activate`
* **Mac/Linux:** `source .venv/bin/activate`


5. **Install Dependencies:**
```bash
pip install google-api-python-client google-auth-oauthlib google-auth-httplib2 ytmusicapi

```



---

## 🔑 Step 2: Get Old Account Credentials (The Reader)

We need official API access to read your old account.

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Log in with your **OLD** Google account.
3. Click **"Select a project"** at the top left and create a **New Project** (call it "YouTube Migrator").
4. In the top search bar, type **"YouTube Data API v3"** and click **Enable**.
5. Go to **APIs & Services > Credentials** (on the left menu).
6. Click **+ CREATE CREDENTIALS** -> **OAuth client ID**.
* *Note: If it asks you to configure a consent screen first, do so. Set it to "External", fill in dummy app names, add your email as a test user, and skip the scopes.*


7. For Application Type, choose **Desktop app**.
8. Click **Download JSON** (the little down arrow).
9. Move that file into this project folder and rename it to `client_secret.json`.
10. Open `config.py` in a text editor and ensure it points to this file:
```python
CLIENT_SECRET_FILE = "./client_secret.json"

```



---

## 🍪 Step 3: Get New Account Cookies (The Writer)

We need to extract your session data so the script can act as "you" on the new account.

1. Open **Firefox** (Use a Private Window to ensure no accounts are mixed up).
2. Go to [music.youtube.com](https://music.youtube.com) and log into your **NEW** account.
3. Press `F12` to open Developer Tools and click the **Network** tab.
4. In the filter box at the top of the Network tab, type `browse`.
5. In the YouTube Music window, click on **Library** on the left menu.
6. A request named `browse?prettyPrint=false` (or similar) will pop up in the Network tab.
7. **Right-click** that `browse` request -> Hover over **Copy** -> Click **Copy Request Headers**.
8. Go back to your terminal (ensure your `.venv` is still active) and run:
```bash
ytmusicapi browser

```


9. Follow the prompts: Paste the giant block of text you copied, press `Enter`, type `Ctrl+Z` (or `Ctrl+D` on Mac), and press `Enter` again.
10. When it asks for a filename, save it exactly as: **`new_headers.json`**.

---

## 🚀 Step 4: Run the Migration

If you are migrating to a brand-new account, ensure the file `migrated_likes.txt` is **empty or deleted**. (The script uses this file as a memory bank so it can resume progress if you close it, preventing duplicate work).

Run the script:

```bash
python transfer_master.py

```

**What will happen:**

1. A browser window will pop up asking you to log into Google. **Log into your OLD account here** and grant it permissions. (This creates a `token_old.pickle` file so you never have to log in again).
2. The script will look at your new account, figure out what's missing, and start migrating your Likes, Subscriptions, and Playlists.
3. It purposely runs slowly (pausing for 1.5 to 3.5 seconds between actions) to mimic human behavior and avoid shadow-bans. Let it run in the background!

---

## 🛑 Troubleshooting & Important Notes

* **I stopped the script halfway, do I have to start over?**
No! The script has "Resume Logic." Just run it again. It will check `migrated_likes.txt` and your new account to skip everything it already finished.
* **I want to migrate to a THIRD account now.**
You must delete `migrated_likes.txt` first. Otherwise, the script will think it already transferred your videos and will skip them. Generate a new `new_headers.json` for the third account and run the script.
* **Some videos say "Skipping (Video is Private/Deleted)"**
Normal. The script ignores dead links from your old account so it doesn't crash.
* **Why did it skip my "Episodes for Later" or "Liked Music" playlists?**
YouTube automatically generates these system playlists. The script ignores them because they cannot be manually duplicated.