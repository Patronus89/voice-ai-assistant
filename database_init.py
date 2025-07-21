#!/usr/bin/env python3
"""Database initialization script"""

from app.models.database import create_tables, init_sample_data
from config.settings import settings

def main():
    print("Initializing Voice AI Assistant database...")
    
    try:
        create_tables()
        print("✅ Database tables created successfully")
        
        init_sample_data()
        print("✅ Sample data initialized")
        
        print("\n🎉 Database setup complete!")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()
