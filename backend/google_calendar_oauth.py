import os
import datetime

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# ==================================================
# CONFIG
# ==================================================

SCOPES = ["https://www.googleapis.com/auth/calendar"]

# IMPORTANT:
# These paths MUST match your project structure
CLIENT_SECRET_FILE = "auth/client_secret.json"
TOKEN_FILE = "auth/token.json"


# ==================================================
# AUTH / SERVICE CREATION
# ==================================================

def get_calendar_service():
    """
    Returns an authenticated Google Calendar service.
    OAuth flow runs ONLY the first time.
    """
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE, SCOPES
            )
            creds = flow.run_local_server(port=8080)

        os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


# ==================================================
# EVENT CREATION
# ==================================================

def create_calendar_event(summary, description, scheduled_time=None):
    """
    Creates a Google Calendar event. Uses user-provided scheduled_time or defaults to 10 mins from now.
    """
    service = get_calendar_service()

    if scheduled_time:
        start_time = scheduled_time
    else:
        start_time = datetime.datetime.now() + datetime.timedelta(minutes=10)
        
    end_time = start_time + datetime.timedelta(minutes=30)

    event = {
        "summary": summary,
        "description": description,
        "start": {
            "dateTime": start_time.isoformat(),
            "timeZone": "Asia/Kolkata",
        },
        "end": {
            "dateTime": end_time.isoformat(),
            "timeZone": "Asia/Kolkata",
        },
    }

    created_event = (
        service.events()
        .insert(calendarId="primary", body=event)
        .execute()
    )

    return {
        "event_id": created_event.get("id"),
        "htmlLink": created_event.get("htmlLink"),
    }