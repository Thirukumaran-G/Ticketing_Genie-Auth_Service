import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.config.settings import settings
from src.observability.logging.logger import get_logger

logger = get_logger(__name__)


class EmailService:

    async def _send(
        self, to_email: str, subject: str, html_body: str, text_body: str
    ) -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"]      = to_email
        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        try:
            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USERNAME,
                password=settings.SMTP_PASSWORD,
                use_tls=settings.SMTP_USE_TLS,
                start_tls=not settings.SMTP_USE_TLS,
            )
            logger.info("email_sent", to=to_email, subject=subject)
        except aiosmtplib.SMTPException as exc:
            logger.error("email_smtp_error", to=to_email, error=str(exc))
        except Exception as exc:
            logger.error("email_send_failed", to=to_email, error=str(exc))

    async def send_password_reset(
        self,
        to_email: str,
        full_name: str | None,
        reset_token: str,
    ) -> None:
        name      = full_name or to_email.split("@")[0]
        reset_url = f"{settings.APP_URL}/reset-password?token={reset_token}"
        expire    = settings.PASSWORD_RESET_EXPIRE_MINUTES
        subject   = f"[{settings.APP_NAME}] Password Reset Request"

        html_body = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 0;">
    <tr><td align="center">
      <table width="580" cellpadding="0" cellspacing="0"
             style="background:#fff;border-radius:8px;
                    box-shadow:0 2px 8px rgba(0,0,0,0.08);overflow:hidden;">
        <tr>
          <td style="background:#1a1a2e;padding:28px 40px;">
            <h1 style="margin:0;color:#fff;font-size:20px;">{settings.APP_NAME}</h1>
          </td>
        </tr>
        <tr>
          <td style="padding:36px 40px;">
            <h2 style="margin:0 0 12px;color:#1a1a2e;font-size:18px;">
              Password Reset Request
            </h2>
            <p style="color:#444;font-size:15px;line-height:1.6;margin:0 0 8px;">
              Hi <strong>{name}</strong>,
            </p>
            <p style="color:#444;font-size:15px;line-height:1.6;margin:0 0 24px;">
              We received a request to reset your {settings.APP_NAME} password.
              Click the button below to set a new one.
            </p>
            <table cellpadding="0" cellspacing="0" style="margin:0 0 24px;">
              <tr>
                <td style="border-radius:6px;background:#4f46e5;">
                  <a href="{reset_url}"
                     style="display:inline-block;padding:13px 30px;color:#fff;
                            font-size:15px;font-weight:600;text-decoration:none;
                            border-radius:6px;">
                    Reset My Password
                  </a>
                </td>
              </tr>
            </table>
            <p style="color:#666;font-size:13px;margin:0 0 6px;">
              Or copy this link into your browser:
            </p>
            <p style="word-break:break-all;margin:0 0 24px;">
              <a href="{reset_url}" style="color:#4f46e5;font-size:13px;">{reset_url}</a>
            </p>
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="background:#fff8e1;border-left:4px solid #f59e0b;
                          border-radius:4px;margin-bottom:20px;">
              <tr>
                <td style="padding:12px 16px;color:#92400e;font-size:13px;line-height:1.5;">
                  ⚠️ This link expires in <strong>{expire} minutes</strong> and
                  can only be used <strong>once</strong>.<br/>
                  All active sessions will be signed out after reset.<br/>
                  If you did not request this, you can safely ignore this email.
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <tr>
          <td style="background:#f8f8f8;padding:16px 40px;border-top:1px solid #eee;">
            <p style="margin:0;color:#aaa;font-size:12px;text-align:center;">
              © {settings.APP_NAME} · Automated email — do not reply.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
        """

        text_body = f"""Hi {name},

We received a request to reset your {settings.APP_NAME} password.

Reset your password here:
{reset_url}

This link expires in {expire} minutes and can only be used once.
All active sessions will be signed out after reset.

If you did not request this, ignore this email — your password will not change.

— {settings.APP_NAME}
        """.strip()

        await self._send(to_email, subject, html_body, text_body)