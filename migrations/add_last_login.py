import sqlite3
import os
from datetime import datetime

def migrate():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if last_login column exists
        cursor.execute("PRAGMA table_info(Users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'last_login' not in columns:
            print("Adding last_login column to Users table...")
            cursor.execute('''
                ALTER TABLE Users 
                ADD COLUMN last_login TIMESTAMP
            ''')
            conn.commit()
            print("Migration completed successfully!")
        else:
            print("last_login column already exists. No migration needed.")
            
    except sqlite3.Error as e:
        print(f"Error during migration: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    migrate()
