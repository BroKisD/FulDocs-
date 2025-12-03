from datetime import datetime
from extensions import db

class Question(db.Model):
    __tablename__ = 'questions'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    tags = db.Column(db.String(200))
    status = db.Column(db.String(20), default='open')  # open, closed, answered
    file_path = db.Column(db.String(200))
    views = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationships
    answers = db.relationship('Answer', backref='question', lazy=True, cascade='all, delete-orphan')
    
    def __init__(self, title, user_id, **kwargs):
        self.title = title
        self.user_id = user_id
        
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'tags': self.tags,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'author': self.author.name if self.author else 'Unknown',
            'answer_count': len(self.answers),
            'views': self.views
        }
    
    def has_accepted_answer(self):
        return any(answer.is_accepted for answer in self.answers)
    
    def __repr__(self):
        return f'<Question {self.title}>'
