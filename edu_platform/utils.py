import os
from werkzeug.utils import secure_filename

def allowed_file(filename, allowed_extensions=None):
    """Check if the file extension is allowed"""
    if allowed_extensions is None:
        allowed_extensions = {'pdf', 'doc', 'docx', 'txt'}
    
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def get_secure_filename(filename):
    """Get a secure filename and ensure it's unique"""
    from datetime import datetime
    from flask import current_app
    
    # Get the base filename and extension
    base, ext = os.path.splitext(secure_filename(filename))
    
    # Add timestamp to make it unique
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    new_filename = f"{base}_{timestamp}{ext}"
    
    # Check if file exists (should be very unlikely with timestamp)
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], new_filename)
    counter = 1
    
    while os.path.exists(file_path):
        new_filename = f"{base}_{timestamp}_{counter}{ext}"
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], new_filename)
        counter += 1
    
    return new_filename

def save_uploaded_file(file, folder=None):
    """Save an uploaded file and return the filename"""
    from flask import current_app
    
    if not file or not file.filename:
        return None
    
    # Get secure filename
    filename = get_secure_filename(file.filename)
    
    # Determine upload folder
    upload_folder = folder or current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_folder, exist_ok=True)
    
    # Save file
    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)
    
    return filename

def delete_file(filename, folder=None):
    """Delete a file from the uploads folder"""
    from flask import current_app
    
    if not filename:
        return False
    
    try:
        upload_folder = folder or current_app.config['UPLOAD_FOLDER']
        file_path = os.path.join(upload_folder, filename)
        
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
    except Exception as e:
        current_app.logger.error(f"Error deleting file {filename}: {str(e)}")
    
    return False

def format_datetime(value, format='medium'):
    """Format a datetime object to a string"""
    if value is None:
        return ''
    
    if format == 'full':
        format = "%A, %B %d, %Y at %I:%M %p"
    elif format == 'medium':
        format = "%b %d, %Y %I:%M %p"
    elif format == 'date':
        format = "%B %d, %Y"
    elif format == 'time':
        format = "%I:%M %p"
    
    return value.strftime(format)

def get_pagination(page, per_page, total, route_name, **kwargs):
    """Generate pagination information for templates"""
    from flask import url_for
    
    pages = {
        'has_prev': page > 1,
        'has_next': page * per_page < total,
        'current_page': page,
        'total_pages': (total + per_page - 1) // per_page,
        'total_items': total,
        'per_page': per_page
    }
    
    # Generate URLs for pagination
    if pages['has_prev']:
        pages['prev_url'] = url_for(route_name, page=page-1, **kwargs)
    else:
        pages['prev_url'] = None
    
    if pages['has_next']:
        pages['next_url'] = url_for(route_name, page=page+1, **kwargs)
    else:
        pages['next_url'] = None
    
    # Generate page numbers to display
    page_numbers = []
    for num in range(max(1, page-2), min(pages['total_pages']+1, page+3)):
        page_numbers.append({
            'number': num,
            'url': url_for(route_name, page=num, **kwargs),
            'is_current': num == page
        })
    
    pages['page_numbers'] = page_numbers
    
    return pages
