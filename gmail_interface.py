import os
import re
from datetime import datetime
from base64 import urlsafe_b64decode
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


class GmailInterface:
    def __init__(self, sender, sent_time):
        self._scopes = ["https://www.googleapis.com/auth/gmail.readonly"]
        self._sender = sender
        self._sent_time = sent_time
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

    def get_url(self):
        id_ = None
        for attempt in range(1, 11):
            messages = self._get_messages(numberOfMessages=attempt*10)
            id_ = self._find_message_by_sender(messages)
            if id_:
                break
        else:
            raise Exception(f"Message not found in {attempt} attempts!")
        message = self._get_content(id_)
        return self._extract_url(message)

    def _extract_url(self, message):
        match = re.search(r"(?:Sign In\s*\( )(.*)(?= \))", message)
        if match is None or len(match.groups()) < 1:
            raise Exception("URL not found!")
        return match.group(1)

    def _get_messages(self, num_messages=10):
        res = self._message_service.list(
            userId="me",
            maxResults=num_messages,
        ).execute()
        return res.get("messages", [])

    def _find_message_by_sender(self, messages):
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
                            "%a, %d %b %Y %H:%M:%S %z (%Z)",
                        )
                    except ValueError:
                        time = None
            if name == self._sender and time >= self._sent_time:
                return message["id"]
        return None

    def _get_content(self, id_, format="full"):
        message = self._message_service.get(
            userId="me",
            id=id_,
            format=format,
        ).execute()
        base64_data = ""
        for part in message["payload"]["parts"]:
            base64_data += part["body"]["data"]
        return urlsafe_b64decode(base64_data).decode()
