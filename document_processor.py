import os
from PyPDF2 import PdfReader
from docx import Document
from db_utils import get_db_connection

def extract_text_from_file(file_path):
    """Extract text from various document formats."""
    _, ext = os.path.splitext(file_path.lower())
    
    try:
        if ext == '.pdf':
            with open(file_path, 'rb') as f:
                reader = PdfReader(f)
                text = '\n'.join(page.extract_text() for page in reader.pages)
                return text
                
        elif ext in ['.docx', '.doc']:
            doc = Document(file_path)
            return '\n'.join(paragraph.text for paragraph in doc.paragraphs)
            
        elif ext == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
                
    except Exception as e:
        print(f"Error extracting text from {file_path}: {str(e)}")
        return ""

def get_document_context():
    """Get context from all documents in the uploads directory."""
    uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    context = []
    
    if not os.path.exists(uploads_dir):
        return ""
        
    for filename in os.listdir(uploads_dir):
        file_path = os.path.join(uploads_dir, filename)
        if os.path.isfile(file_path):
            text = extract_text_from_file(file_path)
            if text:
                context.append(f"Document: {filename}\n{text}")
    
    return "\n\n".join(context)

def get_documents_metadata() -> list[dict]:
    """Retrieve metadata for all documents from the database."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, file_path, created_at, user_id
            FROM documents 
            ORDER BY created_at DESC
        """)
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error fetching document metadata: {str(e)}")
        return []
    finally:
        conn.close()
