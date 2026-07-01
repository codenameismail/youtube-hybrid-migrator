import time
import random
import os
from auth import authenticate_youtube
from config import OLD_TOKEN, CLIENT_SECRET_FILE
from ytmusicapi import YTMusic

class MasterMigrator:
    def __init__(self):
        print("🔐 Logging into OLD account via Official API (Unrestricted Reading)...")
        self.youtube_old = authenticate_youtube(CLIENT_SECRET_FILE, OLD_TOKEN)
        
        print("🔐 Logging into NEW account via Browser Cookies (Unlimited Writing)...")
        self.new_yt = YTMusic("new_headers.json")
        print("✅ Authentication successful.")

        # Set up local memory for non-music videos
        self.memory_file = "migrated_likes.txt"
        if not os.path.exists(self.memory_file):
            open(self.memory_file, 'w').close()

    def delay(self):
        """Random delay to prevent YouTube from shadow-banning the session."""
        time.sleep(random.uniform(1.5, 3.5))

    # ==========================================
    # DATA FETCHING HELPERS (OFFICIAL API)
    # ==========================================
    def get_old_playlist_items(self, playlist_id):
        """Fetches ALL videos from a specific old playlist, ignoring music filters."""
        videos = []
        try:
            request = self.youtube_old.playlistItems().list(
                part="snippet",
                playlistId=playlist_id,
                maxResults=50
            )
            while request:
                response = request.execute()
                for item in response.get("items", []):
                    title = item["snippet"].get("title", "Unknown")
                    video_id = item["snippet"]["resourceId"]["videoId"]
                    
                    # Filter out dead links
                    if title not in ["Private video", "Deleted video"]:
                        videos.append({"title": title, "id": video_id})
                        
                request = self.youtube_old.playlistItems().list_next(request, response)
        except Exception as e:
            print(f"❌ Failed to fetch playlist items: {e}")
        return videos

    def get_old_subscriptions(self):
        """Fetches ALL subscriptions, including non-music channels."""
        subs = []
        try:
            request = self.youtube_old.subscriptions().list(
                part="snippet",
                mine=True,
                maxResults=50
            )
            while request:
                response = request.execute()
                for item in response.get("items", []):
                    title = item["snippet"].get("title", "Unknown")
                    channel_id = item["snippet"]["resourceId"]["channelId"]
                    subs.append({"title": title, "id": channel_id})
                    
                request = self.youtube_old.subscriptions().list_next(request, response)
        except Exception as e:
            print(f"❌ Failed to fetch subscriptions: {e}")
        return subs

    def get_old_playlists(self):
        """Fetches ALL playlists created by the user."""
        playlists = []
        try:
            request = self.youtube_old.playlists().list(
                part="snippet",
                mine=True,
                maxResults=50
            )
            while request:
                response = request.execute()
                for item in response.get("items", []):
                    title = item["snippet"].get("title", "Unknown")
                    playlist_id = item["id"]
                    playlists.append({"title": title, "id": playlist_id})
                    
                request = self.youtube_old.playlists().list_next(request, response)
        except Exception as e:
            print(f"❌ Failed to fetch playlists: {e}")
        return playlists

    # ==========================================
    # TRANSFER MODULES
    # ==========================================
    def transfer_likes(self):
        print("\n📥 [LIKES] Fetching ALL Liked Videos from OLD account...")
        all_old_likes = self.get_old_playlist_items("LL")
        
        if not all_old_likes:
            print("⚠️ No liked videos found.")
            return

        print(f"✅ Found {len(all_old_likes)} total liked videos.")

        print("📥 [LIKES] Fetching existing likes and local memory for resume logic...")
        
        # 1. Read YT Music API likes
        new_likes = self.new_yt.get_liked_songs(limit=None)
        yt_music_liked_ids = {track['videoId'] for track in new_likes.get('tracks', []) if track.get('videoId')}
        
        # 2. Read Local Memory (for the non-music videos YT Music hides)
        with open(self.memory_file, "r") as f:
            local_memory_ids = set(f.read().splitlines())

        # Combine both sets
        new_liked_ids = yt_music_liked_ids.union(local_memory_ids)

        # Reverse to keep chronological order
        all_old_likes.reverse()

        print("\n📤 [LIKES] Processing on NEW account...")
        for i, video in enumerate(all_old_likes, 1):
            video_id = video['id']
            title = video['title']

            if video_id in new_liked_ids:
                print(f"[{i}/{len(all_old_likes)}] ⏩ Skipping (already liked): {title}")
                continue

            try:
                self.new_yt.rate_song(video_id, 'LIKE')
                print(f"[{i}/{len(all_old_likes)}] 👍 Liked: {title}")
                
                # Save to local memory immediately
                with open(self.memory_file, "a") as f:
                    f.write(video_id + "\n")
                    
                self.delay()
            except Exception as e:
                print(f"[{i}/{len(all_old_likes)}] ❌ Failed: {title} - {e}")

    def transfer_subscriptions(self):
        print("\n📥 [SUBS] Fetching ALL Subscriptions from OLD account...")
        old_subs = self.get_old_subscriptions()
        
        if not old_subs:
            print("⚠️ No subscriptions found.")
            return

        print(f"✅ Found {len(old_subs)} channels.")

        print("📥 [SUBS] Fetching existing subs from NEW account for resume logic...")
        new_subs = self.new_yt.get_library_subscriptions(limit=None)
        new_sub_ids = {sub['browseId'] for sub in new_subs} if new_subs else set()

        old_subs.reverse()

        print("\n📤 [SUBS] Processing on NEW account...")
        for i, sub in enumerate(old_subs, 1):
            channel_id = sub['id']
            title = sub['title']
            
            if channel_id in new_sub_ids:
                print(f"[{i}/{len(old_subs)}] ⏩ Skipping (already subbed): {title}")
                continue
                
            try:
                self.new_yt.subscribe_artists([channel_id])
                print(f"[{i}/{len(old_subs)}] 🔔 Subscribed: {title}")
                self.delay()
            except Exception as e:
                print(f"[{i}/{len(old_subs)}] ❌ Failed: {title} - {e}")

    def transfer_playlists(self):
        print("\n📥 [PLAYLISTS] Fetching ALL Playlists from OLD account...")
        old_playlists = self.get_old_playlists()
        
        print("📥 [PLAYLISTS] Fetching existing Playlists from NEW account...")
        new_playlists = self.new_yt.get_library_playlists(limit=None)
        new_playlist_titles = {p['title']: p['playlistId'] for p in new_playlists} if new_playlists else {}

        print(f"✅ Found {len(old_playlists)} playlists to process.")

        old_playlists.reverse()

        for playlist in old_playlists:
            title = playlist['title']
            old_id = playlist['id']
            
            # Skip system playlists
            if old_id in ['LL', 'WL', 'LM', 'SEAMWL']:
                continue

            print(f"\n📁 Processing Playlist: {title}")
            old_videos = self.get_old_playlist_items(old_id)
            video_ids = [vid['id'] for vid in old_videos]
            
            if not video_ids:
                print(f"⚠️ Playlist '{title}' is empty or only has deleted videos. Skipping.")
                continue

            try:
                # RESUME LOGIC
                if title in new_playlist_titles:
                    print(f"⏩ Playlist '{title}' exists. Checking tracks...")
                    new_id = new_playlist_titles[title]
                    
                    # Get current tracks in the new playlist
                    new_tracks = self.new_yt.get_playlist(new_id, limit=None).get('tracks', [])
                    new_video_ids = {track['videoId'] for track in new_tracks if track['videoId']}
                    
                    # Find missing tracks
                    missing_videos = [vid for vid in video_ids if vid not in new_video_ids]
                    
                    if not missing_videos:
                        print(f"⏩ All {len(video_ids)} tracks already exist. Skipping.")
                        continue
                    
                    print(f"📤 Adding {len(missing_videos)} missing tracks...")
                    self.new_yt.add_playlist_items(new_id, missing_videos)
                    print(f"✅ Successfully updated '{title}'.")
                    self.delay()
                    continue

                # CREATION LOGIC
                print(f"📂 Creating '{title}' on new account...")
                new_playlist_id = self.new_yt.create_playlist(title, "Recovered from old account")
                self.delay()

                print(f"📤 Adding all {len(video_ids)} tracks...")
                self.new_yt.add_playlist_items(new_playlist_id, video_ids)
                print(f"✅ Successfully transferred '{title}'.")
                self.delay()

            except Exception as e:
                print(f"❌ Failed to process playlist '{title}': {e}")


if __name__ == "__main__":
    migrator = MasterMigrator()
    
    print("\n🚀 --- STARTING MASTER TRANSFER ---")
    
    migrator.transfer_likes()
    migrator.transfer_subscriptions()
    migrator.transfer_playlists()
    
    print("\n🎉 All data successfully migrated!")