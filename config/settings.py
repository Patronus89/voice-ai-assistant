import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

class Settings:
    # Twilio Configuration
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "")
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./voiceai.db")
    
    # Email Configuration
    SENDGRID_API_KEY: str = os.getenv("SENDGRID_API_KEY", "")
    FROM_EMAIL: str = os.getenv("FROM_EMAIL", "")
    STAFF_EMAIL: str = os.getenv("STAFF_EMAIL", "")
    
    # Business Configuration
    RESTAURANT_NAME: str = os.getenv("RESTAURANT_NAME", "Restaurant")
    RESTAURANT_PHONE: str = os.getenv("RESTAURANT_PHONE", "")
    CREDIT_UNION_NAME: str = os.getenv("CREDIT_UNION_NAME", "Credit Union")
    
    # Business Hours (24-hour format)
    BUSINESS_HOURS_START: int = int(os.getenv("BUSINESS_HOURS_START", "9"))
    BUSINESS_HOURS_END: int = int(os.getenv("BUSINESS_HOURS_END", "17"))
    ONCALL_STAFF_PHONE: str = os.getenv("ONCALL_STAFF_PHONE", "")
    
    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"

settings = Settings()