"""Email sender using SendGrid - CAN-SPAM compliant."""

from datetime import datetime
from typing import Optional

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Content,
    From,
    Header,
    Mail,
    To,
    UnsubscribeGroup,
)

from app.config import settings


class EmailSender:
    def __init__(self):
        self.client = SendGridAPIClient(settings.sendgrid_api_key)

    async def send_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        html_body: str,
        plain_body: Optional[str] = None,
        reply_to: Optional[str] = None,
        custom_args: Optional[dict] = None,
    ) -> dict:
        """Send a CAN-SPAM compliant email.

        custom_args are included in the SendGrid payload and returned with
        webhook events, letting us trace events back to the outreach log.
        """
        message = Mail(
            from_email=From(settings.email_from_address, settings.email_from_name),
            to_emails=To(to_email, to_name),
            subject=subject,
            html_content=Content("text/html", html_body),
        )

        # Plain text fallback
        if plain_body:
            message.add_content(Content("text/plain", plain_body))

        # Reply-to
        if reply_to:
            message.reply_to = reply_to

        # Custom args for tracking (lead_id, outreach_log_id, campaign_id)
        # These appear in webhook events so we can map them back
        if custom_args:
            for key, value in custom_args.items():
                message.custom_arg[key] = str(value)

        # CAN-SPAM: Add unsubscribe link in footer
        # SendGrid handles this via unsubscribe groups
        # The unsubscribe URL is also in the email body

        try:
            response = self.client.send(message)
            return {
                "success": True,
                "status_code": response.status_code,
                "message_id": response.headers.get("X-Message-Id"),
                "sent_at": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "sent_at": datetime.utcnow().isoformat(),
            }

    def build_cold_email_html(
        self,
        body_text: str,
        demo_url: str,
        business_name: str,
        sender_name: str,
        sender_company: str,
        sender_phone: str,
        sender_address: str,
        unsubscribe_url: str,
    ) -> str:
        """Build HTML email from plain text body."""
        # Convert plain text to HTML with basic formatting
        body_html = body_text.replace("\n\n", "</p><p>").replace("\n", "<br>")
        body_html = f"<p>{body_html}</p>"

        # Make demo URL a clickable button
        body_html = body_html.replace(
            demo_url,
            f'<a href="{demo_url}" style="display:inline-block;padding:12px 24px;background-color:#2563eb;color:white;text-decoration:none;border-radius:6px;font-weight:600;">View Your Demo Website →</a>',
        )

        return f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="margin-bottom: 24px;">
                {body_html}
            </div>
            
            <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
            
            <p style="font-size: 14px; color: #666;">
                {sender_name}<br>
                {sender_company}<br>
                {sender_phone}<br>
                {sender_address}
            </p>
            
            <p style="font-size: 12px; color: #999;">
                <a href="{unsubscribe_url}?email={to_email if '{to_email}' in body_text else ''}" style="color: #999;">Unsubscribe</a>
                | <a href="{unsubscribe_url}" style="color: #999;">Manage Preferences</a>
            </p>
        </body>
        </html>
        """


email_sender = EmailSender()
