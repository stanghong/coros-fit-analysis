"""
Migration script to add athlete info columns to users table.

This script adds the new columns (strava_username, strava_firstname, strava_lastname, updated_at)
to the existing users table without dropping it.

Usage:
    python -m backend.migrate_add_athlete_info
    Or set DB_AUTO_MIGRATE=true and it will run automatically on startup
"""

import os
from sqlalchemy import text
from db import engine

def migrate_add_athlete_info():
    """Add athlete info columns to users table if they don't exist."""
    if engine is None:
        print("ERROR: Database engine not available. Set DATABASE_URL environment variable.")
        return False
    
    try:
        with engine.connect() as conn:
            # Start a transaction
            trans = conn.begin()
            
            try:
                # Check if columns exist
                check_query = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' 
                    AND column_name IN ('strava_username', 'strava_firstname', 'strava_lastname', 'updated_at')
                """)
                result = conn.execute(check_query)
                existing_columns = {row[0] for row in result}
                
                # Add columns that don't exist
                if 'strava_username' not in existing_columns:
                    print("Adding strava_username column...")
                    conn.execute(text("ALTER TABLE users ADD COLUMN strava_username VARCHAR"))
                
                if 'strava_firstname' not in existing_columns:
                    print("Adding strava_firstname column...")
                    conn.execute(text("ALTER TABLE users ADD COLUMN strava_firstname VARCHAR"))
                
                if 'strava_lastname' not in existing_columns:
                    print("Adding strava_lastname column...")
                    conn.execute(text("ALTER TABLE users ADD COLUMN strava_lastname VARCHAR"))
                
                if 'updated_at' not in existing_columns:
                    print("Adding updated_at column...")
                    conn.execute(text("""
                        ALTER TABLE users 
                        ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    """))
                    
                    # Create trigger function if it doesn't exist
                    conn.execute(text("""
                        CREATE OR REPLACE FUNCTION update_updated_at_column()
                        RETURNS TRIGGER AS $$
                        BEGIN
                            NEW.updated_at = CURRENT_TIMESTAMP;
                            RETURN NEW;
                        END;
                        $$ language 'plpgsql';
                    """))
                    
                    # Create trigger
                    conn.execute(text("""
                        DROP TRIGGER IF EXISTS update_users_updated_at ON users;
                        CREATE TRIGGER update_users_updated_at
                            BEFORE UPDATE ON users
                            FOR EACH ROW
                            EXECUTE FUNCTION update_updated_at_column();
                    """))
                
                # Commit transaction
                trans.commit()
                print("✅ Migration completed successfully!")
                return True
                
            except Exception as e:
                trans.rollback()
                print(f"ERROR: Migration failed: {str(e)}")
                import traceback
                traceback.print_exc()
                return False
                
    except Exception as e:
        print(f"ERROR: Failed to connect to database: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    migrate_add_athlete_info()
