"""Step 3: playlists.

YouTube and YouTube Music treat playlists differently depending on HOW they are created:
  * created through the YouTube Music endpoint  -> shows up in YouTube Music's library
  * created through the official YouTube API    -> YouTube only

So each playlist is tagged MUSIC or YOUTUBE (playlist_types.txt) and rebuilt the matching way.
"""
import math
import time

import config
import util
from quota import QuotaStop
from youtube_api import is_quota_error

SKIP_IDS = {"LL", "WL", "LM", "SEAMWL"}
VALID_TYPES = ("MUSIC", "YOUTUBE")


# ---------------------------------------------------------------- types file
def guess_type(music, total):
    return "MUSIC" if total and music / total >= config.MUSIC_THRESHOLD else "YOUTUBE"


def build_types_file(old_api, path=None):
    """Write playlist_types.txt with a MUSIC/YOUTUBE guess for every old playlist."""
    path = path or config.PLAYLIST_TYPES
    lines = [
        "# Each line:  TYPE | playlist title | note",
        "# TYPE must be MUSIC (shows in YouTube Music) or YOUTUBE (YouTube only).",
        "# The tool GUESSED from how many videos are in YouTube's Music category.",
        "# Change the first word of any line that is wrong. Don't edit the titles.",
        "# Don't delete the note at the end of each line.",
        "",
    ]
    print("\n[PLAYLISTS] Looking at your playlists to guess MUSIC vs YOUTUBE...")
    for p in old_api.list_playlists():
        if p["id"] in SKIP_IDS:
            continue
        ids = [v["id"] for v in old_api.list_items(p["id"])]
        if not ids:
            lines.append(f"YOUTUBE | {p['title']} | empty")
            continue
        music = old_api.music_count(ids)
        kind = guess_type(music, len(ids))
        lines.append(f"{kind} | {p['title']} | {music}/{len(ids)} videos are music")
        print(f"  {kind:8} {p['title']}  ({music}/{len(ids)} music)")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_types(path=None):
    path = path or config.PLAYLIST_TYPES
    types = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "|" not in line:
                continue
            kind, rest = line.split("|", 1)
            title = rest.rsplit("|", 1)[0].strip() if "|" in rest else rest.strip()
            types[title] = kind.strip().upper()
    return types


# ------------------------------------------------------------- music playlists
def _add_in_batches(new_music, playlist_id, video_ids):
    total = len(video_ids)
    for start in range(0, total, config.BATCH_SIZE):
        batch = video_ids[start:start + config.BATCH_SIZE]
        try:
            new_music.add_playlist_items(playlist_id, batch)
            print(f"   added {min(start + config.BATCH_SIZE, total)}/{total}")
        except Exception as e:
            print(f"   batch starting at {start + 1} failed: {e}")
        util.pause()


def _sync_music(new_music, plan, library):
    for p, ids in plan:
        title = util.clean_text(p["title"])
        print(f"\n[MUSIC] {title}")
        try:
            if title in library:
                pid = library[title]
                tracks = new_music.get_playlist(pid, limit=None).get("tracks", [])
                have = {t["videoId"] for t in tracks if t.get("videoId")}
                missing = [v for v in ids if v not in have]
                if not missing:
                    print("   already complete")
                    continue
                print(f"   exists; adding {len(missing)} missing tracks")
            else:
                privacy = p["privacy"].upper()
                if privacy not in ("PUBLIC", "PRIVATE", "UNLISTED"):
                    privacy = "PRIVATE"
                pid = new_music.create_playlist(title, util.clean_text(p["description"]),
                                                privacy_status=privacy)
                if not isinstance(pid, str):
                    raise RuntimeError(f"unexpected response: {pid}")
                library[title] = pid
                util.pause()
                missing = ids
                print(f"   created ({privacy}); adding {len(missing)} tracks")
            _add_in_batches(new_music, pid, missing)
        except Exception as e:
            print(f"   failed: {e}")


# ----------------------------------------------------------- youtube playlists
def _sync_youtube(new_api, plan, quota):
    existing = {p["title"]: p["id"] for p in new_api.list_playlists()}
    for p, ids in plan:
        title = util.clean_text(p["title"])
        print(f"\n[YOUTUBE] {title}")

        if title in existing:
            pid = existing[title]
            try:
                have = {v["id"] for v in new_api.list_items(pid)}
            except Exception as e:
                print(f"   couldn't read existing playlist: {e}")
                continue
            missing = [v for v in ids if v not in have]
            if not missing:
                print("   already complete")
                continue
            print(f"   exists; adding {len(missing)} missing videos")
        else:
            quota.require(config.WRITE_COST)
            try:
                pid = new_api.create_playlist(p["title"], p["description"], p["privacy"])
            except Exception as e:
                if is_quota_error(e):
                    raise QuotaStop() from e
                print(f"   couldn't create playlist: {e}")
                continue
            quota.spend(config.WRITE_COST)
            existing[title] = pid
            util.append_line(config.YT_PLAYLISTS_CREATED, title)
            missing = ids
            print(f"   created ({p['privacy']}); adding {len(missing)} videos")

        for n, vid in enumerate(missing, 1):
            quota.require(config.WRITE_COST)
            try:
                new_api.add_video(pid, vid)
                print(f"   {n}/{len(missing)}")
            except Exception as e:
                if is_quota_error(e):
                    raise QuotaStop() from e
                print(f"   skipped {vid}: {e}")
            quota.spend(config.WRITE_COST)
            time.sleep(0.3)


