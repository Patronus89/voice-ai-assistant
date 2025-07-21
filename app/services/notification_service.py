from twilio.rest import Client
from typing import Dict, Any, Optional
import logging

from config.settings import settings
from app.models.database import Reservation, FinancialInquiry

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        # Only initialize Twilio if we have real credentials
        if (settings.TWILIO_ACCOUNT_SID and 
            settings.TWILIO_AUTH_TOKEN and 
            settings.TWILIO_ACCOUNT_SID != "demo_account_sid" and
            settings.TWILIO_AUTH_TOKEN != "demo_auth_token"):
            try:
                self.twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                logger.info("Twilio notification service initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio for notifications: {e}")
                self.twilio_client = None
        else:
            self.twilio_client = None
            logger.info("Notification service running in demo mode")
    
    async def send_reservation_confirmation(self, reservation: Reservation):
        """Send reservation confirmation via SMS"""
        try:
            if not self.twilio_client:
                logger.info(f"Demo: Would send reservation confirmation to {reservation.phone} for {reservation.customer_name}")
                return
            
            # Send SMS confirmation
            sms_message = f"Hi {reservation.customer_name}! Your table for {reservation.party_size} is confirmed for {reservation.reservation_date.strftime('%B %d')} at {reservation.reservation_time.strftime('%I:%M %p')} at {settings.RESTAURANT_NAME}. Call {settings.RESTAURANT_PHONE} for changes."
            
            await self.send_sms(reservation.phone, sms_message)
            logger.info(f"Confirmation sent for reservation {reservation.id}")
            
        except Exception as e:
            logger.error(f"Error sending reservation confirmation: {e}")
    
    async def send_staff_notification(self, inquiry: FinancialInquiry):
        """Send staff notification for financial inquiry"""
        try:
            logger.info(f"Staff notification: New {inquiry.priority.value} priority inquiry from {inquiry.customer_name}")
            
            if inquiry.priority.value in ['urgent', 'high'] and settings.ONCALL_STAFF_PHONE:
                await self.send_urgent_sms(inquiry)
                
        except Exception as e:
            logger.error(f"Error sending staff notification: {e}")
    
    async def send_urgent_sms(self, inquiry: FinancialInquiry):
        """Send SMS for urgent inquiries"""
        try:
            if not self.twilio_client:
                logger.info(f"Demo: Would send urgent SMS about {inquiry.customer_name}")
                return
            
            message = f"URGENT: New {inquiry.priority.value} priority inquiry from {inquiry.customer_name} ({inquiry.phone}). Reason: {inquiry.reason[:100]}..."
            
            await self.send_sms(settings.ONCALL_STAFF_PHONE, message)
            
        except Exception as e:
            logger.error(f"Error sending urgent SMS: {e}")
    
    async def send_sms(self, to_phone: str, message: str):
        """Send SMS message"""
        try:
            if not self.twilio_client:
                logger.info(f"Demo: Would send SMS to {to_phone}: {message}")
                return
            
            result = self.twilio_client.messages.create(
                body=message,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=to_phone
            )
            logger.info(f"SMS sent to {to_phone}: {result.sid}")
            
        except Exception as e:
            logger.error(f"Error sending SMS to {to_phone}: {e}")
