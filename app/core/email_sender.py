import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()


def _get_env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name, default)
    return value.strip() if isinstance(value, str) else value


def _resolve_smtp_host(email_host: str | None, email_user: str | None) -> str | None:
    if email_host and "." in email_host and "@" not in email_host:
        return email_host

    if email_user and email_user.lower().endswith("@gmail.com"):
        return "smtp.gmail.com"

    return email_host


EMAIL_USER = _get_env("EMAIL_USER")
EMAIL_PASS = _get_env("EMAIL_PASS")
EMAIL_HOST = _resolve_smtp_host(_get_env("EMAIL_HOST"), EMAIL_USER)
EMAIL_PORT = int(_get_env("EMAIL_PORT", "587"))


def send_email(to_email: str, subject: str, body: str):
    if not EMAIL_HOST or not EMAIL_USER or not EMAIL_PASS:
        print("Email error: missing email configuration")
        return False

    msg = MIMEMultipart()
    msg["From"] = EMAIL_USER
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT, timeout=30)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print("Email error:", e)
        return False