# ------------------------------------------------------------------ entry point
def run(old_api, new_music, get_new_api, quota, only=None, auto=False, ask=input):
    if not config.PLAYLIST_TYPES.exists():
        build_types_file(old_api)
        if not auto:
            print(f"\nWrote {config.PLAYLIST_TYPES}.")
            print("Open it, fix any wrong guesses, save it, then run:  python migrate.py playlists")
            return
        print("\n--auto given: using the guesses as they are.")

    types = read_types()
    bad = {t: k for t, k in types.items() if k not in VALID_TYPES}
    if bad:
        print("These lines in playlist_types.txt need MUSIC or YOUTUBE at the start:")
        for t, k in bad.items():
            print(f"   '{k}' | {t}")
        return

    wanted = set(types)
    if only:
        if only not in types:
            print(f"'{only}' isn't in playlist_types.txt. Check the spelling.")
            return
        wanted = {only}

    # ---- read the old account
    plan_yt, plan_music, unknown = [], [], []
    for p in old_api.list_playlists():
        if p["id"] in SKIP_IDS:
            continue
        if p["title"] not in types:
            unknown.append(p["title"])
            continue
        if p["title"] not in wanted:
            continue
        try:
            ids = [v["id"] for v in old_api.list_items(p["id"])]
        except Exception as e:
            print(f"Couldn't read '{p['title']}': {e}")
            continue
        if not ids:
            print(f"'{p['title']}' is empty or only has unavailable videos. Skipping.")
            continue
        (plan_yt if types[p["title"]] == "YOUTUBE" else plan_music).append((p, ids))
    if unknown:
        print("Not in playlist_types.txt (skipped). Delete the file to re-scan: " + ", ".join(unknown))

    # ---- what already exists on the new account
    library = {pl["title"]: pl["playlistId"]
               for pl in (new_music.get_library_playlists(limit=None) or [])}
    created = util.read_set(config.YT_PLAYLISTS_CREATED)
    yt_titles = {util.clean_text(p["title"]) for p, _ in plan_yt}
    # YouTube-only playlists that are visible in YouTube Music were made the wrong way
    # (e.g. by an older version of this tool). They must be rebuilt.
    to_delete = [(t, pid) for t, pid in library.items() if t in yt_titles and t not in created]

    writes = len(plan_yt) + sum(len(ids) for _, ids in plan_yt)
    units = writes * config.WRITE_COST
    days = max(1, math.ceil(units / config.DAILY_QUOTA_BUDGET)) if plan_yt else 0
    print(f"\nMUSIC playlists to sync:   {len(plan_music)}  (via YouTube Music, no quota)")
    print(f"YOUTUBE playlists to sync: {len(plan_yt)}  (via official API)")
    if plan_yt:
        print(f"Quota estimate: about {units:,} units, i.e. ~{days} day(s). "
              f"Left today: {quota.remaining:,}.")
    if to_delete:
        print("\nThese playlists on the NEW account show in YouTube Music but should be YouTube-only.")
        print("They will be DELETED there and rebuilt (the OLD account is never changed):")
        for t, _ in to_delete:
            print(f"   - {t}")
    if not plan_yt and not plan_music:
        print("Nothing to do.")
        return
    if ask("\nType GO to continue: ").strip() != "GO":
        print("Cancelled. Nothing was changed.")
        return

    # ---- do it
    for t, pid in to_delete:
        try:
            new_music.delete_playlist(pid)
            library.pop(t, None)
            print(f"Deleted from YouTube Music: {t}")
        except Exception as e:
            print(f"Couldn't delete '{t}': {e}. Stopping so nothing ends up duplicated.")
            return
        util.pause()

    if plan_music:
        _sync_music(new_music, plan_music, library)

    if plan_yt:
        try:
            _sync_youtube(get_new_api(), plan_yt, quota)
            print("\n[PLAYLISTS] Done. YouTube-only playlists should NOT appear in YouTube Music.")
        except QuotaStop:
            print("\nDaily quota used up. Nothing is lost: run  python migrate.py playlists")
            print("again tomorrow (after midnight Pacific time) and it resumes where it stopped.")
