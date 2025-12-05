import google.generativeai as genai
import os
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
from document_processor import get_document_context, get_documents_metadata
from db_utils import get_db_connection, get_database_context
from typing import Dict, Any, List, Optional

# Load environment variables from .env file
load_dotenv()

# Initialize the Gemini model with optimized settings for Gemini 2.0 Flash
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel(
    'gemini-2.0-flash',
    generation_config={
        'temperature': 0.2,  # Lower temperature for more focused responses
        'top_p': 0.95,
        'top_k': 40,
        'max_output_tokens': 2048,
    },
    safety_settings=[
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
)

# In-memory cache for conversation history (in production, use Redis or similar)
conversation_cache: Dict[str, Dict[str, Any]] = {}
CACHE_EXPIRY = 900  # 15 minutes in seconds

def get_document_links() -> str:
    """Generate clickable links for all uploaded documents."""
    docs = get_documents_metadata()
    if not docs:
        return "No documents available."
    
    links = []
    for doc in docs:
        doc_id = doc.get('id', '')
        title = doc.get('title', 'Untitled')
        links.append(f"[Document: {title}](/documents/{doc_id})")
    
    return "\n".join(links)

def update_conversation_history(session_id: str, role: str, content: str) -> None:
    """Update the conversation history for a session."""
    now = time.time()
    if session_id not in conversation_cache:
        conversation_cache[session_id] = {
            'history': [],
            'last_activity': now
        }
    
    # Clean up old conversations
    expired_sessions = [sid for sid, data in conversation_cache.items() 
                       if now - data['last_activity'] > CACHE_EXPIRY]
    for sid in expired_sessions:
        del conversation_cache[sid]
    
    # Update current session
    conversation_cache[session_id]['history'].append({'role': role, 'content': content})
    conversation_cache[session_id]['last_activity'] = now
    
    # Keep conversation history manageable
    if len(conversation_cache[session_id]['history']) > 20:  # Keep last 20 messages
        conversation_cache[session_id]['history'] = conversation_cache[session_id]['history'][-20:]

def get_chat_response(user_input: str, session_id: str = 'default') -> str:
    """Get a response from Gemini based on user input, document context, and database content.
    
    Args:
        user_input: The user's message
        session_id: Unique identifier for the conversation session
        
    Returns:
        str: The AI's response
    """
    try:
        # Update conversation history with user input
        update_conversation_history(session_id, 'user', user_input)
        
        # Get context from multiple sources
        document_context = get_document_context()
        database_context = get_database_context()
        document_links = get_document_links()
        
        # Get conversation history
        history = conversation_cache.get(session_id, {}).get('history', [])
        history_str = '\n'.join(
            f"{msg['role'].capitalize()}: {msg['content']}" 
            for msg in history[-5:]  # Last 5 messages for context
        )
        
        # Create a prompt that includes all contexts
        prompt = f"""You are an AI assistant for Fulbright University Vietnam educational platform.
You have access to course materials and documents. 

IMPORTANT: Format your response in Markdown. Use **bold** for emphasis, `code` for code, and [links](url) for references.

Available Documents (click to view):
{document_links}

Conversation History:
{history_str}

Document Context:
{document_context}

Database Context:
{database_context}

User: {user_input}

AI (respond in Markdown):"""
        
        # Generate response using the model
        response = model.generate_content(prompt)
        
        if not response.text:
            return "I apologize, but I'm having trouble generating a response. Could you please rephrase your question?"
        
        # Ensure the response is properly formatted
        response_text = response.text or "I apologize, but I'm having trouble generating a response."
        
        # Update conversation history with AI response
        update_conversation_history(session_id, 'assistant', response_text)
        
        return response_text
        
    except Exception as e:
        error_msg = f"I encountered an error: {str(e)}"
        print(f"Error in get_chat_response: {error_msg}")
        return error_msg
