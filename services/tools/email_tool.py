from typing import List, Optional
from langchain_core.tools import tool
from services.tools.approval_store import require_approval
from services.tools.impl.email import (
    save_to_drafts_raw,
    send_email_raw,
    read_emails_raw,
    search_emails_raw
)

@tool
def save_to_drafts(to: str, subject: str, body: str, attachments: Optional[List[str]] = None) -> str:
    """
    Save an email draft directly to the user's IMAP Drafts folder. Does NOT send the email.
    """
    return save_to_drafts_raw(to, subject, body, attachments)

@tool
def send_email(to: str, subject: str, body: str, attachments: Optional[List[str]] = None) -> str:
    """
    Send an email automatically to a recipient via SMTP. Requires approval.
    """
    action_key = f"email:{to}"
    approval = require_approval(
        action_key=action_key,
        description=f"Send email automatically to '{to}' with subject '{subject}'",
        details={"to": to, "subject": subject, "body": body, "attachments": attachments},
    )
    if approval:
        return approval

    return send_email_raw(to, subject, body, attachments)

@tool
def read_emails(limit: int = 5) -> str:
    """
    Read the most recent emails from the inbox via IMAP.
    """
    return read_emails_raw(limit)

@tool
def search_emails(query: str) -> str:
    """
    Search the inbox via IMAP for a specific sender or subject.
    """
    return search_emails_raw(query)