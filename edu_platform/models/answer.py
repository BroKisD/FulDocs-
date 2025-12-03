from datetime import datetime
from extensions import db

class Answer(db.Model):
    __tablename__ = 'answers'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    is_accepted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    
    # Relationships
    votes = db.relationship('Vote', backref='answer', lazy=True, cascade='all, delete-orphan')
    
    def __init__(self, content, user_id, question_id, **kwargs):
        self.content = content
        self.user_id = user_id
        self.question_id = question_id
        
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'is_accepted': self.is_accepted,
            'created_at': self.created_at.isoformat(),
            'author': self.author.name if self.author else 'Unknown',
            'vote_count': self.get_vote_count(),
            'user_vote': None  # Will be set by the view if user is logged in
        }
    
    def get_vote_count(self):
        upvotes = sum(1 for vote in self.votes if vote.vote_type == 'up')
        downvotes = sum(1 for vote in self.votes if vote.vote_type == 'down')
        return upvotes - downvotes
    
    def __repr__(self):
        return f'<Answer {self.id} to Question {self.question_id}>'
