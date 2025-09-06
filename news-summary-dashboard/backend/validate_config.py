#!/usr/bin/env python3
"""
Configuration validation script for Hugging Face Spaces deployment
"""

import os
import sys
from app.config import current_config

def validate_config():
    """Validate all required configuration variables"""
    required_vars = [
        'SUPABASE_URL',
        'SUPABASE_SERVICE_KEY', 
        'REDIS_HOST_NEWS',
        'REDIS_PORT_NEWS',
        'REDIS_PASSWORD_NEWS',
        'REDIS_HOST_STOCK',
        'REDIS_PORT_STOCK', 
        'REDIS_PASSWORD_STOCK',
        'DB_USER',
        'DB_PASSWORD',
        'DB_HOST',
        'DB_PORT',
        'DB_NAME'
    ]
    
    missing_vars = []
    
    for var in required_vars:
        value = getattr(current_config, var, None)
        if not value:
            missing_vars.append(var)
            
    if missing_vars:
        print(f"Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        return False
    
    print("All required environment variables are set")
    
    # Test Redis connections
    try:
        import redis
        
        # Test news Redis
        news_redis = redis.Redis(
            host=current_config.REDIS_HOST_NEWS,
            port=int(current_config.REDIS_PORT_NEWS),
            password=current_config.REDIS_PASSWORD_NEWS,
            decode_responses=True
        )
        news_redis.ping()
        print("News Redis connection successful")
        
        # Test stock Redis  
        stock_redis = redis.Redis(
            host=current_config.REDIS_HOST_STOCK,
            port=int(current_config.REDIS_PORT_STOCK),
            password=current_config.REDIS_PASSWORD_STOCK,
            decode_responses=True
        )
        stock_redis.ping()
        print("Stock Redis connection successful")
        
    except Exception as e:
        print(f"Redis connection failed: {e}")
        return False
    
    # Test Supabase connection
    try:
        from supabase import create_client
        supabase = create_client(current_config.SUPABASE_URL, current_config.SUPABASE_SERVICE_KEY)
        # Simple query to test connection
        result = supabase.table('bookmarks').select('id').limit(1).execute()
        print("Supabase connection successful")
    except Exception as e:
        print(f"Supabase connection failed: {e}")
        return False
        
    print("🎉 All configurations validated successfully!")
    return True

if __name__ == '__main__':
    if not validate_config():
        sys.exit(1)
