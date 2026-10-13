# Troubleshooting

**"Setup isn't finished yet: Missing secrets/..."**
You haven't created `secrets/client_secret.json` (SETUP Part 2) or `secrets/new_headers.json` (SETUP Part 3).

**`ModuleNotFoundError` / "Missing dependencies"**
The virtual environment isn't active. Activate it (see SETUP Part 1) and run `pip install -r requirements.txt`.

**Google says "Access blocked" or "access_denied" when logging in**
The account isn't listed as a Test user. In Google Cloud Console, open Google Auth Platform, then Audience, and add **both** accounts. On the warning page click Advanced, then continue.

**Asked to log in again after a few days**
Normal for apps in Testing mode. Refresh tokens expire after about a week. Just log in again.

**Authentication errors or `401`/`403` from YouTube Music**
Your cookies expired. Redo SETUP Part 3 to replace `secrets/new_headers.json`.

**`quotaExceeded` / "Daily quota used up"**
Not an error, just the official API's daily limit. Run the same command the next day (after midnight Pacific time). Progress is saved.

**A YouTube-only playlist still shows in YouTube Music**
1. Check it's marked `YOUTUBE` in `state/playlist_types.txt`.
2. Fully close and reopen the YouTube Music app, since it caches.
3. Run `python migrate.py playlists` again. It detects playlists that appear in YouTube Music but should be YouTube-only, and offers to rebuild them.

**I marked a playlist wrong and already ran it**
- MUSIC to YOUTUBE: change the word and re-run. The tool offers to replace it.
- YOUTUBE to MUSIC: delete that playlist on the NEW account, change the word to MUSIC, and re-run.

**Some videos were skipped**
Private and deleted videos can't be copied. They're skipped on purpose. Takeout shows what they were.

**Likes and subscriptions are slow**
Deliberate: random pauses of 1.5 to 3.5 seconds avoid triggering Google's anti-automation. Roughly 40 minutes per 1,000 likes. You can stop with Ctrl+C and resume any time.

**The browser doesn't open, or "port 8080 in use"**
Close whatever uses port 8080, or change `port=8080` in `auth.py`.

**Migrating to a different account later**
1. `python migrate.py reset`
2. Delete `secrets/token_new.json`
3. Redo SETUP Part 3 with the new account
4. Add the new account as a Test user in Google Cloud

**A playlist with `<` or `>` in its title or description**
YouTube rejects those characters, so they're removed from the copy.

**Python 3.10 `FutureWarning`**
Harmless. Upgrade to Python 3.11+ to remove it.
