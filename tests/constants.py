from datetime import datetime
from typing import Any

VALID_EMAIL: str  = "test@example.com"
NON_EXISTENT_ID: int = 999999999
INVALID_EMAIL: str = "wrong@example.com"

VALID_THREAD_ID: str = "thread-123"
ANOTHER_THREAD_ID: str = "thread-456"

DUMMY_MSG_PAYLOAD: dict[str, Any] = {
        "message_id": "msg-111",
        "is_draft": False,
        "message_from": "Sender <sender@example.com>",
        "dateandtime": datetime.now().isoformat(),
        "to": "Receiver <receiver@example.com>",
        "cc": "",
        "bcc": "",
        "subject": "Test Project",
        "raw_content": "VGhpcyBpcyBhIHRlc3QgZW1haWw=" # Base64 for "This is a test email"
    }