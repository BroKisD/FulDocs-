from datetime import datetime
from extensions import db

class Bookmark(db.Model):
    __tablename__ = 'bookmarks'
    
    id = db.Column(db.Integer, primary_key=True)
    item_type = db.Column(db.String(20), nullable=False)  # 'document' or 'question'
    item_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'item_type', 'item_id', name='_user_item_uc'),
    )
    
    def __init__(self, user_id, item_type, item_id):
        self.user_id = user_id
        self.item_type = item_type
        self.item_id = item_id
    
    def get_item(self):
        """Get the bookmarked item based on item_type and item_id"""
        if self.item_type == 'document':
            from .document import Document
            return Document.query.get(self.item_id)
        elif self.item_type == 'question':
            from .question import Question
            return Question.query.get(self.item_id)
        return None
    
    def to_dict(self):
        item = self.get_item()
        return {
            'id': self.id,
            'item_type': self.item_type,
            'item_id': self.item_id,
            'created_at': self.created_at.isoformat(),
            'item': item.to_dict() if hasattr(item, 'to_dict') else None
        }
    
    def __repr__(self):
        return f'<Bookmark {self.item_type} {self.item_id} by User {self.user_id}>'
