"""Step 2: channel subscriptions."""
import config
import util


def run(old_api, new_music):
    print("\n[SUBS] Reading subscriptions from the OLD account...")
    old_subs = old_api.list_subscriptions()
    if not old_subs:
        print("No subscriptions found.")
        return
    print(f"Found {len(old_subs)} channels.")

    # YouTube Music only lists music artists, so a local memory file covers the rest.
    already = util.read_set(config.SUBS_MEMORY)
    try:
        subs = new_music.get_library_subscriptions(limit=None) or []
        already |= {s["browseId"] for s in subs if s.get("browseId")}
    except Exception as e:
        print(f"Couldn't read existing subscriptions on the NEW account ({e}). Using local memory only.")

    old_subs.reverse()

    done = skipped = failed = 0
    for i, sub in enumerate(old_subs, 1):
        tag = f"[{i}/{len(old_subs)}]"
        if sub["id"] in already:
            skipped += 1
            continue
        try:
            new_music.subscribe_artists([sub["id"]])
            util.append_line(config.SUBS_MEMORY, sub["id"])
            done += 1
            print(f"{tag} Subscribed: {sub['title']}")
            util.pause()
        except Exception as e:
            failed += 1
            print(f"{tag} Failed: {sub['title']} - {e}")

    print(f"[SUBS] Done. Newly subscribed: {done}, already done: {skipped}, failed: {failed}.")
