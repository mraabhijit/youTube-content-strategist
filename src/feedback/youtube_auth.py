from pathlib import Path

from config import settings
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


def get_authenticated_service(api_name: str, api_version: str):
    """
    Returns an authenticated Google API Service.
    Handles token caching and refresh automatically.
    """
    creds = None

    if Path(settings.token_path).exists():
        creds = Credentials.from_authorized_user_file(settings.token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                settings.client_secrets_path, SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(settings.token_path, "w") as token_file:
            token_file.write(creds.to_json())

    return build(api_name, api_version, credentials=creds)
