import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory, abort, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import Document, db, Notification
from datetime import datetime

# Import the allowed_file function from the main app
from app import allowed_file

documents_bp = Blueprint('documents', __name__)

@documents_bp.route('/')
@login_required
def list_documents():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Get filter parameters
    status = request.args.get('status', 'all')
    search = request.args.get('search', '').strip()
    
    # Base query
    query = Document.query
    
    # Apply filters
    if status != 'all':
        query = query.filter(Document.status == status)
    
    if search:
        query = query.filter(
            (Document.title.ilike(f'%{search}%')) |
            (Document.description.ilike(f'%{search}%')) |
            (Document.tags.ilike(f'%{search}%'))
        )
    
    # If not admin, only show user's documents or approved documents
    if not current_user.is_admin():
        query = query.filter(
            (Document.user_id == current_user.id) | 
            (Document.status == 'approved')
        )
    
    # Order and paginate
    documents = query.order_by(Document.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('documents/list.html',
                         documents=documents,
                         status=status,
                         search=search)

@documents_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        # Get form data
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        tags = request.form.get('tags', '').strip()
        
        # Validate input
        if not title:
            flash('Title is required', 'error')
            return render_template('documents/upload.html',
                                title=title,
                                description=description,
                                tags=tags)
        
        # Handle file upload
        file = request.files.get('file')
        file_path = None
        
        if file and file.filename:
            if not allowed_file(file.filename):
                flash('Invalid file type. Allowed types are: pdf, doc, docx, txt', 'error')
                return render_template('documents/upload.html',
                                    title=title,
                                    description=description,
                                    tags=tags)
            
            # Save file
            filename = secure_filename(file.filename)
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            
            # Ensure unique filename
            counter = 1
            while os.path.exists(file_path):
                name, ext = os.path.splitext(filename)
                filename = f"{name}_{counter}{ext}"
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                counter += 1
            
            file.save(file_path)
            file_path = filename  # Store relative path
        
        # Create document
        document = Document(
            title=title,
            description=description,
            tags=tags,
            user_id=current_user.id,
            file_path=file_path,
            status='pending' if not current_user.is_admin() else 'approved'
        )
        
        db.session.add(document)
        
        # Notify admin if needed
        if not current_user.is_admin():
            admin = User.query.filter_by(role='admin').first()
            if admin:
                notification = Notification(
                    user_id=admin.id,
                    message=f"New document '{title}' uploaded for review",
                    link=url_for('documents.review', document_id=document.id)
                )
                db.session.add(notification)
        
        db.session.commit()
        
        flash('Document uploaded successfully!', 'success')
        return redirect(url_for('documents.view', document_id=document.id))
    
    return render_template('documents/upload.html')

@documents_bp.route('/<int:document_id>')
@login_required
def view(document_id):
    document = Document.query.get_or_404(document_id)
    
    # Check if user has permission to view
    if document.status != 'approved' and document.user_id != current_user.id and not current_user.is_admin():
        abort(403)
    
    # Increment view count
    document.views += 1
    db.session.commit()
    
    # Check if document is bookmarked by current user
    is_bookmarked = False
    if current_user.is_authenticated:
        is_bookmarked = Bookmark.query.filter_by(
            user_id=current_user.id,
            item_type='document',
            item_id=document.id
        ).first() is not None
    
    return render_template('documents/view.html',
                         document=document,
                         is_bookmarked=is_bookmarked)

@documents_bp.route('/<int:document_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(document_id):
    document = Document.query.get_or_404(document_id)
    
    # Check if user has permission to edit
    if document.user_id != current_user.id and not current_user.is_admin():
        abort(403)
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        tags = request.form.get('tags', '').strip()
        
        # Validate input
        if not title:
            flash('Title is required', 'error')
            return render_template('documents/edit.html', document=document)
        
        # Handle file upload if a new file is provided
        file = request.files.get('file')
        if file and file.filename:
            if not allowed_file(file.filename):
                flash('Invalid file type. Allowed types are: pdf, doc, docx, txt', 'error')
                return render_template('documents/edit.html', document=document)
            
            # Delete old file if it exists
            if document.file_path:
                try:
                    os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], document.file_path))
                except OSError:
                    pass
            
            # Save new file
            filename = secure_filename(file.filename)
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            
            # Ensure unique filename
            counter = 1
            while os.path.exists(file_path):
                name, ext = os.path.splitext(filename)
                filename = f"{name}_{counter}{ext}"
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                counter += 1
            
            file.save(file_path)
            document.file_path = filename
        
        # Update document
        document.title = title
        document.description = description
        document.tags = tags
        document.updated_at = datetime.utcnow()
        
        # If admin is editing, they can change status
        if current_user.is_admin() and 'status' in request.form:
            document.status = request.form['status']
        
        db.session.commit()
        
        flash('Document updated successfully!', 'success')
        return redirect(url_for('documents.view', document_id=document.id))
    
    return render_template('documents/edit.html', document=document)

