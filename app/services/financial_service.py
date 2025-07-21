from sqlalchemy.orm import Session
from datetime import datetime, time
from typing import Dict, Optional, Any
import json
import logging

from app.models.database import FinancialInquiry, CallSession, InquiryPriority
from app.services.voice_service import VoiceService
from app.services.notification_service import NotificationService
from config.settings import settings

logger = logging.getLogger(__name__)

class FinancialService:
    def __init__(self):
        self.voice_service = VoiceService()
        self.notification_service = NotificationService()
    
    def is_business_hours(self) -> bool:
        """Check if current time is within business hours"""
        now = datetime.now()
        current_hour = now.hour
        current_day = now.weekday()  # 0 = Monday, 6 = Sunday
        
        # Monday-Friday, business hours
        is_weekday = current_day < 5  # Monday-Friday
        is_business_time = settings.BUSINESS_HOURS_START <= current_hour < settings.BUSINESS_HOURS_END
        
        return is_weekday and is_business_time
    
    async def handle_after_hours_inquiry(self, db: Session, user_input: str, 
                                        call_sid: str) -> tuple[str, bool]:
        """Handle after-hours customer inquiries"""
        try:
            # Get or create session
            session_data = self.get_session_data(db, call_sid)
            
            # Extract customer information
            customer_info = await self.extract_customer_info(user_input, session_data)
            
            # Update session
            self.update_session_data(db, call_sid, customer_info)
            
            # Check if we have all required information
            required_fields = ['name', 'phone', 'reason']
            missing_fields = [field for field in required_fields 
                             if not customer_info.get(field)]
            
            if missing_fields:
                # Ask for missing information
                next_question = self.get_next_question(missing_fields[0])
                return next_question, False
            
            # All information collected, create inquiry
            inquiry = await self.create_inquiry(db, customer_info)
            
            # Send notifications to staff
            await self.notification_service.send_staff_notification(inquiry)
            
            response = f"Thank you, {inquiry.customer_name}! I've recorded your information and our team will contact you within 24 hours. Have a great day!"
            
            return response, True
            
        except Exception as e:
            logger.error(f"Error handling financial inquiry: {e}")
            return "I apologize for the technical difficulty. Please call back during business hours and our team will be happy to assist you.", True
    
    async def extract_customer_info(self, user_input: str, 
                                   existing_data: Dict) -> Dict[str, Any]:
        """Extract customer information using AI or fallback logic"""
        if self.voice_service.openai_enabled:
            return await self._extract_with_ai(user_input, existing_data)
        else:
            return self._extract_with_fallback(user_input, existing_data)
    
    async def _extract_with_ai(self, user_input: str, existing_data: Dict) -> Dict[str, Any]:
        """Extract customer information using OpenAI"""
        try:
            import openai
            
            prompt = f"""
            Extract customer information from: "{user_input}"
            Current data: {json.dumps(existing_data)}
            
            Extract and update any of these fields:
            - name: full customer name
            - phone: phone number (format as +1XXXXXXXXXX)
            - email: email address (if provided)
            - reason: reason for calling or issue description
            - member_number: account or member number (if provided)
            
            Determine priority based on keywords:
            - URGENT: fraud, account locked, emergency, stolen card
            - HIGH: payment due, loan deadline, cannot access account
            - MEDIUM: general questions, account information
            - LOW: information request, general inquiry
            
            Respond with ONLY valid JSON containing the updated customer information.
            Include a "priority" field with the determined priority level.
            """
            
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Extract customer information and respond with only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.1
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Merge with existing data
            updated_data = existing_data.copy()
            updated_data.update(result)
            
            return updated_data
            
        except Exception as e:
            logger.error(f"Error extracting customer info with AI: {e}")
            return self._extract_with_fallback(user_input, existing_data)
    
    def _extract_with_fallback(self, user_input: str, existing_data: Dict) -> Dict[str, Any]:
        """Extract customer information using pattern matching"""
        updated_data = existing_data.copy()
        
        # Extract name
        if not existing_data.get('name') and any(phrase in user_input.lower() for phrase in ['my name is', 'i am', 'this is']):
            words = user_input.split()
            name_start = -1
            for i, word in enumerate(words):
                if word.lower() in ['is', 'am']:
                    name_start = i + 1
                    break
            if name_start > 0 and name_start < len(words):
                potential_name = ' '.join(words[name_start:name_start+2])
                updated_data['name'] = potential_name.title()
        
        # Extract phone number
        phone = self.voice_service.extract_phone_number(user_input)
        if phone:
            updated_data['phone'] = phone
        
        # Extract email
        email = self.voice_service.extract_email(user_input)
        if email:
            updated_data['email'] = email
        
        # Store reason if not extracted yet
        if not existing_data.get('reason'):
            updated_data['reason'] = user_input
        
        # Determine priority
        priority = self._determine_priority(user_input)
        updated_data['priority'] = priority
        
        return updated_data
    
    def _determine_priority(self, text: str) -> str:
        """Determine priority based on keywords"""
        text_lower = text.lower()
        
        urgent_keywords = ['fraud', 'stolen', 'unauthorized', 'locked', 'emergency', 'hack']
        high_keywords = ['payment', 'due', 'deadline', 'billing', 'dispute', 'access', 'urgent']
        
        if any(keyword in text_lower for keyword in urgent_keywords):
            return 'URGENT'
        elif any(keyword in text_lower for keyword in high_keywords):
            return 'HIGH'
        else:
            return 'MEDIUM'
    
    def get_next_question(self, missing_field: str) -> str:
        """Get appropriate question for missing field"""
        questions = {
            'name': "I'll be happy to help you. First, could you tell me your full name?",
            'phone': "Thank you! And what's the best phone number for our team to reach you at?",
            'reason': "Perfect! Now, could you briefly tell me what you're calling about today?",
            'email': "Would you also like to provide an email address for follow-up?"
        }
        
        return questions.get(missing_field, "I need a bit more information. Could you repeat that?")
    
    async def create_inquiry(self, db: Session, info: Dict[str, Any]) -> FinancialInquiry:
        """Create financial inquiry in database"""
        # Determine priority enum
        priority_map = {
            'URGENT': InquiryPriority.URGENT,
            'HIGH': InquiryPriority.HIGH,
            'MEDIUM': InquiryPriority.MEDIUM,
            'LOW': InquiryPriority.LOW
        }
        
        priority = priority_map.get(info.get('priority', 'MEDIUM'), InquiryPriority.MEDIUM)
        
        inquiry = FinancialInquiry(
            customer_name=info['name'],
            phone=info['phone'],
            email=info.get('email'),
            reason=info['reason'],
            priority=priority,
            call_time=datetime.now()
        )
        
        db.add(inquiry)
        db.commit()
        db.refresh(inquiry)
        
        logger.info(f"Created financial inquiry {inquiry.id} for {inquiry.customer_name} with priority {priority.value}")
        return inquiry
    
    def get_session_data(self, db: Session, call_sid: str) -> Dict[str, Any]:
        """Get session data for call"""
        session = db.query(CallSession).filter(CallSession.call_sid == call_sid).first()
        
        if session and session.session_data:
            try:
                return json.loads(session.session_data)
            except:
                return {}
        
        return {}
    
    def update_session_data(self, db: Session, call_sid: str, data: Dict[str, Any]):
        """Update session data"""
        session = db.query(CallSession).filter(CallSession.call_sid == call_sid).first()
        
        if not session:
            session = CallSession(
                call_sid=call_sid,
                call_type='financial',
                session_data=json.dumps(data)
            )
            db.add(session)
        else:
            session.session_data = json.dumps(data)
            session.updated_at = datetime.now()
        
        db.commit()
