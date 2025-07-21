from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, Date, Time, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from datetime import datetime, date, time
import enum

from config.settings import settings

# Database setup
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Enums
class ReservationStatus(enum.Enum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"

class InquiryPriority(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

# Models
class Reservation(Base):
    __tablename__ = "reservations"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(100), nullable=True)
    reservation_date = Column(Date, nullable=False)
    reservation_time = Column(Time, nullable=False)
    party_size = Column(Integer, nullable=False)
    special_requests = Column(Text, nullable=True)
    status = Column(Enum(ReservationStatus), default=ReservationStatus.CONFIRMED)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class MenuItem(Base):
    __tablename__ = "menu_items"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(String(20), nullable=False)  # Store as string for flexibility
    category = Column(String(50), nullable=False)
    allergens = Column(Text, nullable=True)  # JSON string of allergens
    available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

class FinancialInquiry(Base):
    __tablename__ = "financial_inquiries"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(100), nullable=True)
    reason = Column(Text, nullable=False)
    priority = Column(Enum(InquiryPriority), default=InquiryPriority.MEDIUM)
    call_time = Column(DateTime, default=func.now())
    follow_up_completed = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())

class CallSession(Base):
    __tablename__ = "call_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    call_sid = Column(String(100), unique=True, nullable=False)
    session_data = Column(Text, nullable=True)  # JSON string
    call_type = Column(String(20), nullable=False)  # 'restaurant' or 'financial'
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

# Database functions
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    Base.metadata.create_all(bind=engine)

def init_sample_data():
    """Initialize database with sample menu items"""
    db = SessionLocal()
    try:
        # Check if menu items already exist
        if db.query(MenuItem).count() > 0:
            return
        
        # Sample menu items
        menu_items = [
            MenuItem(
                name="Grilled Salmon",
                description="Fresh Atlantic salmon with lemon herb butter",
                price="$24.99",
                category="Main Course",
                allergens="fish"
            ),
            MenuItem(
                name="Caesar Salad",
                description="Romaine lettuce, parmesan cheese, croutons, Caesar dressing",
                price="$12.99",
                category="Appetizer",
                allergens="dairy, gluten"
            ),
            MenuItem(
                name="Chocolate Cake",
                description="Rich chocolate cake with vanilla ice cream",
                price="$8.99",
                category="Dessert",
                allergens="dairy, eggs, gluten"
            )
        ]
        
        for item in menu_items:
            db.add(item)
        
        db.commit()
        print("Sample menu items added to database")
        
    except Exception as e:
        print(f"Error initializing sample data: {e}")
        db.rollback()
    finally:
        db.close()