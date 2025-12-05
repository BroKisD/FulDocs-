import sqlite3
import os
import hashlib

def list_users():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("\nCurrent Users:")
    print("-" * 70)
    print(f"{'ID':<5} {'Email':<30} {'Name':<20} {'Role':<10} Has Password")
    print("-" * 70)
    
    # Get list of columns to check if password exists
    cursor.execute("PRAGMA table_info(Users)")
    columns = [column[1] for column in cursor.fetchall()]
    has_password = 'password' in columns
    
    if has_password:
        cursor.execute("SELECT id, email, name, role, password IS NOT NULL as has_password FROM Users")
    else:
        cursor.execute("SELECT id, email, name, role, 0 as has_password FROM Users")
    
    users = cursor.fetchall()
    
    for user in users:
        user_id = user['id']
        email = user['email']
        name = user['name'] if 'name' in user.keys() and user['name'] else ''
        role = user['role']
        has_pwd = 'has_password' in user and user['has_password']
        print(f"{user_id:<5} {email:<30} {name:<20} {role:<10} {'Yes' if has_pwd else 'No'}")
    
    conn.close()
    return users, has_password

def hash_password(password):
    """Hash a password using the same method as in app.py"""
    import os
    salt = os.urandom(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt.hex() + pwd_hash.hex()

def reset_password(user_id, new_password):
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        hashed_password = hash_password(new_password)
        cursor.execute("UPDATE Users SET password = ? WHERE id = ?", 
                      (hashed_password, user_id))
        conn.commit()
        print(f"Password updated for user ID {user_id}")
        return True
    except Exception as e:
        print(f"Error updating password: {e}")
        return False
    finally:
        conn.close()

def add_password_column():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE Users ADD COLUMN password TEXT")
        conn.commit()
        print("\nAdded 'password' column to Users table")
        return True
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            return True  # Column already exists
        print(f"Error adding password column: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("User Management Utility")
    print("=" * 70)
    
    # List all users and check if password column exists
    users, has_password = list_users()
    
    if not has_password:
        print("\nNo password column found in Users table.")
        response = input("Do you want to add the password column? (y/n): ")
        if response.lower() == 'y':
            if add_password_column():
                has_password = True
            else:
                print("Failed to add password column. Exiting.")
                exit(1)
        else:
            print("Cannot proceed without password column. Exiting.")
            exit(1)
    
    # Ask if user wants to reset passwords
    response = input("\nDo you want to reset passwords for all users to '77777777'? (y/n): ")
    
    if response.lower() == 'y':
        for user in users:
            reset_password(user['id'], '77777777')
        print("\nAll user passwords have been reset to '77777777'")
    else:
        print("\nPassword reset cancelled.")
