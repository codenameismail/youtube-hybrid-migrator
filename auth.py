"""Google OAuth login for the official YouTube Data API."""
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]


def _save(credentials, token_file):
    token_file = Path(token_file)
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(credentials.to_json(), encoding="utf-8")


def _load(token_file):
    token_file = Path(token_file)
    if not token_file.exists():
        return None
    try:
        return Credentials.from_authorized_user_file(str(token_file), SCOPES)
    except Exception:
        return None


def authenticate_youtube(client_secret_file, token_file, account_label):
    """Return an authenticated YouTube service.

    Uses the saved token when possible, silently refreshes it when expired, and
    only opens the browser when a real login is needed.
    """
    client_secret_file = Path(client_secret_file)
    credentials = _load(token_file)

    if credentials and not credentials.valid and credentials.refresh_token:
        try:
            credentials.refresh(Request())
            _save(credentials, token_file)
        except Exception:
            credentials = None  # refresh token expired or revoked
    if credentials and not credentials.valid:
        credentials = None

    if not credentials:
        if not client_secret_file.exists():
            raise FileNotFoundError(
                f"{client_secret_file} not found. See docs/SETUP.md (Part 2) to create it."
            )
        print(
            f"\nA browser window will open. Log in with your {account_label} Google account.")
        flow = InstalledAppFlow.from_client_secrets_file(
            str(client_secret_file), SCOPES)
        credentials = flow.run_local_server(port=8080)
        _save(credentials, token_file)

    return build("youtube", "v3", credentials=credentials, cache_discovery=False)
