import os
import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CLIENT_SECRET_FILE = "client_secret.json"
TOKEN_FILE = "token.json"

def get_calendar_service():
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            SCOPES
        )
        creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def create_calendar_event(summary, description):
    service = get_calendar_service()

    start = datetime.datetime.now() + datetime.timedelta(minutes=10)
    end = start + datetime.timedelta(minutes=30)

    event = {
        "summary": summary,
        "description": description,
        "start": {
            "dateTime": start.isoformat(),
            "timeZone": "Asia/Kolkata",
        },
        "end": {
            "dateTime": end.isoformat(),
            "timeZone": "Asia/Kolkata",
        },
    }

    service.events().insert(calendarId="primary", body=event).execute()
