import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from langchain_core.tools import tool
from services.tools.approval_store import require_approval

# Manual dotenv loader to keep it zero-dependency
def load_dotenv():
    env_path = os.path.join(os.getcwd(), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip()

@tool
def draft_email(to: str, subject: str, body: str) -> str:
    """
    Draft and send an email automatically to a recipient.
    Shows an approval dialog before anything is sent.
    Use this when the user asks to write, compose, or send an email.
    Args:
        to: recipient email address or name
        subject: email subject line
        body: full email body text
    """
    action_key = f"email:{to}"
    approval = require_approval(
        action_key=action_key,
        description=f"Send email automatically to '{to}' with subject '{subject}'",
        details={"to": to, "subject": subject, "body": body},
    )
    
    if approval:
        return approval

    # Load environmental variables from .env
    load_dotenv()
    
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")

    # If SMTP credentials are not configured, guide the user on how to set them up
    if not sender_email or not sender_password:
        # Try local debugging server (port 1025) first
        try:
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = "omniagent@localhost"
            msg["To"] = to
            
            server = smtplib.SMTP("localhost", 1025, timeout=2)
            server.sendmail("omniagent@localhost", [to], msg.as_string())
            server.quit()
            return (
                f"✅ Email sent automatically via local debug SMTP server (localhost:1025)!\n\n"
                f"**To:** {to}\n"
                f"**Subject:** {subject}\n"
                f"**Body:**\n{body}"
            )
        except Exception:
            # Generate the template .env file automatically for the user to make it easier!
            env_content = (
                "# OmniAgent SMTP Configuration\n"
                "SENDER_EMAIL=your_email@gmail.com\n"
                "SENDER_PASSWORD=your_gmail_app_password\n"
                "SMTP_SERVER=smtp.gmail.com\n"
                "SMTP_PORT=587\n"
            )
            try:
                if not os.path.exists(".env"):
                    with open(".env", "w", encoding="utf-8") as f:
                        f.write(env_content)
            except Exception:
                pass

            return (
                f"❌ SMTP credentials not configured.\n\n"
                f"I have automatically created a `.env` template file in your project root.\n"
                f"Please open `.env` and fill in your sender email and password (for Gmail, use an **App Password**):\n"
                f"```env\n"
                f"SENDER_EMAIL=your_email@gmail.com\n"
                f"SENDER_PASSWORD=your_gmail_app_password\n"
                f"```\n"
                f"Once you fill this in, future emails will be sent automatically via Gmail SMTP!"
            )

    # Execute actual automatic email sending via SMTP
    try:
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        
        return (
            f"🚀 **Email Sent Automatically!**\n\n"
            f"Successfully connected to `{smtp_server}` and delivered email to `{to}`.\n\n"
            f"**From:** {sender_email}\n"
            f"**To:** {to}\n"
            f"**Subject:** {subject}\n\n"
            f"**Body:**\n{body}"
        )
    except Exception as e:
        return f"❌ Failed to send email automatically via SMTP: {str(e)}"