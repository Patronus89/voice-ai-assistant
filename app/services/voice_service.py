from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather
from typing import Dict, Optional, Any
import json
import re
from datetime import datetime
import logging

from config.settings import settings

logger = logging.getLogger(__name__)

class VoiceService:
    def __init__(self):
        # Only initialize Twilio if we have real credentials
        if (settings.TWILIO_ACCOUNT_SID and 
            settings.TWILIO_AUTH_TOKEN and 
            settings.TWILIO_ACCOUNT_SID != "demo_account_sid" and
            settings.TWILIO_AUTH_TOKEN != "demo_auth_token"):
            try:
                self.twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                self.twilio_enabled = True
                logger.info("Twilio client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {e}")
                self.twilio_client = None
                self.twilio_enabled = False
        else:
            self.twilio_client = None
            self.twilio_enabled = False
            logger.info("Twilio running in demo mode - no real credentials provided")
        
        # OpenAI setup
        if (settings.OPENAI_API_KEY and 
            settings.OPENAI_API_KEY != "demo_openai_key"):
            try:
                import openai
                openai.api_key = settings.OPENAI_API_KEY
                self.openai_enabled = True
                logger.info("OpenAI client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI: {e}")
                self.openai_enabled = False
        else:
            self.openai_enabled = False
            logger.info("OpenAI running in demo mode - no real credentials provided")
    
    def create_response(self) -> VoiceResponse:
        """Create a new TwiML response object"""
        return VoiceResponse()
    
    def say_and_gather(self, response: VoiceResponse, message: str, 
                      action: str, timeout: int = 5, speech_timeout: int = 3) -> VoiceResponse:
        """Add say and gather to TwiML response"""
        response.say(message, voice='Polly.Joanna')
        response.gather(
            input='speech',
            timeout=timeout,
            speech_timeout=speech_timeout,
            action=action,
            method='POST'
        )
        return response
    
    async def classify_intent(self, user_speech: str, context: str = "general") -> Dict[str, Any]:
        """Classify user intent using OpenAI or fallback"""
        if not self.openai_enabled:
            return self._fallback_intent_classification(user_speech, context)
        
        try:
            import openai
            
            if context == "restaurant":
                prompt = f"""
                Classify this restaurant customer request:
                "{user_speech}"
                
                Categories:
                - RESERVATION: booking, changing, canceling reservations
                - MENU_INQUIRY: questions about food, ingredients, prices
                - HOURS_LOCATION: operating hours, address, directions
                - COMPLAINT: issues, problems
                - OTHER: anything else
                
                Respond in JSON format:
                {{"intent": "CATEGORY", "confidence": 0.9, "entities": {{"date": null, "time": null, "party_size": null}}}}
                """
            
            elif context == "financial":
                prompt = f"""
                Classify this financial services request:
                "{user_speech}"
                
                Categories:
                - ACCOUNT_INQUIRY: account questions, balance, statements
                - LOAN_APPLICATION: loan questions, applications
                - TECHNICAL_ISSUE: online banking, card issues
                - COMPLAINT: service complaints, disputes
                - GENERAL: general questions
                
                Priority levels:
                - URGENT: fraud, locked account, emergency
                - HIGH: payment issues, loan deadlines
                - MEDIUM: general inquiries
                - LOW: information requests
                
                Respond in JSON format:
                {{"intent": "CATEGORY", "priority": "LEVEL", "confidence": 0.9}}
                """
            
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an AI that classifies customer requests. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.3
            )
            
            result = response.choices[0].message.content
            return json.loads(result)
            
        except Exception as e:
            logger.error(f"Error in OpenAI intent classification: {e}")
            return self._fallback_intent_classification(user_speech, context)
    
    def _fallback_intent_classification(self, user_speech: str, context: str) -> Dict[str, Any]:
        """Fallback intent classification without AI"""
        speech_lower = user_speech.lower()
        
        if context == "restaurant":
            if any(word in speech_lower for word in ['reservation', 'book', 'table', 'reserve']):
                return {"intent": "RESERVATION", "confidence": 0.8}
            elif any(word in speech_lower for word in ['menu', 'food', 'dish', 'price', 'cost']):
                return {"intent": "MENU_INQUIRY", "confidence": 0.8}
            elif any(word in speech_lower for word in ['hours', 'open', 'close', 'location', 'address']):
                return {"intent": "HOURS_LOCATION", "confidence": 0.8}
            else:
                return {"intent": "OTHER", "confidence": 0.5}
        
        elif context == "financial":
            if any(word in speech_lower for word in ['fraud', 'stolen', 'unauthorized', 'locked']):
                return {"intent": "ACCOUNT_INQUIRY", "priority": "URGENT", "confidence": 0.8}
            elif any(word in speech_lower for word in ['account', 'balance', 'statement']):
                return {"intent": "ACCOUNT_INQUIRY", "priority": "MEDIUM", "confidence": 0.8}
            elif any(word in speech_lower for word in ['loan', 'credit', 'mortgage']):
                return {"intent": "LOAN_APPLICATION", "priority": "MEDIUM", "confidence": 0.8}
            else:
                return {"intent": "GENERAL", "priority": "MEDIUM", "confidence": 0.5}
        
        return {"intent": "OTHER", "confidence": 0.5}
    
    async def generate_smart_response(self, intent_data: Dict[str, Any], 
                                    user_input: str, context: str) -> str:
        """Generate intelligent response"""
        if self.openai_enabled:
            return await self._generate_ai_response(intent_data, user_input, context)
        else:
            return self._generate_fallback_response(intent_data, context)
    
    async def _generate_ai_response(self, intent_data: Dict[str, Any], 
                                   user_input: str, context: str) -> str:
        """Generate response using OpenAI"""
        try:
            import openai
            
            if context == "restaurant":
                prompt = f"""
                You are a helpful restaurant AI assistant for {settings.RESTAURANT_NAME}.
                
                Customer said: "{user_input}"
                Intent detected: {intent_data.get('intent', 'OTHER')}
                
                Generate a helpful, conversational response that:
                1. Acknowledges their request
                2. Provides helpful information or asks follow-up questions
                3. Keeps the conversation flowing naturally
                4. Is under 100 words
                5. Sounds friendly and professional
                
                If it's a reservation request, ask for details like date, time, party size.
                If it's a menu question, offer to help with specific items or recommendations.
                """
            
            elif context == "financial":
                prompt = f"""
                You are a helpful after-hours AI assistant for {settings.CREDIT_UNION_NAME}.
                
                Customer said: "{user_input}"
                Intent: {intent_data.get('intent', 'GENERAL')}
                Priority: {intent_data.get('priority', 'MEDIUM')}
                
                Generate a professional response that:
                1. Acknowledges their concern
                2. Explains you're collecting info for follow-up
                3. Is reassuring and helpful
                4. Is under 100 words
                5. Asks for their contact information if needed
                """
            
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional customer service AI. Be helpful, concise, and friendly."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return self._generate_fallback_response(intent_data, context)
    
    def _generate_fallback_response(self, intent_data: Dict[str, Any], context: str) -> str:
        """Generate fallback responses without AI"""
        intent = intent_data.get("intent", "OTHER")
        
        if context == "restaurant":
            responses = {
                "RESERVATION": "I'd be happy to help you with a reservation. What date and time would you like to dine with us?",
                "MENU_INQUIRY": "I can help you with information about our menu. What would you like to know about our dishes?",
                "HOURS_LOCATION": f"We're open daily from 11 AM to 10 PM. You can find us at [Your Address]. How else can I help?",
                "OTHER": "I'm here to help with reservations, menu questions, or restaurant information. What can I assist you with?"
            }
        
        elif context == "financial":
            responses = {
                "ACCOUNT_INQUIRY": "I understand you have an account question. I'll collect your information so our team can help you first thing tomorrow.",
                "LOAN_APPLICATION": "I'll be happy to help with your loan inquiry. Let me get your contact information for our lending team.",
                "TECHNICAL_ISSUE": "I'll make sure our technical team gets your information to resolve this issue quickly.",
                "GENERAL": "I'll collect your information so our team can assist you with your inquiry."
            }
        
        else:
            return "Thank you for calling. How can I help you today?"
        
        return responses.get(intent, responses.get("OTHER", "How can I help you today?"))
    
    def extract_phone_number(self, text: str) -> Optional[str]:
        """Extract phone number from text"""
        pattern = r'(\+?1?[\s-]?)?\(?([0-9]{3})\)?[\s-]?([0-9]{3})[\s-]?([0-9]{4})'
        match = re.search(pattern, text)
        
        if match:
            area_code = match.group(2)
            exchange = match.group(3)
            number = match.group(4)
            return f"+1{area_code}{exchange}{number}"
        
        return None
    
    def extract_email(self, text: str) -> Optional[str]:
        """Extract email from text"""
        pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        match = re.search(pattern, text)
        return match.group(0) if match else None
