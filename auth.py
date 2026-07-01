import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

def authenticate_youtube(credentials_file, token_file):
    # scopes = ["https://www.googleapis.com/auth/youtube"]
    scopes = ["https://www.googleapis.com/auth/youtube.force-ssl"]

    credentials = None

    if os.path.exists(token_file):
        with open(token_file, "rb") as token:
            credentials = pickle.load(token)

    if not credentials or not credentials.valid:
        flow = InstalledAppFlow.from_client_secrets_file(credentials_file, scopes)
        credentials = flow.run_local_server(port=8080)
        with open(token_file, "wb") as token:
            pickle.dump(credentials, token)

    return build("youtube", "v3", credentials=credentials)
