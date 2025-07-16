import sqlite3
import os
from datetime import datetime

def create_databases():
    """Create all required database tables with proper schema"""
    
    # Ensure db directory exists
    os.makedirs("db", exist_ok=True)
    
    databases = {
        'new_faces': {
            'table': 'faces',
            'schema': '''
                CREATE TABLE IF NOT EXISTS faces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_path TEXT NOT NULL,
                    encoding BLOB NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''
        },
        'old_faces': {
            'table': 'faces', 
            'schema': '''
                CREATE TABLE IF NOT EXISTS faces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_path TEXT NOT NULL,
                    encoding BLOB NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''
        },
        'face_master': {
            'table': 'people',
            'schema': '''
                CREATE TABLE IF NOT EXISTS people (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL DEFAULT 'Unknown',  # partyt to be delete
                    image_path TEXT,
                    encoding BLOB NOT NULL,    # partyt to be delete
                    visits INTEGER DEFAULT 1,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''
        }
    }
    
    print("🏗️ Creating/updating databases...")
    
    for db_name, config in databases.items():
        try:
            db_path = f"./db/{db_name}.db"
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check if table exists and get its schema
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{config['table']}'")
            table_exists = cursor.fetchone() is not None
            
            if table_exists:
                # Get current columns
                cursor.execute(f"PRAGMA table_info({config['table']})")
                existing_columns = {col[1]: col[2] for col in cursor.fetchall()}
                
                # Add missing columns based on database type
                if db_name in ['new_faces', 'old_faces']:
                    if 'timestamp' not in existing_columns:
                        print(f"  📝 Adding timestamp column to {db_name}")
                        cursor.execute(f"ALTER TABLE {config['table']} ADD COLUMN timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                
                elif db_name == 'face_master':
                    # Check and add missing columns for face_master
                    missing_columns = []
                    
                    if 'first_seen' not in existing_columns:
                        missing_columns.append("first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                    
                    if 'last_seen' not in existing_columns:
                        missing_columns.append("last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                    
                    if 'visits' not in existing_columns:
                        missing_columns.append("visits INTEGER DEFAULT 1")
                    
                    if 'name' not in existing_columns:
                        missing_columns.append("name TEXT DEFAULT 'Unknown'")
                    
                    for col_def in missing_columns:
                        col_name = col_def.split()[0]
                        print(f"  📝 Adding {col_name} column to {db_name}")
                        cursor.execute(f"ALTER TABLE {config['table']} ADD COLUMN {col_def}")
                    
                    # Update existing records with NULL values
                    cursor.execute(f"""
                        UPDATE {config['table']} 
                        SET first_seen = CURRENT_TIMESTAMP 
                        WHERE first_seen IS NULL
                    """)
                    cursor.execute(f"""
                        UPDATE {config['table']} 
                        SET last_seen = CURRENT_TIMESTAMP 
                        WHERE last_seen IS NULL
                    """)
                    cursor.execute(f"""
                        UPDATE {config['table']} 
                        SET visits = 1 
                        WHERE visits IS NULL
                    """)
                    cursor.execute(f"""
                        UPDATE {config['table']} 
                        SET name = 'Unknown' 
                        WHERE name IS NULL
                    """)
            
            # Create table with full schema (will be ignored if exists)
            cursor.execute(config['schema'])
            
            conn.commit()
            conn.close()
            
            print(f"✅ Database {db_name}.db ready")
            
        except Exception as e:
            print(f"❌ Error setting up {db_name}: {e}")
            if conn:
                conn.close()
    
    print("🎯 All databases created/updated successfully!")

def verify_databases():
    """Verify all databases have correct schema"""
    print("\n🔍 Verifying database schemas...")
    
    expected_schemas = {
        'new_faces': ['id', 'image_path', 'encoding', 'timestamp'],
        'old_faces': ['id', 'image_path', 'encoding', 'timestamp'],
        'face_master': ['id', 'name', 'image_path', 'encoding', 'visits', 'first_seen', 'last_seen']
    }
    
    for db_name, expected_cols in expected_schemas.items():
        try:
            conn = sqlite3.connect(f"./db/{db_name}.db")
            cursor = conn.cursor()
            
            table_name = 'people' if db_name == 'face_master' else 'faces'
            cursor.execute(f"PRAGMA table_info({table_name})")
            actual_cols = [col[1] for col in cursor.fetchall()]
            
            missing_cols = set(expected_cols) - set(actual_cols)
            extra_cols = set(actual_cols) - set(expected_cols)
            
            if not missing_cols and not extra_cols:
                print(f"✅ {db_name}: Schema correct")
            else:
                if missing_cols:
                    print(f"⚠️ {db_name}: Missing columns: {missing_cols}")
                if extra_cols:
                    print(f"ℹ️ {db_name}: Extra columns: {extra_cols}")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ Error verifying {db_name}: {e}")

def reset_databases():
    """Delete and recreate all databases (WARNING: This will delete all data!)"""
    print("⚠️ RESETTING ALL DATABASES - THIS WILL DELETE ALL DATA!")
    
    for db_name in ['new_faces', 'old_faces', 'face_master']:
        db_path = f"./db/{db_name}.db"
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"🗑️ Deleted {db_name}.db")
    
    create_databases()
    print("🔄 Databases reset complete!")

if __name__ == "__main__":
    print("🚀 Database Setup Utility")
    print("=" * 40)
    
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'reset':
            response = input("Are you sure you want to reset all databases? (yes/no): ")
            if response.lower() == 'yes':
                reset_databases()
            else:
                print("❌ Reset cancelled")
        elif sys.argv[1] == 'verify':
            verify_databases()
        else:
            print("Usage: python creating_db.py [reset|verify]")
    else:
        create_databases()
        verify_databases()