import sqlite3
import hashlib
import os

def hash_password(password):
    """Hash a password using the same method as in app.py"""
    salt = os.urandom(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt.hex() + pwd_hash.hex()

def update_user_passwords():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Check if password column exists
        cursor.execute("PRAGMA table_info(Users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'password' not in columns:
            print("Adding password column to Users table...")
            cursor.execute("ALTER TABLE Users ADD COLUMN password TEXT")
            conn.commit()
        
        # Update all users with the new password
        new_password = '77777777'
        hashed_password = hash_password(new_password)
        
        cursor.execute("UPDATE Users SET password = ?", (hashed_password,))
        conn.commit()
        
        # Verify the update
        cursor.execute("SELECT id, email, name, role FROM Users")
        users = cursor.fetchall()
        
        print("\nUpdated user passwords:")
        print("-" * 70)
        print(f"{'ID':<5} {'Email':<30} {'Name':<20} {'Role':<10}")
        print("-" * 70)
        
        for user in users:
            print(f"{user['id']:<5} {user['email']:<30} {user.get('name', ''):<20} {user['role']:<10}")
            
        print("\nAll user passwords have been reset to '77777777'")
        
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    print("Updating all user passwords to '77777777'...")
    update_user_passwords()
