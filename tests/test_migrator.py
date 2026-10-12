"""Offline tests: fake accounts stand in for Google, so no login or internet is needed.

Run from the project folder:   python -m unittest discover -s tests -v
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
import likes  # noqa: E402
import playlists  # noqa: E402
import subscriptions  # noqa: E402
import util  # noqa: E402
from quota import QuotaStop, QuotaTracker  # noqa: E402


# ------------------------------------------------------------------ fakes
class FakeOldAPI:
    def __init__(self, playlist_defs=None, likes_=None, subs=None, music_ids=()):
        # playlist_defs: {title: (privacy, [video ids])}
        self.defs = playlist_defs or {}
        self.likes = likes_ or []
        self.subs = subs or []
        self.music_ids = set(music_ids)

    def list_playlists(self):
        return [{"id": f"PL{i}", "title": t, "description": f"about {t}", "privacy": priv}
                for i, (t, (priv, _)) in enumerate(self.defs.items())]

    def list_items(self, playlist_id):
        if playlist_id == "LL":
            return [{"id": v, "title": f"like {v}"} for v in self.likes]
        titles = list(self.defs)
        ids = self.defs[titles[int(playlist_id[2:])]][1]
        return [{"id": v, "title": f"vid {v}"} for v in ids]

    def list_subscriptions(self):
        return [{"id": c, "title": f"chan {c}"} for c in self.subs]

    def music_count(self, ids):
        return sum(1 for v in ids if v in self.music_ids)


class FakeMusic:
    def __init__(self, library=None, liked=(), subs=()):
        self.library = dict(library or {})          # title -> playlist id
        self.tracks = {}                            # playlist id -> [video ids]
        self.liked = set(liked)
        self.subs = set(subs)
        self.created, self.deleted, self.rated, self.subscribed = [], [], [], []

    def get_library_playlists(self, limit=None):
        return [{"title": t, "playlistId": p} for t, p in self.library.items()]

    def get_playlist(self, pid, limit=None):
        return {"tracks": [{"videoId": v} for v in self.tracks.get(pid, [])]}

    def create_playlist(self, title, description, privacy_status="PRIVATE"):
        pid = f"M-{title}"
        self.library[title] = pid
        self.tracks[pid] = []
        self.created.append((title, privacy_status))
        return pid

    def add_playlist_items(self, pid, video_ids):
        self.tracks[pid].extend(video_ids)

    def delete_playlist(self, pid):
        self.deleted.append(pid)
        self.library = {t: p for t, p in self.library.items() if p != pid}

    def get_liked_songs(self, limit=None):
        return {"tracks": [{"videoId": v} for v in self.liked]}

    def rate_song(self, vid, rating):
        self.rated.append(vid)

    def get_library_subscriptions(self, limit=None):
        return [{"browseId": c} for c in self.subs]

    def subscribe_artists(self, ids):
        self.subscribed.extend(ids)


class FakeNewAPI:
    def __init__(self, fail_after=None):
        self.playlists = {}      # id -> {"title","privacy","videos"}
        self.fail_after = fail_after
        self.writes = 0

    def _write(self):
        if self.fail_after is not None and self.writes >= self.fail_after:
            raise Exception("quotaExceeded")
        self.writes += 1

    def list_playlists(self):
        return [{"id": i, "title": p["title"], "description": "", "privacy": p["privacy"]}
                for i, p in self.playlists.items()]

    def list_items(self, pid):
        return [{"id": v, "title": v} for v in self.playlists[pid]["videos"]]

    def create_playlist(self, title, description, privacy):
        self._write()
        pid = f"Y{len(self.playlists)}"
        self.playlists[pid] = {"title": title, "privacy": privacy, "videos": []}
        return pid

    def add_video(self, pid, vid):
        self._write()
        self.playlists[pid]["videos"].append(vid)


# ------------------------------------------------------------------ base
class TempProject(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.patches = [
            mock.patch.object(config, "STATE_DIR", root / "state"),
            mock.patch.object(config, "LIKES_MEMORY", root / "state" / "likes.txt"),
            mock.patch.object(config, "SUBS_MEMORY", root / "state" / "subs.txt"),
            mock.patch.object(config, "PLAYLIST_TYPES", root / "state" / "types.txt"),
            mock.patch.object(config, "YT_PLAYLISTS_CREATED", root / "state" / "created.txt"),
            mock.patch.object(config, "QUOTA_FILE", root / "state" / "quota.json"),
            mock.patch.object(util, "pause", lambda: None),
            mock.patch("time.sleep", lambda s: None),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def write_types(self, text):
        config.PLAYLIST_TYPES.parent.mkdir(parents=True, exist_ok=True)
        config.PLAYLIST_TYPES.write_text(text, encoding="utf-8")


# ------------------------------------------------------------------ tests
class QuotaTests(TempProject):
    def test_persists_and_resets_next_day(self):
        q = QuotaTracker(today=lambda: "2026-01-01")
        q.spend(100)
        self.assertEqual(QuotaTracker(today=lambda: "2026-01-01").used, 100)
        self.assertEqual(QuotaTracker(today=lambda: "2026-01-02").used, 0)

    def test_require_stops_at_budget(self):
        q = QuotaTracker(budget=100, today=lambda: "d")
        q.spend(50)
        q.require(50)
        q.spend(50)
        with self.assertRaises(QuotaStop):
            q.require(50)


class TypesFileTests(TempProject):
    def test_guess(self):
        self.assertEqual(playlists.guess_type(7, 10), "MUSIC")
        self.assertEqual(playlists.guess_type(6, 10), "YOUTUBE")
        self.assertEqual(playlists.guess_type(0, 0), "YOUTUBE")

    def test_build_and_read_round_trip_with_pipe_in_title(self):
        old = FakeOldAPI({"Gym": ("private", ["m1", "m2"]), "A | B": ("public", ["v1"])},
                         music_ids=["m1", "m2"])
        playlists.build_types_file(old)
        self.assertEqual(playlists.read_types(), {"Gym": "MUSIC", "A | B": "YOUTUBE"})


class PlaylistFlowTests(TempProject):
    def setUp(self):
        super().setUp()
        self.old = FakeOldAPI({"Gym": ("private", ["m1", "m2"]),
                               "Vlogs": ("public", ["v1", "v2", "v3"])})
        self.write_types("MUSIC | Gym | x\nYOUTUBE | Vlogs | x\n")

    def run_flow(self, music, api, quota=None, answer="GO", **kw):
        quota = quota or QuotaTracker(today=lambda: "d")
        playlists.run(self.old, music, lambda: api, quota, ask=lambda _: answer, **kw)

    def test_each_playlist_is_built_the_right_way(self):
        music, api = FakeMusic(), FakeNewAPI()
        self.run_flow(music, api)
        self.assertEqual(music.created, [("Gym", "PRIVATE")])           # music playlist via YT Music
        self.assertNotIn("Vlogs", music.library)                          # YouTube one NOT via YT Music
        vlogs = next(p for p in api.playlists.values() if p["title"] == "Vlogs")
        self.assertEqual(vlogs["videos"], ["v1", "v2", "v3"])
        self.assertEqual(vlogs["privacy"], "public")                      # privacy preserved

    def test_second_run_changes_nothing(self):
        music, api = FakeMusic(), FakeNewAPI()
        self.run_flow(music, api)
        writes, created = api.writes, list(music.created)
        self.run_flow(music, api)
        self.assertEqual(api.writes, writes)
        self.assertEqual(music.created, created)

    def test_wrongly_made_youtube_playlist_is_replaced(self):
        music = FakeMusic(library={"Vlogs": "OLDID"})   # shows in YT Music, wasn't made by the API
        api = FakeNewAPI()
        self.run_flow(music, api)
        self.assertEqual(music.deleted, ["OLDID"])
        self.assertEqual(len(api.playlists), 1)

    def test_declining_changes_nothing(self):
        music, api = FakeMusic(library={"Vlogs": "OLDID"}), FakeNewAPI()
        self.run_flow(music, api, answer="no")
        self.assertEqual((music.deleted, music.created, api.playlists), ([], [], {}))

    def test_quota_stop_then_resume_without_duplicates(self):
        music = FakeMusic()
        api = FakeNewAPI()
        q = QuotaTracker(budget=100, today=lambda: "d")                  # create + 1 video only
        self.run_flow(music, api, quota=q)
        self.assertEqual(len(api.playlists), 1)
        self.assertEqual(next(iter(api.playlists.values()))["videos"], ["v1"])
        q2 = QuotaTracker(budget=9500, today=lambda: "next")             # "tomorrow"
        self.run_flow(music, api, quota=q2)
        self.assertEqual(len(api.playlists), 1)
        self.assertEqual(next(iter(api.playlists.values()))["videos"], ["v1", "v2", "v3"])

    def test_real_quota_error_from_google_stops_cleanly(self):
        music, api = FakeMusic(), FakeNewAPI(fail_after=2)               # Google says no after 2 writes
        self.run_flow(music, api)                                         # must not raise
        self.assertEqual(api.writes, 2)

    def test_only_limits_to_one_playlist(self):
        music, api = FakeMusic(), FakeNewAPI()
        self.run_flow(music, api, only="Vlogs")
        self.assertEqual(music.created, [])
        self.assertEqual(len(api.playlists), 1)

    def test_bad_type_word_is_reported_and_nothing_runs(self):
        self.write_types("MUSC | Gym | x\nYOUTUBE | Vlogs | x\n")
        music, api = FakeMusic(), FakeNewAPI()
        self.run_flow(music, api)
        self.assertEqual((music.created, api.playlists), ([], {}))

    def test_first_run_writes_file_and_stops_for_review(self):
        config.PLAYLIST_TYPES.unlink()
        music, api = FakeMusic(), FakeNewAPI()
        self.run_flow(music, api)
        self.assertTrue(config.PLAYLIST_TYPES.exists())
        self.assertEqual((music.created, api.playlists), ([], {}))

    def test_auto_accepts_guesses_and_continues(self):
        config.PLAYLIST_TYPES.unlink()
        music, api = FakeMusic(), FakeNewAPI()
        self.run_flow(music, api, auto=True)
        self.assertEqual(len(api.playlists), 2)   # no music_ids -> both guessed YOUTUBE


class LikesAndSubsTests(TempProject):
    def test_likes_skip_done_and_remember(self):
        old = FakeOldAPI(likes_=["a", "b", "c"])          # newest first, as YouTube returns them
        music = FakeMusic(liked=["a"])
        util.append_line(config.LIKES_MEMORY, "b")
        likes.run(old, music)
        self.assertEqual(music.rated, ["c"])
        self.assertIn("c", util.read_set(config.LIKES_MEMORY))

    def test_likes_oldest_first(self):
        old = FakeOldAPI(likes_=["new", "mid", "old"])
        music = FakeMusic()
        likes.run(old, music)
        self.assertEqual(music.rated, ["old", "mid", "new"])

    def test_subs_use_memory_for_non_music_channels(self):
        old = FakeOldAPI(subs=["c1", "c2", "c3"])
        music = FakeMusic(subs=["c1"])
        util.append_line(config.SUBS_MEMORY, "c2")
        subscriptions.run(old, music)
        self.assertEqual(music.subscribed, ["c3"])
        subscriptions.run(old, music)
        self.assertEqual(music.subscribed, ["c3"])        # rerun: nothing new


if __name__ == "__main__":
    unittest.main()
