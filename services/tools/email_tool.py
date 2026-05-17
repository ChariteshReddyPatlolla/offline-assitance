from langchain_core.tools import tool
from services.tools.approval_store import require_approval

@tool
def draft_email(to: str, subject: str, body: str) -> str:
    """
    Draft an email to a recipient. Shows an approval dialog before anything is sent.
    Use this when the user asks to write, compose, or send an email.
    Args:
        to: recipient email address or name
        subject: email subject line
        body: full email body text
    """
    action_key = f"email:{to}:{subject[:30]}"
    approval = require_approval(
        action_key=action_key,
        description=f"Send email to '{to}' with subject '{subject}'",
        details={"to": to, "subject": subject, "body": body},
    )
    
    # Corrected conditional: check if approval failed or was denied
    if not approval:
        return "❌ Email draft was denied or requires user confirmation before proceeding."

    # If approved, return the draft (actual SMTP sending can be added later)
    return (
        f"✅ Email draft approved!\n\n"
        f"**To:** {to}\n"
        f"**Subject:** {subject}\n\n"
        f"**Body:**\n{body}\n\n"
        f"_(Note: SMTP sending not configured. Draft is ready to copy.)_"
    )