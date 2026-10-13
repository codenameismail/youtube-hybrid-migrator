# How it works

## Why two different "writers"

| | Official YouTube API | YouTube Music via cookies (`ytmusicapi`) |
|---|---|---|
| Sees non-music videos | Yes | Partly |
| Quota | 10,000 units/day. Reads ~1, writes 50 | None |
| Playlists created appear in YouTube Music | **No** | **Yes** |
| Stability | Official | Unofficial, can break |

So the tool reads everything with the official API, writes cheap things (likes, subscriptions) and music playlists through YouTube Music, and writes YouTube-only playlists through the official API.

## The playlist problem this solves

Early versions created *every* playlist through YouTube Music. Playlists made that way show up in YouTube Music's library, even if they contain only ordinary videos (tutorials, podcasts, vlogs). The author tested this by hand: the same two videos, as a playlist created on youtube.com, stayed out of YouTube Music, while the copy made by the old script appeared there.

The fix is to create each playlist the right way for its purpose:

- **MUSIC**: created through YouTube Music. Shows up there.
- **YOUTUBE**: created through the official API. Stays on YouTube.

### How a playlist gets its type

Playlists on the old account carry no label saying which kind they were. The tool **guesses**: it checks the category of every video in the playlist and marks it MUSIC when at least 70% are in YouTube's "Music" category (`MUSIC_THRESHOLD` in `config.py`), otherwise YOUTUBE. The guesses go in `state/playlist_types.txt` so you can correct them before anything is written.

Each line looks like `YOUTUBE | My Playlist | 0/20 videos are music`. Change only the first word.

### Fixing playlists that were made the wrong way

If a playlist marked YOUTUBE already exists in the NEW account's YouTube Music library and wasn't created by this tool's official-API path, it's the "wrong way" case. The tool lists these, asks you to type `GO`, deletes them from the NEW account, and rebuilds them through the official API. The OLD account is never modified.

## Steps

1. **Likes.** Reads `LL` (the Liked videos list) from the OLD account, then likes each video on the NEW one, oldest first so the most recent like ends up on top.
2. **Subscriptions.** Subscribes to each channel on the NEW account.
3. **Playlists.** Reads each playlist you created, then syncs it as MUSIC or YOUTUBE. Order, privacy (public/unlisted/private) and description are preserved. Private and deleted videos are skipped.

## Quota maths

The daily default is 10,000 units. The tool budgets 9,500 (`DAILY_QUOTA_BUDGET`) to leave a margin. Creating a playlist and adding one video each cost 50 units, so roughly **190 writes per day**. For example, 5 playlists with 300 videos in total is 305 writes, about 15,250 units, about **2 days**.

Usage is saved in `state/quota.json` and resets at midnight Pacific time, so you can re-run safely on the same day. Only YOUTUBE playlists use quota. Likes, subscriptions and MUSIC playlists don't.

The tool prints an estimate before it starts. If you hit the real limit, it stops cleanly. Run the same command the next day.

## Resume logic

| Item | How "already done" is detected |
|---|---|
| Likes | `state/migrated_likes.txt` plus the NEW account's existing liked songs |
| Subscriptions | `state/migrated_subs.txt` plus the NEW account's music subscriptions (YouTube Music only lists music artists, which is why the file is needed) |
| MUSIC playlists | Matched by title in the NEW account's library, then only missing tracks are added |
| YOUTUBE playlists | Matched by title via the official API, then only missing videos are added |

Playlists are matched by **title**. Two playlists with identical titles on the old account will be merged into one.

## Safety checks

- Before writing, both account names are shown for confirmation.
- If the YouTube Music cookies and the official-API login names differ, you're asked to confirm again.
- Nothing is deleted without typing `GO`.
- Large playlists are added in batches of 50 so one failed request doesn't lose the lot.

## What isn't migrated

| Item | Why |
|---|---|
| Watch Later | The official API can't read it. Takeout has it as a CSV, so you can add those videos to a normal playlist by hand |
| Playlists saved from other people | Only playlists *you created* are read |
| Albums/songs added to the YouTube Music library without liking | Not read |
| Uploaded songs and your own channel's videos | Can't be moved between accounts |
| Watch and search history | Can't be imported |
| Notification bell settings, subscription order | No API |
| Comments | Can't be moved |
