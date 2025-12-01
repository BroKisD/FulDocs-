import os
import sqlite3
from datetime import datetime, timedelta

# Get the absolute path to the database file
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')

def get_db_connection():
    """Create and return a database connection."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def get_database_context():
    """Fetch relevant context from the application's database."""
    context = []
    try:
        conn = get_db_connection()
        
        # Get recent documents (last 30 days)
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        # Get recent documents
        documents = conn.execute(
            'SELECT title, description, file_path FROM Documents '
            'WHERE status = ? AND created_at >= ?',
            ('Verified', thirty_days_ago)
        ).fetchall()
        
        # Get recent questions and answers
        questions = conn.execute(
            'SELECT q.title, q.description, a.content as answer_content, a.is_accepted, u.name as answer_author '
            'FROM Questions q '
            'LEFT JOIN Answers a ON q.id = a.question_id '
            'LEFT JOIN Users u ON a.user_id = u.id '
            'WHERE q.created_at >= ?',
            (thirty_days_ago,)
        ).fetchall()
        
        # Format documents context
        if documents:
            context.append("\n=== AVAILABLE DOCUMENTS ===")
            for doc in documents:
                context.append(
                    f"Document: {doc['title']}\n"
                    f"Description: {doc['description']}\n"
                    f"File: {doc['file_path']}"
                )
        
        # Format Q&A context
        if questions:
            context.append("\n=== RECENT Q&A ===")
            for q in questions:
                answer_info = f"Answered by: {q['answer_author']}" if q['answer_content'] else "No answers yet"
                context.append(
                    f"\nQ: {q['title']}\n"
                    f"Details: {q['description']}\n"
                    f"A: {q['answer_content'] or 'No answer yet'}\n"
                    f"{answer_info}"
                )
        
        return "\n".join(context) if context else "No recent documents or questions found in the database."
        
    except Exception as e:
        print(f"Error in get_database_context: {str(e)}")
        return "Error: Could not fetch data from the database."
    finally:
        conn.close()
