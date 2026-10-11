#!/usr/bin/env python3
"""YouTube Ultimate Migrator: copy likes, subscriptions and playlists to a new account.

    python migrate.py              # everything, in order
    python migrate.py likes        # or: subs, playlists
    python migrate.py reset        # forget progress (before migrating to a different account)
"""
import argparse
import sys

try:
    from ytmusicapi import YTMusic
except ImportError:
    sys.exit("Missing dependencies. Activate your virtual environment, then run:\n"
             "    pip install -r requirements.txt")

import config
import likes
import playlists
import subscriptions
import util
from auth import authenticate_youtube
from quota import QuotaTracker
from youtube_api import YouTubeAPI


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Copy YouTube likes, subscriptions and playlists "
                                            "from an OLD Google account to a NEW one.")
    p.add_argument("step", nargs="?", default="all",
                   choices=["all", "likes", "subs", "playlists", "reset"],
                   help="what to do (default: all)")
    p.add_argument("--only", metavar="TITLE",
                   help="playlists: process just this one playlist (good for a first test)")
    p.add_argument("--auto", action="store_true",
                   help="playlists: accept the MUSIC/YOUTUBE guesses without pausing to review them")
    p.add_argument("--yes", action="store_true",
                   help="skip the 'is this the right account?' confirmation")
    return p.parse_args(argv)


def preflight():
    problems = []
    if not config.CLIENT_SECRET_FILE.exists():
        problems.append(f"Missing {config.CLIENT_SECRET_FILE.relative_to(config.ROOT)}  (docs/SETUP.md, Part 2)")
    if not config.NEW_HEADERS.exists():
        problems.append(f"Missing {config.NEW_HEADERS.relative_to(config.ROOT)}  (docs/SETUP.md, Part 3)")
    if problems:
        print("Setup isn't finished yet:")
        for line in problems:
            print("  - " + line)
        sys.exit(1)


def reset():
    files = [f for f in config.STATE_DIR.glob("*") if f.is_file()] if config.STATE_DIR.exists() else []
    if not files:
        print("No progress files to clear.")
        return
    print("This clears the progress memory (likes, subs, playlist types, quota). Your accounts are untouched:")
    for f in files:
        print(f"   {f.name}")
    if input("Type RESET to continue: ").strip() == "RESET":
        for f in files:
            f.unlink()
        print("Cleared.")
    else:
        print("Cancelled.")


def new_account_name(new_music):
    try:
        return new_music.get_account_info().get("accountName")
    except Exception:
        return None


def confirm_accounts(old_api, new_name):
    old_name = old_api.whoami()
    print("\nSource (OLD, read only):      " + (old_name or "(couldn't read the name)"))
    print("Destination (NEW, written to): " + (new_name or "(couldn't read the name)"))
    if old_name and new_name and old_name.strip().lower() == new_name.strip().lower():
        print("WARNING: both accounts have the same name. Make sure they are really different accounts.")
    return input("Is that right? Type YES to continue: ").strip().upper() == "YES"


def main(argv=None):
    args = parse_args(argv)
    # Video titles often contain emoji; never crash on a console that can't print them.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    config.ensure_dirs()

    if args.step == "reset":
        return reset()

    preflight()
    old_api = YouTubeAPI(authenticate_youtube(config.CLIENT_SECRET_FILE, config.OLD_TOKEN, "OLD"))
    try:
        new_music = YTMusic(str(config.NEW_HEADERS))
    except Exception as e:
        sys.exit(f"Couldn't use {config.NEW_HEADERS.name}: {e}\n"
                 "Re-create it (docs/SETUP.md, Part 3). Cookies expire.")
    new_name = new_account_name(new_music)

    if not args.yes and not confirm_accounts(old_api, new_name):
        print("Cancelled.")
        return

    cache = {}

    def get_new_api():
        if "api" not in cache:
            api = YouTubeAPI(authenticate_youtube(config.CLIENT_SECRET_FILE, config.NEW_TOKEN, "NEW"))
            official_name = api.whoami()
            if (not args.yes and new_name and official_name
                    and official_name.strip().lower() != new_name.strip().lower()):
                print(f"\nYouTube Music cookies are for '{new_name}' but you just logged in as '{official_name}'.")
                if input("Are these the same NEW account? Type YES to continue: ").strip().upper() != "YES":
                    sys.exit("Cancelled. Log in with the same NEW account in both places.")
            cache["api"] = api
        return cache["api"]

    if args.step in ("all", "likes"):
        likes.run(old_api, new_music)
    if args.step in ("all", "subs"):
        subscriptions.run(old_api, new_music)
    if args.step in ("all", "playlists"):
        playlists.run(old_api, new_music, get_new_api, QuotaTracker(),
                      only=args.only, auto=args.auto)

    print("\nFinished. Compare counts on both accounts before deleting anything (see README).")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped. Progress is saved; run the same command again to resume.")
