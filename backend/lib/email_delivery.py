"""
Password-reset email delivery for ORBIS.

Production configuration (via environment variables):
  SMTP_HOST     — SMTP server hostname
  SMTP_PORT     — SMTP port (default 587 for STARTTLS)
  SMTP_USER     — SMTP username
  SMTP_PASS     — SMTP password
  FROM_EMAIL    — Sender email address

When SMTP_HOST is not configured, the dev adapter logs the reset link
to the server console. Reset tokens are NEVER returned in API responses.
"""
from __future__ import annotations
import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

def _get_app_url() -> str:
    """Return the configured application origin URL."""
    url = os.environ.get("APP_URL", "http://localhost:3000").rstrip("/")
    return url

def _build_reset_email(reset_url: str) -> tuple[str, str]:
    """Build subject and HTML body for the reset email."""
    subject = "ORBIS — Password Reset Request"
    body = f"""
<html>
<body style="font-family: monospace; background: #050811; color: #94a3b8; padding: 2rem;">
  <div style="max-width: 480px; margin: 0 auto; border: 1px solid #1e293b; padding: 2rem; border-radius: 8px;">
    <div style="font-size: 1.25rem; color: #e2e8f0; letter-spacing: 0.2em; margin-bottom: 1rem;">ORBIS</div>
    <div style="font-size: 0.7rem; color: #38bdf8; letter-spacing: 0.15em; margin-bottom: 1.5rem;">RECOVERY CHANNEL</div>
    <p>A password reset was requested for your operator account.</p>
    <p>This link expires in <strong>1 hour</strong> and is single-use.</p>
    <div style="margin: 2rem 0;">
      <a href="{reset_url}" style="background: #38bdf8; color: #0f172a; padding: 0.75rem 1.5rem; text-decoration: none; border-radius: 4px; font-weight: bold;">
        RESET PASSWORD
      </a>
    </div>
    <p style="font-size: 0.75rem; color: #64748b;">
      If you did not request this, you can safely ignore this email.<br>
      Do not share this link.
    </p>
  </div>
</body>
</html>
"""
    return subject, body

def send_reset_email(to_email: str, token: str) -> None:
    """
    Send the password-reset link.
    
    In development (no SMTP_HOST configured): logs the reset URL to console only.
    In production: sends via SMTP.
    
    The plaintext token is NEVER logged. Only the reset URL is logged in dev mode.
    """
    app_url = _get_app_url()
    reset_url = f"{app_url}/reset-password?token={token}"
    subject, html_body = _build_reset_email(reset_url)
    
    smtp_host = os.environ.get("SMTP_HOST", "").strip()
    
    if not smtp_host:
        logger.warning(
            "ORBIS DEV — password reset requested for %s. "
            "No SMTP configured. Reset link: %s",
            to_email,
            reset_url,
        )
        return

    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")
    from_email = os.environ.get("FROM_EMAIL", smtp_user or "noreply@orbis.local")
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html"))
    
    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.ehlo()
            server.starttls()
            if smtp_user:
                server.login(smtp_user, smtp_pass)
            server.sendmail(from_email, [to_email], msg.as_string())
        logger.info("ORBIS — password reset email sent to %s", to_email)
    except Exception as exc:
        logger.error("ORBIS — failed to send reset email: %s", exc)
        raise
