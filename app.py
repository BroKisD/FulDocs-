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
import sqlite3
from datetime import datetime
from flask import (Flask, render_template, request, redirect,
                   url_for, session, send_from_directory, flash, jsonify)
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.secret_key = 'replace_with_a_random_secret_key'

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
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

    # Add new columns to existing Users table
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
            ('professor@university.edu', 'Professor', 'Prof. Smith', 'Computer Science Professor'),
            ('student@university.edu', 'Student', 'Jane Doe', 'Computer Science student'),
        ]
        for email, role, name, bio in users:
            cursor.execute(
                'INSERT INTO Users (email, role, name, bio) VALUES (?, ?, ?, ?)',
                (email, role, name, bio))

    # Seed sample documents
    existing_docs = cursor.execute('SELECT COUNT(*) AS count FROM Documents').fetchone()['count']
    if existing_docs == 0:
        sample_docs = [
            ('Introduction to Flask', 'A comprehensive guide to building web applications with Flask',
             'flask, python, web', 'Flask is a lightweight WSGI web application framework...', 'Verified', 2, None),
            ('Database Design Principles', 'Learn the fundamentals of database design',
             'database, sql, design', 'Database design is crucial for building scalable applications...', 'Verified', 2, None),
            ('My Research Project', 'Final year research on machine learning',
             'ml, research, project', 'This project explores the application of machine learning...', 'Pending', 3, None),
        ]
        for title, description, tags, content, status, user_id, file_path in sample_docs:
            cursor.execute(
                '''INSERT INTO Documents (title, description, tags, content, status, user_id, file_path)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (title, description, tags, content, status, user_id, file_path))

    # Seed sample questions
    existing_questions = cursor.execute('SELECT COUNT(*) AS count FROM Questions').fetchone()['count']
    if existing_questions == 0:
        sample_questions = [
            ('How to integrate Flask with SQLite?',
             'I am trying to integrate Flask with SQLite and need advice on best practices.',
             'flask, database, sqlite', 'Pending', 3, None),
            ('What is the difference between GET and POST?',
             'Could someone explain when to use GET vs POST requests?',
             'http, web, api', 'Pending', 3, None),
        ]
        for title, description, tags, status, user_id, file_path in sample_questions:
            cursor.execute(
                '''INSERT INTO Questions (title, description, tags, status, user_id, file_path)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (title, description, tags, status, user_id, file_path))

    conn.commit()
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
            conn.close()
            if user:
                session['user_id'] = user['id']
                session['role'] = user['role']
                session['email'] = user['email']
                session['name'] = user['name'] or email.split('@')[0]
                flash('Welcome back!', 'success')
                return redirect(url_for('feed'))
            else:
                error = 'No account found for this email.'
    return render_template('login.html', error=error)


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
    
    # Get user's documents
    docs = conn.execute(
        '''SELECT * FROM Documents WHERE user_id = ? ORDER BY created_at DESC LIMIT 10''',
        (user_id,)).fetchall()
    
    # Get user's questions
    questions = conn.execute(
        '''SELECT * FROM Questions WHERE user_id = ? ORDER BY created_at DESC LIMIT 10''',
        (user_id,)).fetchall()
    
    # Get user's answers count
    answers_count = conn.execute(
        'SELECT COUNT(*) as count FROM Answers WHERE user_id = ?',
        (user_id,)).fetchone()['count']
    
    conn.close()
    
    stats = {
        'documents': len(docs),
        'questions': len(questions),
        'answers': answers_count
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
    
    # Fetch verified documents and all questions
    docs = conn.execute(
        '''SELECT Documents.id AS id, Documents.title AS title,
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
                  (SELECT COUNT(*) FROM Answers WHERE question_id = Questions.id) AS answer_count
           FROM Questions
           JOIN Users ON Questions.user_id = Users.id
           ORDER BY Questions.created_at DESC''').fetchall()
    
    conn.close()
    
    # Combine and sort items by creation date, handling None values
    items = list(docs) + list(questions)
    items_sorted = sorted(
        items, 
        key=lambda r: r['created_at'] if r['created_at'] is not None else '', 
        reverse=True
    )
    
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
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        tags = request.form.get('tags', '').strip()
        content = request.form.get('content', '').strip()
        
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
                '''INSERT INTO Documents (title, description, tags, content,
                                          status, user_id, file_path)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (title, description, tags, content, 'Pending',
                 session['user_id'], file_path))
            conn.commit()
            conn.close()
            flash('Document submitted for review!', 'success')
            return redirect(url_for('feed'))
    
    return render_template('post.html')


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
    
    answers = conn.execute(
        '''SELECT Answers.*, Users.email AS author, Users.name AS author_name, Users.id AS author_id
           FROM Answers
           JOIN Users ON Answers.user_id = Users.id
           WHERE Answers.question_id = ?
           ORDER BY Answers.is_accepted DESC, Answers.upvotes - Answers.downvotes DESC, Answers.created_at ASC''',
        (question_id,)).fetchall()
    
    # Get user's votes
    user_votes = {}
    if answers:
        answer_ids = [a['id'] for a in answers]
        votes = conn.execute(
            f'''SELECT answer_id, vote_type FROM Votes 
                WHERE user_id = ? AND answer_id IN ({','.join('?' * len(answer_ids))})''',
            [session['user_id']] + answer_ids).fetchall()
        user_votes = {v['answer_id']: v['vote_type'] for v in votes}
    
    conn.close()
    
    return render_template('question_detail.html', question=question, 
                         answers=answers, user_votes=user_votes)


@app.route('/answer/<int:answer_id>/vote', methods=['POST'])
def vote_answer(answer_id: int):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    vote_type = request.json.get('vote_type')
    if vote_type not in ['up', 'down']:
        return jsonify({'error': 'Invalid vote type'}), 400
    
    conn = get_db_connection()
    
    # Check existing vote
    existing_vote = conn.execute(
        'SELECT * FROM Votes WHERE user_id = ? AND answer_id = ?',
        (session['user_id'], answer_id)).fetchone()
    
    if existing_vote:
        if existing_vote['vote_type'] == vote_type:
            # Remove vote
            conn.execute('DELETE FROM Votes WHERE user_id = ? AND answer_id = ?',
                        (session['user_id'], answer_id))
            if vote_type == 'up':
                conn.execute('UPDATE Answers SET upvotes = upvotes - 1 WHERE id = ?', (answer_id,))
            else:
                conn.execute('UPDATE Answers SET downvotes = downvotes - 1 WHERE id = ?', (answer_id,))
        else:
            # Change vote
            conn.execute('UPDATE Votes SET vote_type = ? WHERE user_id = ? AND answer_id = ?',
                        (vote_type, session['user_id'], answer_id))
            if vote_type == 'up':
                conn.execute('UPDATE Answers SET upvotes = upvotes + 1, downvotes = downvotes - 1 WHERE id = ?',
                           (answer_id,))
            else:
                conn.execute('UPDATE Answers SET downvotes = downvotes + 1, upvotes = upvotes - 1 WHERE id = ?',
                           (answer_id,))
    else:
        # New vote
        conn.execute('INSERT INTO Votes (user_id, answer_id, vote_type) VALUES (?, ?, ?)',
                    (session['user_id'], answer_id, vote_type))
        if vote_type == 'up':
            conn.execute('UPDATE Answers SET upvotes = upvotes + 1 WHERE id = ?', (answer_id,))
        else:
            conn.execute('UPDATE Answers SET downvotes = downvotes + 1 WHERE id = ?', (answer_id,))
    
    conn.commit()
    
    # Get updated counts
    answer = conn.execute('SELECT upvotes, downvotes FROM Answers WHERE id = ?', (answer_id,)).fetchone()
    conn.close()
    
    return jsonify({
        'upvotes': answer['upvotes'],
        'downvotes': answer['downvotes'],
        'score': answer['upvotes'] - answer['downvotes']
    })


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
    
    existing = conn.execute(
        'SELECT * FROM Bookmarks WHERE user_id = ? AND item_type = ? AND item_id = ?',
        (session['user_id'], item_type, item_id)).fetchone()
    
    if existing:
        conn.execute('DELETE FROM Bookmarks WHERE id = ?', (existing['id'],))
        bookmarked = False
    else:
        conn.execute(
            'INSERT INTO Bookmarks (user_id, item_type, item_id) VALUES (?, ?, ?)',
            (session['user_id'], item_type, item_id))
        bookmarked = True
    
    conn.commit()
    conn.close()
    
    return jsonify({'bookmarked': bookmarked})


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
    pending_docs = conn.execute(
        '''SELECT Documents.id, Documents.title, Documents.description,
                  Documents.tags, Documents.status,
                  Users.email AS author, Users.name AS author_name
           FROM Documents
           JOIN Users ON Documents.user_id = Users.id
           WHERE Documents.status = 'Pending' ''').fetchall()
    conn.close()
    return render_template('admin.html', docs=pending_docs)


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


@app.route('/uploads/<path:filename>')
def uploaded_file(filename: str):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    app.run(debug=True)