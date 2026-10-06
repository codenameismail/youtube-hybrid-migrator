"""Central settings and file locations. Nothing in here needs editing normally."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Private files (credentials, cookies). Git-ignored. Never share these.
SECRETS_DIR = ROOT / "secrets"
CLIENT_SECRET_FILE = SECRETS_DIR / "client_secret.json"   # from Google Cloud Console
OLD_TOKEN = SECRETS_DIR / "token_old.json"                # created on first login (OLD account)
NEW_TOKEN = SECRETS_DIR / "token_new.json"                # created on first login (NEW account)
NEW_HEADERS = SECRETS_DIR / "new_headers.json"            # browser cookies for the NEW account

# Progress/memory files. Git-ignored. They contain your personal viewing data.
STATE_DIR = ROOT / "state"
LIKES_MEMORY = STATE_DIR / "migrated_likes.txt"
SUBS_MEMORY = STATE_DIR / "migrated_subs.txt"
PLAYLIST_TYPES = STATE_DIR / "playlist_types.txt"
YT_PLAYLISTS_CREATED = STATE_DIR / "yt_playlists_created.txt"
QUOTA_FILE = STATE_DIR / "quota.json"

# Official YouTube API quota: 10,000 units/day by default. Every write costs 50.
DAILY_QUOTA_BUDGET = 9500   # stay below the real limit
WRITE_COST = 50

# A playlist is guessed to be a MUSIC playlist when at least this share of its
# videos are in YouTube's "Music" category.
MUSIC_THRESHOLD = 0.7

# Tracks sent per request when adding to a YouTube Music playlist.
BATCH_SIZE = 50

# Random pause (seconds) between YouTube Music writes, to look human.
DELAY_RANGE = (1.5, 3.5)


def ensure_dirs():
    SECRETS_DIR.mkdir(exist_ok=True)
    STATE_DIR.mkdir(exist_ok=True)
