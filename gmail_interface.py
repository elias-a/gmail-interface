import os
import re
from datetime import datetime
from base64 import urlsafe_b64decode
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


class GmailInterface:
    def __init__(self):
        self._scopes = ["https://www.googleapis.com/auth/gmail.readonly"]
        self._authenticate()
        self._initialize()

    def _authenticate(self):
        credentials = None
        if os.path.exists("token.json"):
            credentials = Credentials.from_authorized_user_file(
                "token.json",
                self._scopes,
            )
        if not credentials or not credentials.valid:
            if (
                credentials and
                credentials.expired and
                credentials.refresh_token
            ):
                credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json",
                    self._scopes,
                )
                credentials = flow.run_local_server(port=0)
                with open("token.json", "wt") as f:
                    f.write(credentials.to_json())
        self._credentials = credentials

    def _initialize(self):
        service = build("gmail", "v1", credentials=self._credentials)
        self._message_service = service.users().messages()

    def get_message_by_sender(self, sender, sent_time, max_attempts=5):
        id_ = None
        for attempt in range(max_attempts):
            messages = self._get_messages(num_messages=5*(attempt+1))
            id_ = self._parse_messages(messages, sender, sent_time)
            if id_:
                content = self._get_content(id_)
                return content
        else:
            raise Exception(f"Message not found in {attempt} attempts!")

    def _get_messages(self, num_messages=10):
        res = self._message_service.list(
            userId="me",
            maxResults=num_messages,
        ).execute()
        return res.get("messages", [])

    def _parse_messages(self, messages, sender, sent_time):
        for message in messages:
            id_ = message["id"]
            data = self._message_service.get(
                userId="me",
                id=id_,
                format="metadata",
            ).execute()
            headers = data["payload"]["headers"]
            name = None
            time = None
            for header in headers:
                if header["name"] == "From":
                    name = header["value"]
                elif header["name"] == "Date":
                    value = header["value"]
                    try:
                        time = datetime.strptime(
                            value,
                            "%a, %d %b %Y %H:%M:%S %z",
                        )
                    except ValueError:
                        time = None
            if name == sender and time >= sent_time:
                return message["id"]
        return None

    def _get_content(self, id_, format="full"):
        message = self._message_service.get(
            userId="me",
            id=id_,
            format=format,
        ).execute()
        data = "".join(p["body"]["data"] for p in message["payload"]["parts"])
        return urlsafe_b64decode(data).decode()
