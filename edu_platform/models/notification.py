from datetime import datetime
from extensions import db

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(500), nullable=False)
    link = db.Column(db.String(200))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    def __init__(self, user_id, message, link=None):
        self.user_id = user_id
        self.message = message
        self.link = link
    
    def mark_as_read(self):
        self.is_read = True
        db.session.commit()
    
    def to_dict(self):
        return {
            'id': self.id,
            'message': self.message,
            'link': self.link,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat(),
            'time_ago': self.get_time_ago()
        }
    
    def get_time_ago(self):
        ""
        Returns a string representing how long ago the notification was created
        (e.g., "2 minutes ago", "1 hour ago", "3 days ago")
        """
        from datetime import datetime
        now = datetime.utcnow()
        diff = now - self.created_at
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds >= 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        else:
            minutes = diff.seconds // 60
            if minutes == 0:
                return "just now"
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    
    def __repr__(self):
        return f'<Notification {self.id} for User {self.user_id}>'
