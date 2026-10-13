# YouTube Ultimate Migrator

Copy everything you *consume* on YouTube from an old Google account to a new one: **liked videos, liked songs, subscriptions, and playlists**. It is built for the case Google doesn't cover: you can't transfer this data between accounts, and Takeout is only a backup.

The part most tools get wrong is playlists. This one keeps **YouTube playlists on YouTube only** and **music playlists in YouTube Music**, instead of dumping everything into YouTube Music.

---

## What it does

| Migrated | How |
|---|---|
| Liked videos / liked songs | Read via the official API, re-liked through YouTube Music (no quota cost) |
| Subscriptions | Read via the official API, re-subscribed through YouTube Music (no quota cost) |
| Playlists you created | Rebuilt as **MUSIC** (YouTube Music) or **YOUTUBE** (YouTube only), keeping order, privacy and description |

**Not migrated** (no way to read or write it, or out of scope): Watch Later, playlists you *saved* from other people, albums/songs saved to your YouTube Music library without liking, uploaded songs/videos, watch and search history, notification-bell settings, comments. Your Google Takeout export is the only copy of those. See [How it works](docs/HOW_IT_WORKS.md#what-isnt-migrated).

## How it works in 30 seconds

- **Reader: official YouTube API** on the OLD account. It sees everything, including non-music videos. Reading costs about 1 quota unit.
- **Writer for likes, subs and music playlists: YouTube Music via browser cookies** (`ytmusicapi`) on the NEW account. No quota.
- **Writer for YouTube-only playlists: the official API** on the NEW account. Playlists created this way do not appear in YouTube Music (this was verified by hand: the same two videos stay hidden when created through YouTube, but show up when created through YouTube Music). It costs 50 quota units per write against a 10,000/day limit, so big libraries take a few days. The tool tracks quota and resumes where it stopped.

Details and quota maths: [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md).

---

## Quick start

Full instructions with every click: **[docs/SETUP.md](docs/SETUP.md)**. Short version:

```bash
python -m venv .venv
# Windows (cmd/PowerShell): .venv\Scripts\activate    Git Bash: source .venv/Scripts/activate
# Mac/Linux:                source .venv/bin/activate
pip install -r requirements.txt
```

Then, once:

1. Put your Google Cloud OAuth file at `secrets/client_secret.json` (SETUP, Part 2).
2. Save your NEW account's browser cookies to `secrets/new_headers.json` (SETUP, Part 3).

Run:

```bash
python migrate.py
```

It shows both account names and asks you to confirm before writing anything. Then it does likes, subscriptions, and playlists in that order.

**Playlists pause once for your review.** The first time it reaches playlists, it writes `state/playlist_types.txt` with a MUSIC/YOUTUBE guess for each playlist (based on how many of its videos are in YouTube's Music category). Fix any wrong guesses in Notepad, save, and run `python migrate.py playlists`.

### Commands

| Command | What it does |
|---|---|
| `python migrate.py` | Likes, then subscriptions, then playlists |
| `python migrate.py likes` | Only likes |
| `python migrate.py subs` | Only subscriptions |
| `python migrate.py playlists` | Only playlists |
| `python migrate.py playlists --only "My Playlist"` | One playlist only. Do this first as a test |
| `python migrate.py playlists --auto` | Accept the MUSIC/YOUTUBE guesses without pausing |
| `python migrate.py reset` | Forget progress (before migrating to a different account) |
| `--yes` (any command) | Skip the account confirmation |

Everything is **resumable**: stop any time (Ctrl+C), run the same command again, and it skips what's done.

---

## Before you delete the old account

1. Compare counts on both accounts: liked videos, subscriptions, number of playlists, and the video count of each playlist.
2. Check the YouTube-only playlists do **not** show in YouTube Music (fully close and reopen the app).
3. Keep your Google Takeout archive permanently.
4. Remember the list of things that can't be migrated above.
5. Consider simply abandoning the old account instead of deleting it. Deletion is only recoverable for a short window.

## Safety and privacy

- `secrets/` holds your OAuth client, login tokens and **browser cookies. The cookie file is equivalent to a password** for the NEW account. `state/` holds your personal viewing data. Both are in `.gitignore`. **Never commit or share them.** Run `git status` before every commit.
- When you're finished, delete `secrets/new_headers.json` and revoke the app at <https://myaccount.google.com/permissions> on both accounts.
- This project uses [`ytmusicapi`](https://github.com/sigma67/ytmusicapi), an unofficial library that talks to YouTube Music the way the website does. It can break when YouTube changes, and automated activity can in principle upset Google. The tool is deliberately slow (random 1.5 to 3.5 second pauses). Use it at your own risk. This project is not affiliated with Google or YouTube.

## Project layout

```
migrate.py          entry point (all commands)
likes.py            step 1: liked videos / songs
subscriptions.py    step 2: subscriptions
playlists.py        step 3: playlists (MUSIC vs YOUTUBE)
youtube_api.py      official YouTube Data API wrapper
auth.py             Google OAuth login (tokens saved and auto-refreshed)
quota.py            daily quota tracking across runs
config.py, util.py  settings and helpers
tests/              offline tests (no accounts needed)
docs/               SETUP, HOW_IT_WORKS, TROUBLESHOOTING
secrets/  state/    created at runtime, git-ignored
```

## Development

```bash
python -m unittest discover -s tests -v
```

The tests use fake accounts, so they need no login or internet.

## Docs

- [Setup guide](docs/SETUP.md)
- [How it works](docs/HOW_IT_WORKS.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Changelog](CHANGELOG.md)