@documents_bp.route('/<int:document_id>/delete', methods=['POST'])
@login_required
def delete(document_id):
    document = Document.query.get_or_404(document_id)
    
    # Check if user has permission to delete
    if document.user_id != current_user.id and not current_user.is_admin():
        abort(403)
    
    # Delete file if it exists
    if document.file_path:
        try:
            os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], document.file_path))
        except OSError:
            pass
    
    # Delete document
    db.session.delete(document)
    db.session.commit()
    
    flash('Document deleted successfully!', 'success')
    return redirect(url_for('documents.list_documents'))

@documents_bp.route('/<int:document_id>/download')
@login_required
def download(document_id):
    document = Document.query.get_or_404(document_id)
    
    # Check if user has permission to download
    if document.status != 'approved' and document.user_id != current_user.id and not current_user.is_admin():
        abort(403)
    
    if not document.file_path:
        flash('No file available for download', 'error')
        return redirect(url_for('documents.view', document_id=document.id))
    
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], document.file_path)
    if not os.path.exists(file_path):
        flash('File not found', 'error')
        return redirect(url_for('documents.view', document_id=document.id))
    
    # Increment download count (if you have that field)
    if hasattr(document, 'downloads'):
        document.downloads += 1
        db.session.commit()
    
    return send_from_directory(
        current_app.config['UPLOAD_FOLDER'],
        document.file_path,
        as_attachment=True,
        download_name=document.title + os.path.splitext(document.file_path)[1]
    )

@documents_bp.route('/<int:document_id>/review', methods=['GET', 'POST'])
@login_required
def review(document_id):
    # Only admins can review documents
    if not current_user.is_admin():
        abort(403)
    
    document = Document.query.get_or_404(document_id)
    
    if request.method == 'POST':
        action = request.form.get('action')
        feedback = request.form.get('feedback', '').strip()
        
        if action == 'approve':
            document.status = 'approved'
            document.verified_by = current_user.id
            document.verified_at = datetime.utcnow()
            
            # Notify the uploader
            notification = Notification(
                user_id=document.user_id,
                message=f"Your document '{document.title}' has been approved!",
                link=url_for('documents.view', document_id=document.id)
            )
            db.session.add(notification)
            
            flash('Document approved successfully!', 'success')
        
        elif action == 'reject':
            document.status = 'rejected'
            
            # Notify the uploader with feedback
            notification = Notification(
                user_id=document.user_id,
                message=f"Your document '{document.title}' was rejected. {feedback}",
                link=url_for('documents.edit', document_id=document.id)
            )
            db.session.add(notification)
            
            flash('Document rejected successfully!', 'success')
        
        db.session.commit()
        return redirect(url_for('documents.review_queue'))
    
    return render_template('documents/review.html', document=document)

@documents_bp.route('/review-queue')
@login_required
def review_queue():
    # Only admins can access the review queue
    if not current_user.is_admin():
        abort(403)
    
    # Get pending documents
    pending_documents = Document.query\
        .filter_by(status='pending')\
        .order_by(Document.created_at.asc())\
        .all()
    
    return render_template('documents/review_queue.html', documents=pending_documents)
