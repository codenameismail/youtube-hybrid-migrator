"""Step 1: liked videos / liked songs."""
import config
import util


def run(old_api, new_music):
    print("\n[LIKES] Reading liked videos from the OLD account...")
    old_likes = old_api.list_items("LL")
    if not old_likes:
        print("No liked videos found.")
        return
    print(f"Found {len(old_likes)} liked videos.")

    already = util.read_set(config.LIKES_MEMORY)
    try:
        liked = new_music.get_liked_songs(limit=None)
        already |= {t["videoId"]
                    for t in liked.get("tracks", []) if t.get("videoId")}
    except Exception as e:
        print(
            f"Couldn't read existing likes on the NEW account ({e}). Using local memory only.")

    # Oldest first, so the most recent like ends up on top of the new account's list.
    old_likes.reverse()

    liked_now = skipped = failed = 0
    for i, video in enumerate(old_likes, 1):
        tag = f"[{i}/{len(old_likes)}]"
        if video["id"] in already:
            skipped += 1
            continue
        try:
            new_music.rate_song(video["id"], "LIKE")
            util.append_line(config.LIKES_MEMORY, video["id"])
            liked_now += 1
            print(f"{tag} Liked: {video['title']}")
            util.pause()
        except Exception as e:
            failed += 1
            print(f"{tag} Failed: {video['title']} - {e}")

    print(
        f"[LIKES] Done. Newly liked: {liked_now}, already done: {skipped}, failed: {failed}.")
