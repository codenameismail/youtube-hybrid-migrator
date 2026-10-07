"""Thin wrapper around the official YouTube Data API v3.

Reads cost ~1 quota unit. Writes cost 50 units each (daily default: 10,000).
"""
import util

MUSIC_CATEGORY_ID = "10"
UNAVAILABLE_TITLES = ("Private video", "Deleted video")


def is_quota_error(error):
    return "quotaExceeded" in str(error)


class YouTubeAPI:
    def __init__(self, service):
        self.service = service

    @staticmethod
    def _paged(resource, **kwargs):
        request = resource.list(**kwargs)
        while request:
            response = request.execute()
            for item in response.get("items", []):
                yield item
            request = resource.list_next(request, response)

    def whoami(self):
        """Channel name of the logged-in account, or None if it can't be read."""
        try:
            response = self.service.channels().list(part="snippet", mine=True).execute()
            items = response.get("items", [])
            return items[0]["snippet"]["title"] if items else None
        except Exception:
            return None

    def list_playlists(self):
        """Playlists the account created (not saved ones, not LL/WL)."""
        return [
            {
                "id": item["id"],
                "title": item["snippet"].get("title", "Unknown"),
                "description": item["snippet"].get("description", ""),
                "privacy": item.get("status", {}).get("privacyStatus", "private"),
            }
            for item in self._paged(self.service.playlists(), part="snippet,status",
                                    mine=True, maxResults=50)
        ]

    def list_items(self, playlist_id):
        """Videos in a playlist (use 'LL' for Liked videos). Skips private/deleted ones."""
        videos = []
        for item in self._paged(self.service.playlistItems(), part="snippet",
                                playlistId=playlist_id, maxResults=50):
            snippet = item["snippet"]
            title = snippet.get("title", "Unknown")
            if title in UNAVAILABLE_TITLES:
                continue
            videos.append({"id": snippet["resourceId"]["videoId"], "title": title})
        return videos

    def list_subscriptions(self):
        return [
            {"id": item["snippet"]["resourceId"]["channelId"],
             "title": item["snippet"].get("title", "Unknown")}
            for item in self._paged(self.service.subscriptions(), part="snippet",
                                    mine=True, maxResults=50)
        ]

    def music_count(self, video_ids):
        """How many of these videos are in YouTube's Music category."""
        count = 0
        for i in range(0, len(video_ids), 50):
            chunk = video_ids[i:i + 50]
            response = self.service.videos().list(part="snippet", id=",".join(chunk)).execute()
            count += sum(1 for v in response.get("items", [])
                         if v["snippet"].get("categoryId") == MUSIC_CATEGORY_ID)
        return count

    # ---- writes (50 quota units each) ----
    def create_playlist(self, title, description, privacy):
        if privacy not in ("public", "private", "unlisted"):
            privacy = "private"
        body = {
            "snippet": {"title": util.clean_text(title)[:150],
                        "description": util.clean_text(description)[:5000]},
            "status": {"privacyStatus": privacy},
        }
        return self.service.playlists().insert(part="snippet,status", body=body).execute()["id"]

    def add_video(self, playlist_id, video_id):
        body = {"snippet": {"playlistId": playlist_id,
                            "resourceId": {"kind": "youtube#video", "videoId": video_id}}}
        self.service.playlistItems().insert(part="snippet", body=body).execute()
