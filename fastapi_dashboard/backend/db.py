"""
Database configuration for FastAPI using SQLAlchemy.

This module sets up the SQLAlchemy engine, session, and base class for database operations.
Supports PostgreSQL with SSL (required for Supabase).

SETUP INSTRUCTIONS:

1. Local Development (.env file):
   Create a .env file in the fastapi_dashboard directory:
   
   DATABASE_URL=postgresql://user:password@localhost:5432/coros_fit?sslmode=require
   
   For local PostgreSQL without SSL:
   DATABASE_URL=postgresql://user:password@localhost:5432/coros_fit
   
   For Supabase (local or cloud):
   DATABASE_URL=postgresql://postgres:[YOUR_PASSWORD]@[YOUR_PROJECT].supabase.co:5432/postgres?sslmode=require
   
   ⚠️  IMPORTANT: If your password contains special characters (@, #, %, etc.), 
   you must URL-encode them:
   - @ becomes %40
   - # becomes %23
   - % becomes %25
   - etc.
   
   Example: If password is "pass@word", use "pass%40word"

2. Render.com Deployment:
   In your Render dashboard, go to your service → Environment:
   
   Add environment variable:
   Key: DATABASE_URL
   Value: postgresql://user:password@host:5432/dbname?sslmode=require
   
   For Supabase on Render:
   Value: postgresql://postgres:[PASSWORD]@[PROJECT].supabase.co:5432/postgres?sslmode=require
   
   ⚠️  IMPORTANT: URL-encode special characters in passwords (@ → %40, # → %23, etc.)
   
   Note: If your DATABASE_URL already includes ?sslmode=require, it will be preserved.
         If not, it will be automatically added for Supabase compatibility.

3. Testing the Connection:
   After setting DATABASE_URL, test the connection:
   curl http://localhost:8000/api/db-test
   
   Should return: {"db_connected": true}

Environment Variables:
    DATABASE_URL: PostgreSQL connection string
        Format: postgresql://[user]:[password]@[host]:[port]/[database][?sslmode=require]
        SSL mode is automatically added if missing (required for Supabase)
"""

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import logging
from typing import Generator, Tuple

# Configure logging
logger = logging.getLogger(__name__)

# Get DATABASE_URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

# Create SQLAlchemy engine
# If DATABASE_URL is not set, create a None engine (database features will be disabled)
if DATABASE_URL:
    # Ensure SSL mode is set for Supabase compatibility
    # If sslmode is not in the URL, add it
    if "sslmode=" not in DATABASE_URL:
        separator = "&" if "?" in DATABASE_URL else "?"
        DATABASE_URL = f"{DATABASE_URL}{separator}sslmode=require"
    
    engine = create_engine(
        DATABASE_URL,
        pool_size=5,           # Small footprint for free tier
        max_overflow=10,        # Maximum overflow connections
        pool_pre_ping=True,     # Verify connections before using them
        echo=False              # Set to True for SQL query logging (useful for debugging)
    )
    logger.info("Database engine created successfully")
else:
    engine = None
    logger.warning("DATABASE_URL not set. Database features will be disabled.")

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) if engine else None

# Create Base class for declarative models
Base = declarative_base()


def get_db() -> Generator:
    """
    Dependency function for FastAPI to get database session.
    
    Usage in FastAPI endpoints:
        from fastapi import Depends
        from .db import get_db
        from sqlalchemy.orm import Session
        
        @app.get("/api/endpoint")
        async def my_endpoint(db: Session = Depends(get_db)):
            # Use db session here
            pass
    """
    if SessionLocal is None:
        raise RuntimeError("Database not configured. Set DATABASE_URL environment variable.")
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_db_connection() -> Tuple[bool, str]:
    """
    Test database connection by executing SELECT 1.
    
    Returns:
        Tuple of (success: bool, error_message: str)
        If success is True, error_message will be empty string.
        If success is False, error_message will contain the error details.
    """
    if engine is None:
        error_msg = "Database engine not available. DATABASE_URL not set."
        logger.warning(error_msg)
        return False, error_msg
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        logger.info("Database connection test successful")
        return True, ""
    except Exception as e:
        error_msg = f"Database connection test failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg
