"""Twilio integration for phone calls and SMS."""

from datetime import datetime
from typing import Optional

from twilio.rest import Client as TwilioClient

from app.config import settings


class PhoneService:
    def __init__(self):
        self.client = TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)
        self.from_number = settings.twilio_phone_number

    async def make_call(
        self,
        to_number: str,
        twiml_url: Optional[str] = None,
        status_callback: Optional[str] = None,
    ) -> dict:
        """Initiate an outbound phone call."""
        try:
            call = self.client.calls.create(
                to=to_number,
                from_=self.from_number,
                url=twiml_url or "http://demo.twilio.com/docs/voice.xml",
                status_callback=status_callback,
                status_callback_event=["initiated", "ringing", "answered", "completed"],
                record=True,
            )
            return {
                "success": True,
                "call_sid": call.sid,
                "status": call.status,
                "started_at": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "started_at": datetime.utcnow().isoformat(),
            }

    async def send_sms(
        self,
        to_number: str,
        body: str,
        status_callback: Optional[str] = None,
    ) -> dict:
        """Send an SMS message."""
        try:
            message = self.client.messages.create(
                to=to_number,
                from_=self.from_number,
                body=body,
                status_callback=status_callback,
            )
            return {
                "success": True,
                "message_sid": message.sid,
                "status": message.status,
                "sent_at": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "sent_at": datetime.utcnow().isoformat(),
            }

    def get_call_recording(self, recording_sid: str) -> Optional[str]:
        """Get the URL of a call recording."""
        try:
            recording = self.client.recordings(recording_sid).fetch()
            return f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Recordings/{recording_sid}.wav"
        except Exception:
            return None

    def get_call_transcript(self, recording_url: str) -> Optional[str]:
        """Get transcription of a call recording (uses Twilio's built-in transcription)."""
        # For production, you'd use a dedicated speech-to-text service
        # (Whisper, Google Speech-to-Text, etc.)
        # Twilio provides basic transcription but it's not great quality
        return None


phone_service = PhoneService()
