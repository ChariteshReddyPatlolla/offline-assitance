import os
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import time

def load_dotenv():
    cwd = os.getcwd()
    env_paths = [
        os.path.join(cwd, ".env"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))
    ]
    for env_path in env_paths:
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        os.environ[key.strip()] = val.strip()
            break

def _create_message(to: str, subject: str, body: str, attachments: list = None) -> MIMEMultipart:
    load_dotenv()
    sender_email = os.getenv("SENDER_EMAIL", "omniagent@localhost")
    
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    
    if attachments:
        for filepath in attachments:
            if os.path.isfile(filepath):
                part = MIMEBase("application", "octet-stream")
                with open(filepath, "rb") as f:
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={os.path.basename(filepath)}",
                )
                msg.attach(part)
    return msg

def save_to_drafts_raw(to: str, subject: str, body: str, attachments: list = None) -> str:
    """Connects via IMAP and explicitly saves it to the actual Drafts folder."""
    load_dotenv()
    imap_server = os.getenv("IMAP_SERVER", "imap.gmail.com")
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")
    
    if not sender_email or not sender_password:
        return "❌ Email credentials not configured in .env (SENDER_EMAIL, SENDER_PASSWORD)."

    msg = _create_message(to, subject, body, attachments)
    
    try:
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(sender_email, sender_password)
        # Append to Drafts folder (common names: "[Gmail]/Drafts" or "Drafts")
        draft_folder = "[Gmail]/Drafts" if "gmail" in imap_server else "Drafts"
        mail.append(draft_folder, '', imaplib.Time2Internaldate(time.time()), msg.as_bytes())
        mail.logout()
        
        return (
            f"✅ **Email Saved to Drafts!**\n\n"
            f"Successfully saved to `{draft_folder}` folder via IMAP.\n\n"
            f"**To:** {to}\n**Subject:** {subject}\n**Attachments:** {len(attachments) if attachments else 0}"
        )
    except Exception as e:
        return f"❌ Failed to save draft via IMAP: {str(e)}"

def send_email_raw(to: str, subject: str, body: str, attachments: list = None) -> str:
    """Actually sends the email via SMTP."""
    load_dotenv()
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")
    
    msg = _create_message(to, subject, body, attachments)

    if not sender_email or not sender_password:
        try:
            server = smtplib.SMTP("localhost", 1025, timeout=2)
            server.sendmail("omniagent@localhost", [to], msg.as_string())
            server.quit()
            return f"Success! Email sent automatically via local debug SMTP server (localhost:1025)."
        except Exception:
            return "Failed: SMTP credentials not configured in .env file."

    try:
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        
        return (
            f"**Email Sent Automatically!**\n\n"
            f"Successfully connected to `{smtp_server}` and delivered email to `{to}`.\n\n"
            f"**Subject:** {subject}"
        )
    except Exception as e:
        return f"Failed to send email automatically via SMTP: {str(e)}"

def read_emails_raw(limit: int = 5) -> str:
    load_dotenv()
    imap_server = os.getenv("IMAP_SERVER", "imap.gmail.com")
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")
    
    if not sender_email or not sender_password:
        return "Failed: Email credentials not configured."
        
    try:
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(sender_email, sender_password)
        mail.select("inbox")
        status, messages = mail.search(None, "ALL")
        if status != "OK":
            return "Failed to search inbox."
            
        email_ids = messages[0].split()
        latest_email_ids = email_ids[-limit:]
        
        results = []
        for e_id in reversed(latest_email_ids):
            status, msg_data = mail.fetch(e_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject, encoding = email.header.decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")
                    sender = msg.get("From")
                    results.append(f"**From:** {sender}\n**Subject:** {subject}")
                    
        mail.logout()
        if not results:
            return "No recent emails found."
        return "\n\n---\n\n".join(results)
    except Exception as e:
        return f"❌ Failed to read emails via IMAP: {str(e)}"

def search_emails_raw(query: str) -> str:
    # Simplified search by FROM or SUBJECT
    load_dotenv()
    imap_server = os.getenv("IMAP_SERVER", "imap.gmail.com")
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")
    
    if not sender_email or not sender_password:
        return "❌ Email credentials not configured."
        
    try:
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(sender_email, sender_password)
        mail.select("inbox")
        
        # Search BOTH FROM and SUBJECT
        status, msgs_from = mail.search(None, f'(FROM "{query}")')
        status, msgs_subj = mail.search(None, f'(SUBJECT "{query}")')
        
        email_ids = set(msgs_from[0].split() + msgs_subj[0].split())
        email_ids = list(email_ids)[-5:] # last 5 matches
        
        results = []
        for e_id in reversed(email_ids):
            status, msg_data = mail.fetch(e_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject, encoding = email.header.decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")
                    sender = msg.get("From")
                    results.append(f"**From:** {sender}\n**Subject:** {subject}")
                    
        mail.logout()
        if not results:
            return f"No emails found matching '{query}'."
        return "\n\n---\n\n".join(results)
    except Exception as e:
        return f"❌ Failed to search emails via IMAP: {str(e)}"
