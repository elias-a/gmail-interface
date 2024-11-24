import os
from unittest import TestCase
from dotenv import load_dotenv
from datetime import datetime, timezone
from gmail_interface import GmailInterface


class Test_GmailInterface(TestCase):
    def setUp(self):
        load_dotenv(".test.env")
        self.sender = os.environ["SENDER"]
        self.sent_time = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0,
        )
        self.expected_content = os.environ["CONTENT"]

    def test_get_message_by_sender(self):
        gmail_interface = GmailInterface()
        message = gmail_interface.get_message_by_sender(
            self.sender,
            self.sent_time,
        )
        assert message == self.expected_content
