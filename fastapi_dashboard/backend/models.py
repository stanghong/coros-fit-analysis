"""
SQLAlchemy ORM models for the swimming workout dashboard.

Models:
    - User: Stores user information linked to Strava athlete ID
    - StravaToken: Stores OAuth tokens for Strava integration
    - Activity: Stores Strava activity data
"""

from sqlalchemy import Column, BigInteger, String, Integer, Float, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import os

from db import Base, engine


class User(Base):
    """User model linked to Strava athlete ID."""
    
    __tablename__ = "users"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    strava_athlete_id = Column(BigInteger, unique=True, nullable=False, index=True)
    strava_username = Column(String, nullable=True)  # Strava username
    strava_firstname = Column(String, nullable=True)  # Strava first name
    strava_lastname = Column(String, nullable=True)  # Strava last name
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    strava_tokens = relationship("StravaToken", back_populates="user", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, strava_athlete_id={self.strava_athlete_id}, username={self.strava_username})>"


class StravaToken(Base):
    """Strava OAuth tokens for a user."""
    
    __tablename__ = "strava_tokens"
    
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=False)
    expires_at = Column(BigInteger, nullable=False)  # Unix timestamp
    scope = Column(String, nullable=True)  # OAuth scopes (e.g., "activity:read_all,profile:read_all")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="strava_tokens")
    
    def __repr__(self):
        return f"<StravaToken(user_id={self.user_id}, expires_at={self.expires_at})>"


class Activity(Base):
    """Strava activity data."""
    
    __tablename__ = "activities"
    
    id = Column(BigInteger, primary_key=True)  # Strava activity ID
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    sport_type = Column(String, nullable=True, index=True)  # Strava sport_type (preferred: "Swim", "Run", "Ride", "OpenWaterSwim", etc.)
    type = Column(String, nullable=True)  # Activity type (fallback: "Swim", "Run", "Bike")
    start_date = Column(DateTime(timezone=True), nullable=True)  # Activity start time
    distance_m = Column(Float, nullable=True)  # Distance in meters
    moving_time_s = Column(Integer, nullable=True)  # Moving time in seconds
    elapsed_time_s = Column(Integer, nullable=True)  # Elapsed time in seconds
    average_heartrate = Column(Float, nullable=True)  # Average heart rate (bpm)
    max_heartrate = Column(Float, nullable=True)  # Max heart rate (bpm)
    total_elevation_gain = Column(Float, nullable=True)  # Elevation gain in meters
    raw_json = Column(JSON, nullable=True)  # Full Strava API response as JSON
    fetched_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)  # When we fetched this from Strava
    
    # Relationships
    user = relationship("User", back_populates="activities")
    
    def __repr__(self):
        return f"<Activity(id={self.id}, user_id={self.user_id}, sport_type={self.sport_type}, type={self.type})>"


def init_db():
    """
    Initialize database by creating all tables.
    
    This function should only be called when DB_AUTO_CREATE=true is set
    in environment variables to prevent accidental table creation in production.
    
    Usage:
        Set DB_AUTO_CREATE=true in your .env file or environment variables,
        then call this function at application startup.
    """
    if engine is None:
        raise RuntimeError("Database engine not available. Set DATABASE_URL environment variable.")
    
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")


def check_db_status():
    """
    Check database status by attempting to query the users table.
    
    Returns:
        dict with status information:
        - tables_exist: bool
        - user_count: int (if tables exist)
        - error: str (if error occurred)
    """
    if engine is None:
        return {
            "tables_exist": False,
            "error": "Database not configured. Set DATABASE_URL environment variable."
        }
    
    try:
        from sqlalchemy import inspect, text
        from sqlalchemy.orm import Session
        
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        
        # Check if our tables exist
        required_tables = {"users", "strava_tokens", "activities"}
        tables_exist = required_tables.issubset(set(table_names))
        
        if not tables_exist:
            return {
                "tables_exist": False,
                "existing_tables": table_names,
                "required_tables": list(required_tables),
                "error": f"Missing tables. Found: {table_names}, Required: {list(required_tables)}"
            }
        
        # If tables exist, try to count users
        with Session(engine) as session:
            result = session.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar()
        
        return {
            "tables_exist": True,
            "user_count": user_count,
            "existing_tables": table_names
        }
    
    except Exception as e:
        return {
            "tables_exist": False,
            "error": str(e)
        }
