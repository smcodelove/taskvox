# FILE: migrate_to_whitelabel.py
# COPY-PASTE THIS COMPLETE FILE AND RUN: python migrate_to_whitelabel.py

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://taskvox_user:taskvox_password@localhost:5432/taskvox_db")

def migrate_database():
    """Migrate database columns to white-label names"""
    print("🔄 Starting white-label database migration...")
    
    try:
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as connection:
            # Start transaction
            trans = connection.begin()
            
            try:
                print("📋 Step 1: Renaming User table columns...")
                
                # Check if old column exists before renaming
                result = connection.execute(text("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'elevenlabs_api_key'
                """))
                
                if result.fetchone():
                    # Rename elevenlabs_api_key → voice_api_key
                    connection.execute(text("""
                        ALTER TABLE users 
                        RENAME COLUMN elevenlabs_api_key TO voice_api_key
                    """))
                    print("✅ Users table: elevenlabs_api_key → voice_api_key")
                else:
                    print("⚠️  Users table: elevenlabs_api_key column not found (already migrated?)")
                
                print("📋 Step 2: Renaming Agent table columns...")
                
                # Check if old column exists
                result = connection.execute(text("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'agents' AND column_name = 'elevenlabs_agent_id'
                """))
                
                if result.fetchone():
                    # Rename elevenlabs_agent_id → external_agent_id
                    connection.execute(text("""
                        ALTER TABLE agents 
                        RENAME COLUMN elevenlabs_agent_id TO external_agent_id
                    """))
                    print("✅ Agents table: elevenlabs_agent_id → external_agent_id")
                else:
                    print("⚠️  Agents table: elevenlabs_agent_id column not found (already migrated?)")
                
                print("📋 Step 3: Renaming Conversations table columns...")
                
                # Check if old column exists
                result = connection.execute(text("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'conversations' AND column_name = 'elevenlabs_conversation_id'
                """))
                
                if result.fetchone():
                    # Rename elevenlabs_conversation_id → external_conversation_id
                    connection.execute(text("""
                        ALTER TABLE conversations 
                        RENAME COLUMN elevenlabs_conversation_id TO external_conversation_id
                    """))
                    print("✅ Conversations table: elevenlabs_conversation_id → external_conversation_id")
                else:
                    print("⚠️  Conversations table: elevenlabs_conversation_id column not found (already migrated?)")
                
                # Commit transaction
                trans.commit()
                print("\n🎉 White-label migration completed successfully!")
                print("✅ All ElevenLabs references hidden from database schema")
                
            except Exception as e:
                # Rollback on error
                trans.rollback()
                print(f"\n❌ Migration failed: {e}")
                print("🔄 All changes rolled back")
                raise
                
    except Exception as e:
        print(f"💥 Database connection error: {e}")
        sys.exit(1)

def verify_migration():
    """Verify migration was successful"""
    print("\n🔍 Verifying migration...")
    
    try:
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as connection:
            # Check new column names exist
            tables_to_check = [
                ("users", "voice_api_key"),
                ("agents", "external_agent_id"), 
                ("conversations", "external_conversation_id")
            ]
            
            all_good = True
            
            for table_name, column_name in tables_to_check:
                result = connection.execute(text(f"""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = '{table_name}' AND column_name = '{column_name}'
                """))
                
                if result.fetchone():
                    print(f"✅ {table_name}.{column_name} exists")
                else:
                    print(f"❌ {table_name}.{column_name} missing")
                    all_good = False
            
            if all_good:
                print("\n🎯 Migration verification: SUCCESS!")
                print("✅ All white-label columns are in place")
            else:
                print("\n⚠️  Migration verification: ISSUES FOUND")
                
    except Exception as e:
        print(f"❌ Verification error: {e}")

if __name__ == "__main__":
    print("🚀 TasKvox AI - White-Label Database Migration")
    print("=" * 50)
    
    # Confirm before proceeding
    confirm = input("\n⚠️  This will rename database columns. Continue? (y/N): ")
    
    if confirm.lower() != 'y':
        print("❌ Migration cancelled")
        sys.exit(0)
    
    # Run migration
    migrate_database()
    
    # Verify results
    verify_migration()
    
    print("\n🎉 White-label setup complete!")
    print("📋 Next steps:")
    print("   1. Update your models.py with new field names")
    print("   2. Update your routers with new field references")
    print("   3. Restart your application")
    print("\n✨ Your TasKvox AI is now fully white-labeled!")