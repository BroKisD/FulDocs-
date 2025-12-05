import time
import json
import redis
from datetime import datetime, timedelta
from flask import request, g, current_app, session
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class UserAnalytics:
    _instance = None
    _redis = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(UserAnalytics, cls).__new__(cls)
            cls._instance._initialize_redis()
        return cls._instance
    
    def _initialize_redis(self):
        """Initialize Redis connection for analytics using Redis Cloud configuration."""
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', 6379))
        redis_user = os.getenv('REDIS_USER', 'default')
        redis_password = os.getenv('REDIS_PASSWORD')
        
        if not redis_password:
            print("Warning: REDIS_PASSWORD environment variable is not set. Analytics will not be available.")
            return
        
        try:
            # Connect without SSL
            self.redis = redis.Redis(
                host=redis_host,
                port=redis_port,
                username=redis_user,
                password=redis_password,
                decode_responses=True,
                ssl=False,  # SSL disabled as per test results
                socket_timeout=5,
                socket_connect_timeout=5
            )
            # Test the connection
            self.redis.ping()
            print("Successfully connected to Redis")
        except Exception as e:
            print(f"Warning: Failed to connect to Redis: {e}")
            print("Analytics will not be available.")
            self.redis = None
    
    def track_login(self, user_id):
        """Track when a user logs in"""
        if not self.redis:
            return
            
        try:
            login_time = datetime.utcnow().isoformat()
            self.redis.hset(f'user:{user_id}:sessions', login_time, '')
            self.redis.hset(f'user:{user_id}:current_session', 'login_time', login_time)
            self.redis.incr(f'user:{user_id}:login_count')
            self.redis.hset(f'user:{user_id}:last_login', 'timestamp', login_time)
        except Exception as e:
            print(f"Error in track_login: {e}")
    
    def track_logout(self, user_id):
        """Track when a user logs out and update session duration"""
        if not self.redis:
            return
            
        try:
            current_session = self.redis.hgetall(f'user:{user_id}:current_session')
            if current_session and 'login_time' in current_session:
                login_time = datetime.fromisoformat(current_session['login_time'])
                session_duration = (datetime.utcnow() - login_time).total_seconds()
                
                # Store session duration
                self.redis.hset(f'user:{user_id}:sessions', current_session['login_time'], session_duration)
                
                # Update total session time
                self.redis.hincrbyfloat(f'user:{user_id}:stats', 'total_session_time', session_duration)
                
                # Clear current session
                self.redis.delete(f'user:{user_id}:current_session')
        except Exception as e:
            print(f"Error in track_logout: {e}")
    
    def track_page_view(self, user_id, path):
        """Track a page view for a user"""
        if not user_id or not path:
            return
            
        timestamp = datetime.utcnow().isoformat()
        page_key = f'user:{user_id}:page_views'
        
        # Store the page view with timestamp
        self.redis.zadd(page_key, {f'{timestamp}:{path}': time.time()})
        
        # Increment page view count
        self.redis.hincrby(f'user:{user_id}:page_stats', path, 1)
        
        # Update last active time
        self.redis.hset(f'user:{user_id}:activity', 'last_active', timestamp)
    
    def track_action(self, user_id, action_type, metadata=None):
        """Track a user action (e.g., 'document_upload', 'question_posted')"""
        if not user_id or not action_type:
            return
            
        action_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'action': action_type,
            'metadata': metadata or {}
        }
        
        # Store the action
        self.redis.rpush(f'user:{user_id}:actions', json.dumps(action_data))
        
        # Increment action counter
        self.redis.hincrby(f'user:{user_id}:action_counts', action_type, 1)
    
    def get_user_stats(self, user_id):
        """Get analytics for a specific user"""
        if not user_id:
            return None
            
        # Get all sessions
        sessions = self.redis.hgetall(f'user:{user_id}:sessions')
        session_times = [float(duration) for duration in sessions.values() if duration]
        
        # Get page stats
        page_stats = self.redis.hgetall(f'user:{user_id}:page_stats')
        
        # Get action counts
        action_counts = self.redis.hgetall(f'user:{user_id}:action_counts')
        
        # Get total login count
        login_count = int(self.redis.get(f'user:{user_id}:login_count') or 0)
        
        # Get page times
        page_times = self.redis.hgetall(f'user:{user_id}:page_times')
        # Convert string values to float
        page_times = {k: float(v) for k, v in page_times.items()}
        
        # Calculate average session time
        avg_session = sum(session_times) / len(session_times) if session_times else 0
        
        return {
            'user_id': user_id,
            'total_logins': login_count,
            'total_sessions': len(sessions),
            'avg_session_seconds': avg_session,
            'total_session_seconds': sum(session_times),
            'page_views': page_stats,
            'page_times': page_times,  # Add page times to the response
            'action_counts': action_counts,
            'last_active': self.redis.hget(f'user:{user_id}:activity', 'last_active')
        }

# Create a global instance of the analytics tracker
# This will be initialized when the module is imported
try:
    analytics = UserAnalytics()
except Exception as e:
    print(f"Warning: Could not initialize analytics: {e}")
    analytics = None

def init_analytics(app):
    """Initialize analytics with app context"""
    @app.before_request
    def before_request():
        if not hasattr(g, 'analytics'):
            g.analytics = analytics
            
        if 'user_id' in session and analytics and hasattr(analytics, 'redis') and analytics.redis:
            g.request_start_time = time.time()
            try:
                # Track the page view
                analytics.track_page_view(session['user_id'], request.path)
            except Exception as e:
                current_app.logger.error(f"Error tracking page view: {e}")
    
    @app.after_request
    def after_request(response):
        if (hasattr(g, 'request_start_time') and 
            'user_id' in session and 
            analytics and 
            hasattr(analytics, 'redis') and 
            analytics.redis):
            
            try:
                # Calculate time spent on the page
                time_spent = time.time() - g.request_start_time
                
                # Store time spent on the page (minimum 0.1 seconds to avoid tracking accidental clicks)
                if time_spent > 0.1:
                    analytics.redis.hincrbyfloat(
                        f'user:{session["user_id"]}:page_times', 
                        request.path, 
                        time_spent
                    )
            except Exception as e:
                current_app.logger.error(f"Error tracking page time: {e}")
                
        return response
