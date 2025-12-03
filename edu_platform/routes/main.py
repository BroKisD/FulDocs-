from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from models import Document, Question, Answer, Bookmark, db
from datetime import datetime, timedelta

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.feed'))
    return redirect(url_for('auth.login'))

@main_bp.route('/feed')
@login_required
def feed():
    # Get recent documents
    recent_docs = Document.query.filter_by(status='approved')\
        .order_by(Document.created_at.desc())\
        .limit(5).all()
    
    # Get recent questions
    recent_questions = Question.query\
        .order_by(Question.created_at.desc())\
        .limit(5).all()
    
    # Get trending documents (most viewed in the last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    trending_docs = Document.query\
        .filter(Document.created_at >= week_ago)\
        .order_by(Document.views.desc())\
        .limit(5).all()
    
    # Get unanswered questions
    unanswered_questions = Question.query\
        .filter(~Question.answers.any())\
        .order_by(Question.created_at.desc())\
        .limit(5).all()
    
    return render_template('main/feed.html',
                         recent_docs=recent_docs,
                         recent_questions=recent_questions,
                         trending_docs=trending_docs,
                         unanswered_questions=unanswered_questions)

@main_bp.route('/search')
@login_required
def search():
    query = request.args.get('q', '').strip()
    if not query:
        return redirect(url_for('main.feed'))
    
    # Search in documents
    doc_results = Document.query\
        .filter(
            (Document.title.ilike(f'%{query}%')) |
            (Document.description.ilike(f'%{query}%')) |
            (Document.content.ilike(f'%{query}%')) |
            (Document.tags.ilike(f'%{query}%'))
        )\
        .filter(Document.status == 'approved')\
        .order_by(Document.created_at.desc())\
        .all()
    
    # Search in questions
    question_results = Question.query\
        .filter(
            (Question.title.ilike(f'%{query}%')) |
            (Question.description.ilike(f'%{query}%')) |
            (Question.tags.ilike(f'%{query}%'))
        )\
        .order_by(Question.created_at.desc())\
        .all()
    
    return render_template('main/search_results.html',
                         query=query,
                         doc_results=doc_results,
                         question_results=question_results)

@main_bp.route('/profile/<int:user_id>')
@login_required
def profile(user_id):
    from models import User
    user = User.query.get_or_404(user_id)
    
    # Get user's documents
    docs = Document.query\
        .filter_by(user_id=user_id)\
        .order_by(Document.created_at.desc())\
        .limit(10).all()
    
    # Get user's questions
    questions = Question.query\
        .filter_by(user_id=user_id)\
        .order_by(Question.created_at.desc())\
        .limit(10).all()
    
    # Get user's answers count
    answer_count = Answer.query\
        .filter_by(user_id=user_id)\
        .count()
    
    # Get user's bookmarks
    bookmarks = Bookmark.query\
        .filter_by(user_id=user_id)\
        .order_by(Bookmark.created_at.desc())\
        .limit(10).all()
    
    # Get bookmarked items
    bookmarked_items = []
    for bookmark in bookmarks:
        item = bookmark.get_item()
        if item:
            bookmarked_items.append({
                'type': bookmark.item_type,
                'item': item,
                'bookmarked_at': bookmark.created_at
            })
    
    stats = {
        'documents': len(docs),
        'questions': len(questions),
        'answers': answer_count,
        'bookmarks': len(bookmarks)
    }
    
    return render_template('main/profile.html',
                         user=user,
                         stats=stats,
                         docs=docs,
                         questions=questions,
                         bookmarked_items=bookmarked_items)

@main_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        bio = request.form.get('bio', '').strip()
        
        if not name:
            flash('Name is required', 'error')
        else:
            current_user.name = name
            current_user.bio = bio
            
            # Handle avatar upload
            if 'avatar' in request.files:
                file = request.files['avatar']
                if file.filename:
                    # In a real app, you would save the file and store the path
                    # For now, we'll just store a placeholder
                    current_user.avatar_url = f"https://ui-avatars.com/api/?name={name.replace(' ', '+')}&background=random"
            
            db.session.commit()
            flash('Profile updated successfully', 'success')
            return redirect(url_for('main.profile', user_id=current_user.id))
    
    return render_template('main/edit_profile.html')

@main_bp.route('/notifications')
@login_required
def notifications():
    from models import Notification
    
    # Mark all notifications as read
    Notification.query\
        .filter_by(user_id=current_user.id, is_read=False)\
        .update({Notification.is_read: True})
    db.session.commit()
    
    # Get all notifications
    notifications = Notification.query\
        .filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc())\
        .all()
    
    return render_template('main/notifications.html', notifications=notifications)

@main_bp.route('/notifications/count')
@login_required
def notification_count():
    from models import Notification
    count = Notification.query\
        .filter_by(user_id=current_user.id, is_read=False)\
        .count()
    return jsonify({'count': count})
