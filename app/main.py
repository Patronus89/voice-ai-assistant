from fastapi import FastAPI, Request, Depends, Form, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from twilio.twiml.voice_response import VoiceResponse
import uvicorn
from typing import Optional
import logging

from app.models.database import get_db, create_tables, init_sample_data
from app.services.restaurant_service import RestaurantService
from app.services.financial_service import FinancialService
from app.services.voice_service import VoiceService
from config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Voice AI Assistant", 
    version="1.0.0",
    description="Production Voice AI Assistant for Restaurant and Financial Services"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
voice_service = VoiceService()
restaurant_service = RestaurantService()
financial_service = FinancialService()

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database and sample data"""
    try:
        create_tables()
        init_sample_data()
        logger.info("Voice AI Assistant started successfully!")
        logger.info(f"Restaurant: {settings.RESTAURANT_NAME}")
        logger.info(f"Financial: {settings.CREDIT_UNION_NAME}")
    except Exception as e:
        logger.error(f"Startup error: {e}")

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "service": "Voice AI Assistant",
        "version": "1.0.0",
        "restaurant": settings.RESTAURANT_NAME,
        "financial": settings.CREDIT_UNION_NAME
    }

# Restaurant voice endpoints
@app.post("/voice/restaurant")
async def restaurant_voice_handler(request: Request, db: Session = Depends(get_db)):
    """Handle incoming restaurant calls"""
    try:
        form_data = await request.form()
        call_sid = form_data.get("CallSid", "")
        from_number = form_data.get("From", "")
        
        logger.info(f"Restaurant call from {from_number}, CallSid: {call_sid}")
        
        response = VoiceResponse()
        
        greeting = f"Hello! Welcome to {settings.RESTAURANT_NAME}. I'm your AI assistant. I can help you make a reservation, answer questions about our menu, or provide information about our restaurant. How can I help you today?"
        
        response.say(greeting, voice='Polly.Joanna')
        response.gather(
            input='speech',
            timeout=5,
            speech_timeout=3,
            action='/voice/restaurant/process',
            method='POST'
        )
        
        # Fallback if no speech detected
        response.say("I didn't hear anything. Please call back and I'll be happy to help!")
        
        return Response(content=str(response), media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Error in restaurant voice handler: {e}")
        response = VoiceResponse()
        response.say("I apologize for the technical difficulty. Please call back in a moment.")
        return Response(content=str(response), media_type="application/xml")

@app.post("/voice/restaurant/process")
async def process_restaurant_request(
    request: Request, 
    db: Session = Depends(get_db),
    SpeechResult: Optional[str] = Form(None),
    CallSid: Optional[str] = Form(None)
):
    """Process restaurant customer requests"""
    try:
        if not SpeechResult or not CallSid:
            response = VoiceResponse()
            response.say("I'm sorry, I didn't catch that. Could you please repeat your request?")
            response.gather(
                input='speech',
                action='/voice/restaurant/process',
                method='POST'
            )
            return Response(content=str(response), media_type="application/xml")
        
        logger.info(f"Restaurant speech: {SpeechResult}")
        
        # Classify intent
        intent_data = await voice_service.classify_intent(SpeechResult, "restaurant")
        intent = intent_data.get("intent", "OTHER")
        
        logger.info(f"Classified intent: {intent}")
        
        response = VoiceResponse()
        
        if intent == "RESERVATION":
            # Handle reservation request
            reply, is_complete = await restaurant_service.handle_reservation_request(
                db, SpeechResult, CallSid
            )
            
            response.say(reply, voice='Polly.Joanna')
            
            if not is_complete:
                # Continue gathering information
                response.gather(
                    input='speech',
                    action='/voice/restaurant/process',
                    method='POST'
                )
        
        elif intent == "MENU_INQUIRY":
            # Handle menu questions
            reply = await restaurant_service.handle_menu_inquiry(db, SpeechResult)
            response.say(reply, voice='Polly.Joanna')
            
            # Ask if they need anything else
            response.say("Is there anything else I can help you with today?")
            response.gather(
                input='speech',
                action='/voice/restaurant/process',
                method='POST'
            )
        
        elif intent == "HOURS_LOCATION":
            # Provide restaurant information
            info = f"We're open Monday through Sunday from 11 AM to 10 PM. We're located at [Your Restaurant Address]. You can also visit our website for more information. Is there anything else I can help you with?"
            response.say(info, voice='Polly.Joanna')
            response.gather(
                input='speech',
                action='/voice/restaurant/process',
                method='POST'
            )
        
        else:
            # Use AI to generate smart response
            reply = await voice_service.generate_smart_response(intent_data, SpeechResult, "restaurant")
            response.say(reply, voice='Polly.Joanna')
            response.gather(
                input='speech',
                action='/voice/restaurant/process',
                method='POST'
            )
        
        return Response(content=str(response), media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Error processing restaurant request: {e}")
        response = VoiceResponse()
        response.say("I apologize for the technical difficulty. Let me transfer you to our hostess who can help you right away.")
        response.dial(settings.RESTAURANT_PHONE)
        return Response(content=str(response), media_type="application/xml")

# Financial services voice endpoints
@app.post("/voice/financial")
async def financial_voice_handler(request: Request, db: Session = Depends(get_db)):
    """Handle incoming financial services calls"""
    try:
        form_data = await request.form()
        call_sid = form_data.get("CallSid", "")
        from_number = form_data.get("From", "")
        
        logger.info(f"Financial call from {from_number}, CallSid: {call_sid}")
        
        response = VoiceResponse()
        
        # Check business hours
        if financial_service.is_business_hours():
            # Transfer to human during business hours
            response.say(f"Thank you for calling {settings.CREDIT_UNION_NAME}. Please hold while I transfer you to our customer service team.")
            response.dial(settings.RESTAURANT_PHONE)  # Replace with actual business number
        else:
            # Handle after hours with AI
            greeting = f"Thank you for calling {settings.CREDIT_UNION_NAME}. Our offices are currently closed, but I'm here to help collect your information so our team can assist you first thing tomorrow. This will just take a moment."
            
            response.say(greeting, voice='Polly.Joanna')
            response.gather(
                input='speech',
                timeout=5,
                speech_timeout=3,
                action='/voice/financial/process',
                method='POST'
            )
        
        return Response(content=str(response), media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Error in financial voice handler: {e}")
        response = VoiceResponse()
        response.say("I apologize for the technical difficulty. Please call back during our business hours.")
        return Response(content=str(response), media_type="application/xml")

@app.post("/voice/financial/process")
async def process_financial_request(
    request: Request,
    db: Session = Depends(get_db),
    SpeechResult: Optional[str] = Form(None),
    CallSid: Optional[str] = Form(None)
):
    """Process financial services customer requests"""
    try:
        if not SpeechResult or not CallSid:
            response = VoiceResponse()
            response.say("I'm sorry, I didn't catch that. Could you please repeat that?")
            response.gather(
                input='speech',
                action='/voice/financial/process',
                method='POST'
            )
            return Response(content=str(response), media_type="application/xml")
        
        logger.info(f"Financial speech: {SpeechResult}")
        
        # Handle after-hours inquiry
        reply, is_complete = await financial_service.handle_after_hours_inquiry(
            db, SpeechResult, CallSid
        )
        
        response = VoiceResponse()
        response.say(reply, voice='Polly.Joanna')
        
        if not is_complete:
            # Continue gathering information
            response.gather(
                input='speech',
                action='/voice/financial/process',
                method='POST'
            )
        
        return Response(content=str(response), media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Error processing financial request: {e}")
        response = VoiceResponse()
        response.say("I apologize for the technical difficulty. Please call back during our business hours and our team will be happy to assist you.")
        return Response(content=str(response), media_type="application/xml")

# Admin/Management endpoints
@app.get("/admin/reservations")
async def get_reservations(db: Session = Depends(get_db)):
    """Get all reservations"""
    from app.models.database import Reservation
    reservations = db.query(Reservation).order_by(Reservation.created_at.desc()).limit(50).all()
    return {
        "total": len(reservations),
        "reservations": [
            {
                "id": r.id,
                "name": r.customer_name,
                "phone": r.phone,
                "date": str(r.reservation_date),
                "time": str(r.reservation_time),
                "party_size": r.party_size,
                "status": r.status.value,
                "created_at": str(r.created_at)
            } for r in reservations
        ]
    }

@app.get("/admin/inquiries")
async def get_inquiries(db: Session = Depends(get_db)):
    """Get all financial inquiries"""
    from app.models.database import FinancialInquiry
    inquiries = db.query(FinancialInquiry).order_by(FinancialInquiry.created_at.desc()).limit(50).all()
    return {
        "total": len(inquiries),
        "inquiries": [
            {
                "id": i.id,
                "name": i.customer_name,
                "phone": i.phone,
                "reason": i.reason,
                "priority": i.priority.value,
                "call_time": str(i.call_time),
                "follow_up_completed": i.follow_up_completed
            } for i in inquiries
        ]
    }

@app.get("/admin/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get system statistics"""
    from app.models.database import Reservation, FinancialInquiry
    from sqlalchemy import func
    
    today = func.date('now')
    
    reservation_count = db.query(Reservation).count()
    inquiry_count = db.query(FinancialInquiry).count()
    
    return {
        "total_reservations": reservation_count,
        "total_inquiries": inquiry_count,
        "system_status": "operational",
        "version": "1.0.0"
    }

# Development endpoints (remove in production)
@app.get("/test/voice")
async def test_voice():
    """Test voice endpoint"""
    return {"message": "Voice endpoints operational"}

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
