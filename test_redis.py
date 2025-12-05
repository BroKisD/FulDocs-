import os
import redis
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_redis_connection():
    redis_host = os.getenv('REDIS_HOST')
    redis_port = int(os.getenv('REDIS_PORT', 6379))
    redis_user = os.getenv('REDIS_USER', 'default')
    redis_password = os.getenv('REDIS_PASSWORD')

    print(f"Attempting to connect to Redis at {redis_host}:{redis_port}")
    
    # Test with SSL
    try:
        print("\nTrying SSL connection...")
        r = redis.Redis(
            host=redis_host,
            port=redis_port,
            username=redis_user,
            password=redis_password,
            ssl=True,
            ssl_cert_reqs=None,
            socket_timeout=5,
            decode_responses=True
        )
        r.ping()
        print("✅ Successfully connected with SSL")
        return True
    except Exception as e:
        print(f"❌ SSL connection failed: {e}")
    
    # Test without SSL
    try:
        print("\nTrying non-SSL connection...")
        r = redis.Redis(
            host=redis_host,
            port=redis_port,
            username=redis_user,
            password=redis_password,
            ssl=False,
            socket_timeout=5,
            decode_responses=True
        )
        r.ping()
        print("✅ Successfully connected without SSL")
        return True
    except Exception as e:
        print(f"❌ Non-SSL connection failed: {e}")
    
    print("\n❌ All connection attempts failed")
    return False

if __name__ == "__main__":
    test_redis_connection()
