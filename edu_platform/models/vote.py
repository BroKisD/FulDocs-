from datetime import datetime
from extensions import db

class Vote(db.Model):
    __tablename__ = 'votes'
    
    id = db.Column(db.Integer, primary_key=True)
    vote_type = db.Column(db.String(10), nullable=False)  # 'up' or 'down'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    answer_id = db.Column(db.Integer, db.ForeignKey('answers.id'), nullable=False)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'answer_id', name='_user_answer_uc'),
    )
    
    def __init__(self, user_id, answer_id, vote_type):
        self.user_id = user_id
        self.answer_id = answer_id
        self.vote_type = vote_type
    
    def __repr__(self):
        return f'<Vote {self.vote_type} by User {self.user_id} on Answer {self.answer_id}>'
