"""
Flask-based educational content platform with modern UI and enhanced features.

New features added:
- User profiles with contribution statistics
- Upvote/downvote system for answers
- Bookmark functionality
- Rich text editor support
- Better search with relevance scoring
- Activity tracking
- Notification system
"""

import os
import json
import sqlite3
from datetime import datetime
from flask import (Flask, render_template, request, redirect,
                   url_for, session, send_from_directory, flash, jsonify, abort)
from werkzeug.utils import secure_filename
import os
from db_utils import get_db_connection
from gemini_chat import get_chat_response


app = Flask(__name__)
app.secret_key = 'replace_with_a_random_secret_key'

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size


# Database connection is now imported from db_utils


def init_db():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('PRAGMA foreign_keys = ON')
        
        # Users table with profile fields
        cursor.execute(
            '''CREATE TABLE IF NOT EXISTS Users (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   email TEXT NOT NULL UNIQUE,
                   role TEXT NOT NULL,
                   name TEXT,
                   bio TEXT,
                   avatar_url TEXT,
                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
               )''')

        # Add new columns to existing Users table if they don't exist
        cursor.execute("PRAGMA table_info(Users)")
        existing_cols = [row['name'] for row in cursor.fetchall()]
        
        if 'name' not in existing_cols:
            cursor.execute('ALTER TABLE Users ADD COLUMN name TEXT')
        if 'bio' not in existing_cols:
            cursor.execute('ALTER TABLE Users ADD COLUMN bio TEXT')
        if 'avatar_url' not in existing_cols:
            cursor.execute('ALTER TABLE Users ADD COLUMN avatar_url TEXT')
        if 'created_at' not in existing_cols:
            cursor.execute('ALTER TABLE Users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        if 'first_login' not in existing_cols:
            cursor.execute('ALTER TABLE Users ADD COLUMN first_login INTEGER DEFAULT 1')
            # Set first_login to 0 for existing users
            cursor.execute('UPDATE Users SET first_login = 0 WHERE first_login IS NULL')
            
        # Create Documents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                content TEXT,
                tags TEXT,
                file_path TEXT,
                user_id INTEGER NOT NULL,
                status TEXT DEFAULT 'Pending',
                verification_requested BOOLEAN DEFAULT 0,
                verified_by INTEGER,
                verified_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES Users(id),
                FOREIGN KEY (verified_by) REFERENCES Users(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                tags TEXT,
                status TEXT DEFAULT 'Open',
                file_path TEXT,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES Users (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                is_accepted BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES Users (id),
                FOREIGN KEY (question_id) REFERENCES Questions (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_type TEXT NOT NULL,
                item_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES Users (id),
                UNIQUE(user_id, item_type, item_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                answer_id INTEGER NOT NULL,
                vote_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES Users(id),
                FOREIGN KEY (answer_id) REFERENCES Answers(id),
                UNIQUE(user_id, answer_id)
            )
        ''')
        
        # Create Stars table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Stars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_type TEXT NOT NULL,
                item_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES Users(id),
                UNIQUE(user_id, item_type, item_id)
            )
        ''')
        
        # Create indexes after all tables are created
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_user ON Documents(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_questions_user ON Questions(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_answers_question ON Answers(question_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_answers_user ON Answers(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stars_user ON Stars(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stars_item ON Stars(item_type, item_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_votes_user ON Votes(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_votes_answer ON Votes(answer_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_bookmarks_user ON Bookmarks(user_id)')

        # Documents table
        cursor.execute(
            '''CREATE TABLE IF NOT EXISTS Documents (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   title TEXT NOT NULL,
                   description TEXT,
                   tags TEXT,
                   content TEXT,
                   status TEXT NOT NULL,
                   user_id INTEGER NOT NULL,
                   file_path TEXT,
                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                   updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                   views INTEGER DEFAULT 0,
                   FOREIGN KEY (user_id) REFERENCES Users(id)
               )''')

        cursor.execute("PRAGMA table_info(Documents)")
        existing_cols = [row['name'] for row in cursor.fetchall()]
        if 'file_path' not in existing_cols:
            cursor.execute('ALTER TABLE Documents ADD COLUMN file_path TEXT')
        if 'created_at' not in existing_cols:
            cursor.execute('ALTER TABLE Documents ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        if 'updated_at' not in existing_cols:
            cursor.execute('ALTER TABLE Documents ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        if 'views' not in existing_cols:
            cursor.execute('ALTER TABLE Documents ADD COLUMN views INTEGER DEFAULT 0')

        # Questions table
        cursor.execute(
            '''CREATE TABLE IF NOT EXISTS Questions (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   title TEXT NOT NULL,
                   description TEXT,
                   tags TEXT,
                   status TEXT NOT NULL,
                   user_id INTEGER NOT NULL,
                   file_path TEXT,
                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                   views INTEGER DEFAULT 0,
                   FOREIGN KEY (user_id) REFERENCES Users(id)
               )''')

        cursor.execute("PRAGMA table_info(Questions)")
        existing_cols = [row['name'] for row in cursor.fetchall()]
        if 'views' not in existing_cols:
            cursor.execute('ALTER TABLE Questions ADD COLUMN views INTEGER DEFAULT 0')

        # Answers table with votes
        cursor.execute(
            '''CREATE TABLE IF NOT EXISTS Answers (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   question_id INTEGER NOT NULL,
                   content TEXT NOT NULL,
                   user_id INTEGER NOT NULL,
                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                   upvotes INTEGER DEFAULT 0,
                   downvotes INTEGER DEFAULT 0,
                   is_accepted BOOLEAN DEFAULT 0,
                   FOREIGN KEY (question_id) REFERENCES Questions(id),
                   FOREIGN KEY (user_id) REFERENCES Users(id)
               )''')

        cursor.execute("PRAGMA table_info(Answers)")
        existing_cols = [row['name'] for row in cursor.fetchall()]
        if 'upvotes' not in existing_cols:
            cursor.execute('ALTER TABLE Answers ADD COLUMN upvotes INTEGER DEFAULT 0')
        if 'downvotes' not in existing_cols:
            cursor.execute('ALTER TABLE Answers ADD COLUMN downvotes INTEGER DEFAULT 0')
        if 'is_accepted' not in existing_cols:
            cursor.execute('ALTER TABLE Answers ADD COLUMN is_accepted BOOLEAN DEFAULT 0')

        # Votes table for tracking user votes
        cursor.execute(
            '''CREATE TABLE IF NOT EXISTS Votes (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   user_id INTEGER NOT NULL,
                   answer_id INTEGER NOT NULL,
                   vote_type TEXT NOT NULL,
                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                   FOREIGN KEY (user_id) REFERENCES Users(id),
                   FOREIGN KEY (answer_id) REFERENCES Answers(id),
                   UNIQUE(user_id, answer_id)
               )''')

        # Bookmarks table
        cursor.execute(
            '''CREATE TABLE IF NOT EXISTS Bookmarks (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   user_id INTEGER NOT NULL,
                   item_type TEXT NOT NULL,
                   item_id INTEGER NOT NULL,
                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                   FOREIGN KEY (user_id) REFERENCES Users(id),
                   UNIQUE(user_id, item_type, item_id)
               )''')

        # Notifications table
        cursor.execute(
            '''CREATE TABLE IF NOT EXISTS Notifications (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   user_id INTEGER NOT NULL,
                   message TEXT NOT NULL,
                   link TEXT,
                   is_read BOOLEAN DEFAULT 0,
                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                   FOREIGN KEY (user_id) REFERENCES Users(id)
               )''')

        # Seed users
        existing_users = cursor.execute('SELECT COUNT(*) AS count FROM Users').fetchone()['count']
        if existing_users == 0:
            users = [
                ('admin@university.edu', 'Admin', 'Admin User', 'Platform administrator'),
                ('professor@university.edu', 'Professor', 'Prof. Quan Le', 'HCE Professor'),
                ('student@university.edu', 'Student', 'Student', 'HCE student'),
            ]
            for email, role, name, bio in users:
                cursor.execute(
                    'INSERT INTO Users (email, role, name, bio) VALUES (?, ?, ?, ?)',
                    (email, role, name, bio))

        # Seed sample documents
        existing_docs = cursor.execute('SELECT COUNT(*) AS count FROM Documents').fetchone()['count']
        if existing_docs == 0:
            sample_docs = [
                ('3D Printing Tutorial', 'Comprehensive guide to 3D printing for beginners and enthusiasts',
                 '3d printing, maker, diy, tutorial', 'Learn the fundamentals of 3D printing, from choosing the right printer to troubleshooting common issues. This guide covers everything you need to know to get started with 3D printing.', 'Verified', 2, '100_3DPrintTutorial.html'),
                
                ('Arduino Basic Tutorial', 'Complete beginner\'s guide to Arduino programming and projects',
                 'arduino, electronics, iot, programming', 'Master the basics of Arduino with this hands-on tutorial. Learn about digital/analog I/O, sensors, and build your first projects with step-by-step instructions.', 'Verified', 2, '100_ArduinoBasicTutorial.html'),
                
                ('Blynk Basic Tutorial', 'Getting started with Blynk for IoT projects',
                 'blynk, iot, mobile app, arduino, esp8266', 'Learn how to use Blynk to create mobile apps for your IoT projects. This tutorial covers setting up Blynk with various microcontrollers and creating custom dashboards.', 'Verified', 2, '100_BlynkBasicTutorial.html'),
                
                ('ESP32 WiFi Tutorial', 'Complete guide to WiFi connectivity with ESP32',
                 'esp32, wifi, iot, arduino, networking', 'Master WiFi connectivity with ESP32 microcontrollers. This tutorial covers station mode, access point mode, and creating web servers with the ESP32.', 'Verified', 2, '100_ESP32WifiTutorial.html'),
                
                ('LoRA Simple Tutorial', 'Introduction to LoRa communication for IoT',
                 'lora, iot, wireless, arduino, communication', 'Learn how to implement long-range wireless communication using LoRa modules. This tutorial covers hardware setup, library usage, and practical examples.', 'Verified', 2, '100_LoRASimpleTutorial.html'),
                
                ('RS485 MUX Tutorial', 'Guide to using RS485 with multiplexers',
                 'rs485, mux, communication, industrial, arduino', 'Comprehensive guide to implementing RS485 communication with multiplexers for industrial and automation applications. Covers wiring, addressing, and protocol implementation.', 'Verified', 2, '200_RS485MUXTutorial.html')
            ]
            for title, description, tags, content, status, user_id, file_path in sample_docs:
                cursor.execute(
                    '''INSERT INTO Documents (title, description, tags, content, status, user_id, file_path, verification_requested, verified_by)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 1, 2)''',
                    (title, description, tags, content, status, user_id, file_path))

        # Seed sample questions
        existing_questions = cursor.execute('SELECT COUNT(*) FROM Questions').fetchone()[0]
        if existing_questions == 0:
            sample_questions = [
                ('How do I use Flask?', 'I am new to Flask and need help getting started.', 'flask, python', 'Open', 2, 'flask_help.pdf'),
                ('Database connection issue', 'I am having trouble connecting to my database.', 'database, sql', 'Open', 2, 'db_connection_guide.pdf'),
                ('Best practices for web development', 'What are some best practices for modern web development?', 'web, development', 'Open', 3, 'web_dev_best_practices.pdf')
            ]
            for title, description, tags, status, user_id, file_path in sample_questions:
                cursor.execute(
                    '''INSERT INTO Questions (title, description, tags, status, user_id, file_path)
                       VALUES (?, ?, ?, ?, ?, ?)''',
                    (title, description, tags, status, user_id, file_path))

        conn.commit()
        print("Database initialized successfully")
        
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


init_db()


@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('feed'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        if not email.endswith('@university.edu'):
            error = 'Please use your university email address.'
        else:
            conn = get_db_connection()
            user = conn.execute('SELECT * FROM Users WHERE email = ?', (email,)).fetchone()
            
            if user:
                # Check if this is the user's first login
                first_login = user['first_login'] if 'first_login' in user.keys() else 1
                
                # Update first_login status if it's their first login
                if first_login == 1:
                    conn.execute('UPDATE Users SET first_login = 0 WHERE id = ?', (user['id'],))
                    conn.commit()
                
                session['user_id'] = user['id']
                session['role'] = user['role']
                session['email'] = user['email']
                session['name'] = user['name'] or email.split('@')[0]
                
                if first_login == 1:
                    flash('Welcome to FulDocs! Let\'s get you started!', 'success')
                    return redirect(url_for('welcome_guide'))
                else:
                    flash('Welcome back!', 'success')
                    return redirect(url_for('feed'))
            else:
                error = 'No account found for this email.'
            conn.close()
    return render_template('login.html', error=error)


@app.route('/welcome')
def welcome_guide():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('welcome_guide.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/profile/<int:user_id>')
def profile(user_id: int):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM Users WHERE id = ?', (user_id,)).fetchone()
    
    if not user:
        conn.close()
        flash('User not found.', 'error')
        return redirect(url_for('feed'))
    
    # Get user's documents with star counts
    docs = conn.execute('''
        SELECT d.*, 
               (SELECT COUNT(*) FROM Stars WHERE item_type = 'document' AND item_id = d.id) as star_count
        FROM Documents d 
        WHERE d.user_id = ? 
        ORDER BY d.created_at DESC 
        LIMIT 10
    ''', (user_id,)).fetchall()
    
    # Get user's questions
    questions = conn.execute('''
        SELECT q.*, 
               (SELECT COUNT(*) FROM Answers a WHERE a.question_id = q.id) as answer_count
        FROM Questions q 
        WHERE q.user_id = ? 
        ORDER BY q.created_at DESC 
        LIMIT 10
    ''', (user_id,)).fetchall()
    
    # Get user's answers with star counts
    answers = conn.execute('''
        SELECT a.*, 
               (SELECT COUNT(*) FROM Stars WHERE item_type = 'answer' AND item_id = a.id) as star_count
        FROM Answers a 
        WHERE a.user_id = ? 
        ORDER BY a.created_at DESC 
        LIMIT 10
    ''', (user_id,)).fetchall()
    
    # Get user's answers count
    answers_count = conn.execute(
        'SELECT COUNT(*) as count FROM Answers WHERE user_id = ?',
        (user_id,)).fetchone()['count']
    
    # Calculate total stars received by user
    total_stars = conn.execute('''
        SELECT COUNT(*) as count 
        FROM Stars 
        WHERE item_id IN (
            SELECT id FROM Documents WHERE user_id = ?
            UNION ALL
            SELECT id FROM Answers WHERE user_id = ?
        )
    ''', (user_id, user_id)).fetchone()['count']
    
    conn.close()
    
    # Convert SQLite Row objects to dictionaries
    docs = [dict(doc) for doc in docs]
    questions = [dict(q) for q in questions]
    answers = [dict(a) for a in answers]
    
    stats = {
        'documents': len(docs),
        'questions': len(questions),
        'answers': answers_count,
        'total_stars': total_stars
    }
    
    return render_template('profile.html', user=user, stats=stats, docs=docs, questions=questions)


@app.route('/profile/edit', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        bio = request.form.get('bio', '').strip()
        
        conn.execute(
            'UPDATE Users SET name = ?, bio = ? WHERE id = ?',
            (name, bio, session['user_id']))
        conn.commit()
        session['name'] = name
        flash('Profile updated successfully!', 'success')
        conn.close()
        return redirect(url_for('profile', user_id=session['user_id']))
    
    user = conn.execute('SELECT * FROM Users WHERE id = ?', (session['user_id'],)).fetchone()
    conn.close()
    return render_template('edit_profile.html', user=user)


@app.route('/feed')
def feed():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Fetch verified documents and all questions with verification info and star counts
    docs = conn.execute(
        '''SELECT Documents.id AS id, Documents.title AS title,
                  Documents.description AS description,
                  Documents.tags AS tags,
                  Documents.status AS status,
                  Documents.views AS views,
                  Documents.verification_requested AS verification_requested,
                  Documents.verified_at AS verified_at,
                  Users.email AS author,
                  Users.name AS author_name,
                  Users.id AS author_id,
                  Documents.file_path AS file_path,
                  Documents.created_at AS created_at,
                  'Document' AS type,
                  (SELECT COUNT(*) FROM Stars WHERE item_type = 'document' AND item_id = Documents.id) AS star_count,
                  prof.id AS verified_by_id,
                  prof.name AS verified_by_name
           FROM Documents
           JOIN Users ON Documents.user_id = Users.id
           LEFT JOIN Users AS prof ON Documents.verified_by = prof.id
           WHERE Documents.status = 'Verified'
           ORDER BY Documents.created_at DESC''').fetchall()
    
    questions = conn.execute(
        '''SELECT Questions.id AS id, Questions.title AS title,
                  Questions.description AS description,
                  Questions.tags AS tags,
                  Questions.status AS status,
                  Questions.views AS views,
                  Users.email AS author,
                  Users.name AS author_name,
                  Users.id AS author_id,
                  Questions.file_path AS file_path,
                  Questions.created_at AS created_at,
                  'Question' AS type,
                  0 AS star_count,  -- Questions themselves aren't starred, only answers
                  (SELECT COUNT(*) FROM Answers a WHERE a.question_id = Questions.id) AS answer_count
           FROM Questions
           JOIN Users ON Questions.user_id = Users.id
           ORDER BY Questions.created_at DESC''').fetchall()
    
    conn.close()
    
    # Convert SQLite Row objects to dictionaries and combine
    items = []
    for doc in docs:
        doc_dict = dict(doc)
        doc_dict['user_id'] = doc_dict['author_id']  # Add user_id for consistency
        items.append(doc_dict)
    
    for question in questions:
        q_dict = dict(question)
        q_dict['user_id'] = q_dict['author_id']  # Add user_id for consistency
        items.append(q_dict)
    
    # Sort items by creation date
    items_sorted = sorted(items, key=lambda x: x['created_at'], reverse=True)
    
    return render_template('feed.html', items=items_sorted)


@app.route('/search', methods=['GET', 'POST'])
def search():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    results = []
    query = ''
    type_filter = 'All'
    status_filter = 'All'
    
    if request.method == 'POST':
        query = request.form.get('query', '').strip()
        type_filter = request.form.get('type_filter', 'All')
        status_filter = request.form.get('status_filter', 'All')
        
        conn = get_db_connection()
        result_rows = []
        
        if type_filter in ('All', 'Documents'):
            sql = '''SELECT Documents.id AS id, Documents.title AS title,
                            Documents.description AS description,
                            Documents.tags AS tags,
                            Documents.status AS status,
                            Documents.views AS views,
                            Users.email AS author,
                            Users.name AS author_name,
                            Users.id AS author_id,
                            Documents.file_path AS file_path,
                            Documents.created_at AS created_at,
                            'Document' AS type
                     FROM Documents
                     JOIN Users ON Documents.user_id = Users.id
                     WHERE (Documents.title LIKE ? OR Documents.tags LIKE ? OR Documents.description LIKE ?)'''
            params = [f'%{query}%', f'%{query}%', f'%{query}%'] if query else ['%%', '%%', '%%']
            if status_filter not in ('All', ''):
                sql += ' AND Documents.status = ?'
                params.append(status_filter)
            docs = conn.execute(sql, params).fetchall()
            result_rows.extend(docs)
        
        if type_filter in ('All', 'Questions'):
            sql = '''SELECT Questions.id AS id, Questions.title AS title,
                            Questions.description AS description,
                            Questions.tags AS tags,
                            Questions.status AS status,
                            Questions.views AS views,
                            Users.email AS author,
                            Users.name AS author_name,
                            Users.id AS author_id,
                            Questions.file_path AS file_path,
                            Questions.created_at AS created_at,
                            'Question' AS type,
                            (SELECT COUNT(*) FROM Answers WHERE question_id = Questions.id) AS answer_count
                     FROM Questions
                     JOIN Users ON Questions.user_id = Users.id
                     WHERE (Questions.title LIKE ? OR Questions.tags LIKE ? OR Questions.description LIKE ?)'''
            params = [f'%{query}%', f'%{query}%', f'%{query}%'] if query else ['%%', '%%', '%%']
            if status_filter not in ('All', ''):
                sql += ' AND Questions.status = ?'
                params.append(status_filter)
            qns = conn.execute(sql, params).fetchall()
            result_rows.extend(qns)
        
        results = sorted(result_rows, key=lambda r: r['created_at'] or '', reverse=True)
        conn.close()
    
    return render_template('search.html', results=results, query=query,
                           type_filter=type_filter, status_filter=status_filter)


@app.route('/post', methods=['GET', 'POST'])
def post_document():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        tags = request.form.get('tags', '').strip()
        content = request.form.get('content', '').strip()
        request_verification = request.form.get('request_verification') == 'on'
        professor_id = request.form.get('professor_id')
        
        uploaded_file = request.files.get('file')
        file_path = None
        if uploaded_file and uploaded_file.filename:
            filename = secure_filename(uploaded_file.filename)
            timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            filename = f"{timestamp}_{filename}"
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            uploaded_file.save(save_path)
            file_path = filename
        
        if title:
            if request_verification and professor_id:
                # Insert with verification request
                conn.execute(
                    '''INSERT INTO Documents (title, description, tags, content,
                                          status, user_id, file_path, verification_requested, verified_by)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (title, description, tags, content, 'Pending',
                     session['user_id'], file_path, 1, professor_id))
                flash('Document submitted with verification request!', 'success')
            else:
                # Insert without verification request
                conn.execute(
                    '''INSERT INTO Documents (title, description, tags, content,
                                          status, user_id, file_path)
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (title, description, tags, content, 'Pending',
                     session['user_id'], file_path))
                flash('Document submitted for review!', 'success')
            
            conn.commit()
            conn.close()
            return redirect(url_for('feed'))
    
    # Get list of professors for the dropdown
    professors = conn.execute(
        'SELECT id, name FROM Users WHERE role = "Professor" ORDER BY name'
    ).fetchall()
    conn.close()
    
    return render_template('post.html', professors=professors)


@app.route('/documents/<int:doc_id>')
def view_document(doc_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Get document with author info
    document_row = conn.execute('''
        SELECT d.*, u.email as author, u.name as author_name, u.id as author_id
        FROM Documents d
        JOIN Users u ON d.user_id = u.id
        WHERE d.id = ?
    ''', (doc_id,)).fetchone()
    
    if not document_row:
        conn.close()
        flash('Document not found.', 'error')
        return redirect(url_for('feed'))
    
    # Convert SQLite Row to dict
    document = dict(document_row)
    
    # Get star information
    is_starred = False
    star_count = 0
    
    if 'user_id' in session:
        # Check if current user has starred this document
        star = conn.execute(
            'SELECT id FROM Stars WHERE user_id = ? AND item_type = ? AND item_id = ?',
            (session['user_id'], 'document', doc_id)
        ).fetchone()
        is_starred = star is not None
        
        # Get total star count for this document
        star_count_result = conn.execute(
            'SELECT COUNT(*) as count FROM Stars WHERE item_type = ? AND item_id = ?',
            ('document', doc_id)
        ).fetchone()
        star_count = star_count_result['count'] if star_count_result else 0
    
    # Increment view count
    conn.execute('UPDATE Documents SET views = COALESCE(views, 0) + 1 WHERE id = ?', (doc_id,))
    conn.commit()
    
    conn.close()
    
    return render_template('document_detail.html', 
                         document=document,
                         is_starred=is_starred,
                         star_count=star_count)


@app.route('/ask', methods=['GET', 'POST'])
def ask():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        tags = request.form.get('tags', '').strip()
        
        uploaded_file = request.files.get('file')
        file_path = None
        if uploaded_file and uploaded_file.filename:
            filename = secure_filename(uploaded_file.filename)
            timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            filename = f"{timestamp}_{filename}"
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            uploaded_file.save(save_path)
            file_path = filename
        
        if title:
            conn = get_db_connection()
            conn.execute(
                '''INSERT INTO Questions (title, description, tags, status, user_id, file_path)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (title, description, tags, 'Pending', session['user_id'], file_path))
            conn.commit()
            conn.close()
            flash('Question posted successfully!', 'success')
            return redirect(url_for('feed'))
    
    return render_template('ask.html')


@app.route('/questions/<int:question_id>', methods=['GET', 'POST'])
def question_detail(question_id: int):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Increment view count
    conn.execute('UPDATE Questions SET views = views + 1 WHERE id = ?', (question_id,))
    conn.commit()
    
    question = conn.execute(
        '''SELECT Questions.*, Users.email AS author, Users.name AS author_name, Users.id AS author_id
           FROM Questions
           JOIN Users ON Questions.user_id = Users.id
           WHERE Questions.id = ?''', (question_id,)).fetchone()
    
    if not question:
        conn.close()
        flash('Question not found.', 'error')
        return redirect(url_for('feed'))
    
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        if content:
            conn.execute(
                '''INSERT INTO Answers (question_id, content, user_id)
                   VALUES (?, ?, ?)''',
                (question_id, content, session['user_id']))
            conn.commit()
            
            # Create notification for question author
            if question['user_id'] != session['user_id']:
                conn.execute(
                    '''INSERT INTO Notifications (user_id, message, link)
                       VALUES (?, ?, ?)''',
                    (question['user_id'],
                     f"{session['name']} answered your question",
                     url_for('question_detail', question_id=question_id)))
                conn.commit()
            
            flash('Answer posted successfully!', 'success')
    
    # Get all answers with author info
    answers = conn.execute(
        '''SELECT Answers.*, Users.email AS author, Users.name AS author_name, Users.id AS author_id
           FROM Answers
           JOIN Users ON Answers.user_id = Users.id
           WHERE Answers.question_id = ?
           ORDER BY Answers.is_accepted DESC, Answers.created_at ASC''',
        (question_id,)).fetchall()
    
    # Convert SQLite Row objects to dictionaries for easier manipulation
    answers_list = []
    for answer in answers:
        answer_dict = dict(answer)
        answers_list.append(answer_dict)
    
    # Get star information for each answer if user is logged in
    if 'user_id' in session and answers_list:
        # Get user's starred answers
        answer_ids = [a['id'] for a in answers_list]
        user_stars = conn.execute(
            'SELECT item_id FROM Stars WHERE user_id = ? AND item_type = ? AND item_id IN ({})'.format(
                ','.join(['?'] * len(answer_ids))
            ),
            [session['user_id'], 'answer'] + answer_ids
        ).fetchall()
        user_starred = {s['item_id'] for s in user_stars}
        
        # Get star counts for each answer
        if answer_ids:
            star_counts = conn.execute(
                'SELECT item_id, COUNT(*) as count FROM Stars WHERE item_type = ? AND item_id IN ({}) GROUP BY item_id'.format(
                    ','.join(['?'] * len(answer_ids))
                ),
                ['answer'] + answer_ids
            ).fetchall()
            star_count_map = {s['item_id']: s['count'] for s in star_counts}
        else:
            star_count_map = {}
        
        # Add star info to answers
        for answer in answers_list:
            answer['is_starred'] = answer['id'] in user_starred
            answer['star_count'] = star_count_map.get(answer['id'], 0)
    
    answers = answers_list
    
    conn.close()
    
    return render_template('question_detail.html', question=question, answers=answers)





@app.route('/answer/<int:answer_id>/accept', methods=['POST'])
def accept_answer(answer_id: int):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    conn = get_db_connection()
    
    # Get answer and question
    answer = conn.execute('SELECT * FROM Answers WHERE id = ?', (answer_id,)).fetchone()
    if not answer:
        conn.close()
        return jsonify({'error': 'Answer not found'}), 404
    
    question = conn.execute('SELECT * FROM Questions WHERE id = ?', (answer['question_id'],)).fetchone()
    
    # Only question author can accept answers
    if question['user_id'] != session['user_id']:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Unaccept all other answers for this question
    conn.execute('UPDATE Answers SET is_accepted = 0 WHERE question_id = ?', (answer['question_id'],))
    
    # Toggle acceptance
    new_status = 0 if answer['is_accepted'] else 1
    conn.execute('UPDATE Answers SET is_accepted = ? WHERE id = ?', (new_status, answer_id))
    
    conn.commit()
    conn.close()
    
    flash('Answer accepted!' if new_status else 'Answer unaccepted!', 'success')
    return jsonify({'success': True, 'is_accepted': new_status})


@app.route('/bookmark/<item_type>/<int:item_id>', methods=['POST'])
def toggle_bookmark(item_type: str, item_id: int):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    if item_type not in ['Document', 'Question']:
        return jsonify({'error': 'Invalid type'}), 400
    
    conn = get_db_connection()
    try:
        # Check if the item exists
        if item_type == 'Document':
            item_exists = conn.execute('SELECT 1 FROM Documents WHERE id = ?', (item_id,)).fetchone()
        else:  # Question
            item_exists = conn.execute('SELECT 1 FROM Questions WHERE id = ?', (item_id,)).fetchone()
            
        if not item_exists:
            return jsonify({'error': f'{item_type} not found'}), 404
        
        # Toggle bookmark
        existing = conn.execute(
            'SELECT id FROM Bookmarks WHERE user_id = ? AND item_type = ? AND item_id = ?',
            (session['user_id'], item_type, item_id)
        ).fetchone()
        
        if existing:
            conn.execute('DELETE FROM Bookmarks WHERE id = ?', (existing['id'],))
            bookmarked = False
        else:
            conn.execute(
                'INSERT INTO Bookmarks (user_id, item_type, item_id) VALUES (?, ?, ?)',
                (session['user_id'], item_type, item_id)
            )
            bookmarked = True
        
        conn.commit()
        return jsonify({
            'status': 'success',
            'bookmarked': bookmarked,
            'message': f'Successfully {'added to' if bookmarked else 'removed from'} bookmarks'
        })
        
    except Exception as e:
        conn.rollback()
        app.logger.error(f'Error toggling bookmark: {str(e)}')
        return jsonify({'error': 'An error occurred while updating bookmarks'}), 500
    finally:
        conn.close()


@app.route('/api/star/<string:item_type>/<int:item_id>', methods=['POST'])
def toggle_star(item_type, item_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    if item_type not in ['answer', 'document']:
        return jsonify({'error': 'Invalid item type'}), 400
        
    conn = None
    try:
        conn = get_db_connection()
        user_id = session['user_id']
        
        # Check if the item exists
        if item_type == 'answer':
            item = conn.execute('SELECT id FROM Answers WHERE id = ?', (item_id,)).fetchone()
        else:  # document
            item = conn.execute('SELECT id FROM Documents WHERE id = ?', (item_id,)).fetchone()
                
        if not item:
            if conn:
                conn.close()
            return jsonify({'error': 'Item not found'}), 404
            
        # First, check if the star already exists
        star = conn.execute(
            'SELECT id FROM Stars WHERE user_id = ? AND item_type = ? AND item_id = ?',
            (user_id, item_type, item_id)
        ).fetchone()
            
        if star:
            # Star exists, so we'll remove it
            conn.execute(
                'DELETE FROM Stars WHERE id = ?',
                (star['id'],)
            )
            starred = False
            app.logger.info(f'Star removed: user_id={user_id}, item_type={item_type}, item_id={item_id}')
        else:
            # Star doesn't exist, so we'll add it
            try:
                conn.execute(
                    'INSERT INTO Stars (user_id, item_type, item_id) VALUES (?, ?, ?)',
                    (user_id, item_type, item_id)
                )
                starred = True
                app.logger.info(f'Star added: user_id={user_id}, item_type={item_type}, item_id={item_id}')
            except sqlite3.IntegrityError as e:
                app.logger.error(f'Integrity error when adding star: {str(e)}')
                conn.rollback()
                # If we get here, it means the star exists but our initial check didn't find it
                # This could be due to a race condition, so we'll treat it as a successful toggle
                starred = True
            
        # Get updated star count and check if the current user has starred the item
        star_count = conn.execute(
            'SELECT COUNT(*) as count FROM Stars WHERE item_type = ? AND item_id = ?',
            (item_type, item_id)
        ).fetchone()['count']
            
        # Check if current user has starred the item
        user_has_starred = conn.execute(
            'SELECT 1 FROM Stars WHERE user_id = ? AND item_type = ? AND item_id = ?',
            (user_id, item_type, item_id)
        ).fetchone() is not None
            
        conn.commit()
        return jsonify({
            'status': 'success',
            'starred': user_has_starred,
            'star_count': star_count,
            'message': 'Successfully ' + ('starred' if user_has_starred else 'unstarred') + ' item'
        })
            
    except Exception as e:
        if conn:
            conn.rollback()
        app.logger.error(f'Error toggling star: {str(e)}')
        return jsonify({'error': 'Failed to update star', 'details': str(e)}), 500
    finally:
        if conn:
            conn.close()
        conn.close()


@app.route('/bookmarks')
def bookmarks():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    bookmarks = conn.execute(
        'SELECT * FROM Bookmarks WHERE user_id = ? ORDER BY created_at DESC',
        (session['user_id'],)).fetchall()
    
    items = []
    for bookmark in bookmarks:
        if bookmark['item_type'] == 'Document':
            item = conn.execute(
                '''SELECT Documents.*, Users.name AS author_name, Users.id AS author_id, 'Document' AS type
                   FROM Documents JOIN Users ON Documents.user_id = Users.id
                   WHERE Documents.id = ?''',
                (bookmark['item_id'],)).fetchone()
        else:
            item = conn.execute(
                '''SELECT Questions.*, Users.name AS author_name, Users.id AS author_id, 'Question' AS type,
                          (SELECT COUNT(*) FROM Answers WHERE question_id = Questions.id) AS answer_count
                   FROM Questions JOIN Users ON Questions.user_id = Users.id
                   WHERE Questions.id = ?''',
                (bookmark['item_id'],)).fetchone()
        if item:
            items.append(item)
    
    conn.close()
    
    return render_template('bookmarks.html', items=items)


@app.route('/admin')
def admin():
    if 'user_id' not in session or session.get('role') not in ('Admin', 'Professor'):
        return redirect(url_for('feed'))
    
    conn = get_db_connection()
    
    # Get all documents with author information
    docs = conn.execute('''
        SELECT d.id, d.title, d.description, d.status, d.created_at,
               u.email AS author, u.name AS author_name
        FROM Documents d
        JOIN Users u ON d.user_id = u.id
        ORDER BY d.created_at DESC
    ''').fetchall()
    
    # Get all questions with author information
    questions = conn.execute('''
        SELECT q.id, q.title, q.description, q.created_at,
               u.email AS author, u.name AS author_name
        FROM Questions q
        JOIN Users u ON q.user_id = u.id
        ORDER BY q.created_at DESC
    ''').fetchall()
    
    conn.close()
    
    return render_template('admin.html', docs=docs, questions=questions)


@app.route('/verify/<int:doc_id>')
def verify(doc_id: int):
    if 'user_id' not in session or session.get('role') not in ('Admin', 'Professor'):
        return redirect(url_for('feed'))
    
    conn = get_db_connection()
    conn.execute('UPDATE Documents SET status = ? WHERE id = ?', ('Verified', doc_id))
    conn.commit()
    conn.close()
    flash('Document verified successfully!', 'success')
    return redirect(url_for('admin'))


@app.route('/unverify/<int:doc_id>')
def unverify(doc_id: int):
    if 'user_id' not in session or session.get('role') not in ('Admin', 'Professor'):
        return redirect(url_for('feed'))
    
    conn = get_db_connection()
    conn.execute('UPDATE Documents SET status = ? WHERE id = ?', ('Unverified', doc_id))
    conn.commit()
    conn.close()
    flash('Document marked as unverified.', 'warning')
    return redirect(url_for('admin'))


@app.route('/admin/delete_document/<int:doc_id>', methods=['POST'])
def delete_document(doc_id: int):
    if 'user_id' not in session or session.get('role') != 'Admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        conn = get_db_connection()
        
        # First get the file path to delete the actual file
        doc = conn.execute('SELECT file_path FROM Documents WHERE id = ?', (doc_id,)).fetchone()
        if not doc:
            return jsonify({'success': False, 'error': 'Document not found'}), 404
            
        # Delete the document from database
        conn.execute('DELETE FROM Documents WHERE id = ?', (doc_id,))
        conn.commit()
        conn.close()
        
        # Delete the actual file if it exists
        if doc['file_path']:
            try:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(doc['file_path']))
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                app.logger.error(f'Error deleting file {file_path}: {str(e)}')
        
        flash('Document deleted successfully!', 'success')
        return jsonify({'success': True})
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        app.logger.error(f'Error deleting document: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/delete_question/<int:question_id>', methods=['POST'])
def delete_question(question_id: int):
    if 'user_id' not in session or session.get('role') != 'Admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        conn = get_db_connection()
        
        # First check if the question exists
        question = conn.execute('SELECT id, file_path FROM Questions WHERE id = ?', (question_id,)).fetchone()
        if not question:
            return jsonify({'success': False, 'error': 'Question not found'}), 404
            
        # Delete associated answers first (due to foreign key constraint)
        conn.execute('DELETE FROM Answers WHERE question_id = ?', (question_id,))
        
        # Delete the question
        conn.execute('DELETE FROM Questions WHERE id = ?', (question_id,))
        conn.commit()
        conn.close()
        
        # Delete the associated file if it exists
        if question['file_path']:
            try:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(question['file_path']))
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                app.logger.error(f'Error deleting question file {file_path}: {str(e)}')
        
        flash('Question and its answers deleted successfully!', 'success')
        return jsonify({'success': True})
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        app.logger.error(f'Error deleting question: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/uploads/<path:filename>')
def uploaded_file(filename: str):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/chat')
def chat():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('chat.html')

@app.route('/api/chat', methods=['POST'])
def chat_api():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    user_input = data.get('message', '').strip()
    
    if not user_input:
        return jsonify({'error': 'Message is required'}), 400
    
    try:
        response = get_chat_response(user_input)
        return jsonify({'response': response})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/document/edit/<int:doc_id>', methods=['GET', 'POST'])
def edit_document(doc_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get the document
    cursor.execute('''
        SELECT * FROM Documents 
        WHERE id = ? AND user_id = ?
    ''', (doc_id, session['user_id']))
    document = cursor.fetchone()
    
    if not document:
        conn.close()
        abort(404, "Document not found or you don't have permission to edit it")
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        
        # Handle file upload if a new file is provided
        uploaded_file = request.files.get('file')
        file_path = document['file_path']
        
        if uploaded_file and uploaded_file.filename:
            # Delete old file if it exists
            old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], document['file_path'])
            if os.path.exists(old_file_path):
                os.remove(old_file_path)
            
            # Save new file
            filename = secure_filename(uploaded_file.filename)
            timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            filename = f"{timestamp}_{filename}"
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            uploaded_file.save(save_path)
            file_path = filename
        
        # Update document in database
        cursor.execute('''
            UPDATE Documents 
            SET title = ?, description = ?, file_path = ?, status = 'Pending'
            WHERE id = ? AND user_id = ?
        ''', (title, description, file_path, doc_id, session['user_id']))
        
        conn.commit()
        conn.close()
        
        flash('Document updated successfully! It will be reviewed again by moderators.', 'success')
        return redirect(url_for('profile', user_id=session['user_id']))
    
    # Convert row to dict for easier template access
    document_dict = dict(document)
    conn.close()
    
    return render_template('edit_document.html', document=document_dict)


@app.route('/document/preview/<int:doc_id>')
def document_preview(doc_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get document details
    cursor.execute('''
        SELECT d.*, u.name as author_name, u.avatar_url 
        FROM Documents d 
        JOIN Users u ON d.user_id = u.id 
        WHERE d.id = ?
    ''', (doc_id,))
    
    document = cursor.fetchone()
    if not document:
        return jsonify({'error': 'Document not found'}), 404
    
    # Check if file exists
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], document['file_path'])
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    # Get file extension and type
    file_extension = os.path.splitext(file_path)[1].lower()
    file_type = 'other'
    
    if file_extension in ['.pdf']:
        file_type = 'pdf'
    elif file_extension in ['.jpg', '.jpeg', '.png', '.gif']:
        file_type = 'image'
    elif file_extension in ['.doc', '.docx']:
        file_type = 'document'
    elif file_extension in ['.xls', '.xlsx']:
        file_type = 'spreadsheet'
    elif file_extension in ['.html', '.htm']:
        file_type = 'html'
        # Read the HTML content
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
    
    response_data = {
        'id': document['id'],
        'title': document['title'],
        'description': document['description'],
        'file_path': document['file_path'],
        'file_type': file_type,
        'author': document['author_name'],
        'author_avatar': document['avatar_url'],
        'created_at': document['created_at'],
        'status': document['status']
    }
    
    # Include HTML content in response if it's an HTML file
    if file_type == 'html' and 'html_content' in locals():
        response_data['html_content'] = html_content
    
    return jsonify(response_data)

@app.route('/document/html/<path:filename>')
def serve_html(filename):
    """Serve HTML files with proper content type"""
    # Only allow serving files from the uploads directory
    uploads_dir = os.path.join(app.root_path, 'uploads')
    file_path = os.path.join(uploads_dir, filename)
    
    # Security check to prevent directory traversal
    if not os.path.abspath(file_path).startswith(os.path.abspath(uploads_dir)):
        abort(403, 'Access denied')
    
    if not os.path.exists(file_path):
        abort(404, 'File not found')
    
    return send_from_directory(uploads_dir, filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 9000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_ENV') == 'development')