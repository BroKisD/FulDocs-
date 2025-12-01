import google.generativeai as genai
import os
from datetime import datetime
from document_processor import get_document_context
from db_utils import get_database_context  # Import from our new db_utils module

# Initialize the Gemini model
GEMINI_API_KEY = "AIzaSyDqvFjOFoaNV0vut2lILZD7H35nB95K1IU"
genai.configure(api_key=GEMINI_API_KEY)

# Initialize the model
model = genai.GenerativeModel('gemini-2.0-flash')

def get_chat_response(user_input):
    """Get a response from Gemini based on user input, document context, and database content."""
    try:
        # Get context from multiple sources
        try:
            document_context = get_document_context()
            database_context = get_database_context()
            
            # Create a prompt that includes all contexts
            prompt = f"""You are an AI assistant for an educational platform. 
            Use the following information to answer questions. The information comes from:
            1. Uploaded documents (if any)
            2. Database content (recent documents, questions, and answers)
            3. Your general knowledge (only if needed)

            Current date: {datetime.now().strftime('%Y-%m-%d')}
            
            === UPLOADED DOCUMENTS ===
            {document_context}
            
            === DATABASE CONTENT ===
            {database_context}
            
            === USER QUESTION ===
            {user_input}
            
            Please provide a helpful and accurate response. If the information isn't available in the provided resources, 
            you can use your general knowledge but mention that the information is not from the platform's database.
            """
        except Exception as e:
            print(f"Error preparing context: {str(e)}")
            # Fallback to a simpler prompt if there's an error
            prompt = f"""You are an AI assistant for an educational platform. 
            Please answer the following question based on your knowledge:
            
            {user_input}
            
            Note: Could not access platform resources. Answering from general knowledge only.
            """
        
        # Generate response
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        return f"Error generating response: {str(e)}"
