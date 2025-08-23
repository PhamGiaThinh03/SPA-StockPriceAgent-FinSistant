import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration class"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Environment
    ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development')
    
    # Database
    DB_USER = os.environ.get('user')
    DB_PASSWORD = os.environ.get('password') 
    DB_HOST = os.environ.get('host')
    DB_PORT = os.environ.get('db_port')
    DB_NAME = os.environ.get('dbname')
    
    # Redis News
    REDIS_HOST_NEWS = os.environ.get('REDIS_HOST_NEW')
    REDIS_PORT_NEWS = os.environ.get('REDIS_PORT_NEW')
    REDIS_PASSWORD_NEWS = os.environ.get('REDIS_PASSWORD_NEW')
    
    # Redis Stock
    REDIS_HOST_STOCK = os.environ.get('REDIS_HOST_STOCK')
    REDIS_PORT_STOCK = os.environ.get('REDIS_PORT_STOCK')
    REDIS_PASSWORD_STOCK = os.environ.get('REDIS_PASSWORD_STOCK')
    
    # Supabase
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')
    
    # Gemini API
    GEMINI_API_URL = os.environ.get('gemini_api_url')
    GEMINI_API_KEY = os.environ.get('gemini_api_key')
    
    # CORS Origins for production
    ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', '').split(',') if os.environ.get('ALLOWED_ORIGINS') else [
        "https://*.vercel.app",
        "https://localhost:3000",
        "http://localhost:3000"
    ]


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    ENVIRONMENT = 'development'
    

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    ENVIRONMENT = 'production'


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    ENVIRONMENT = 'testing'


# Config dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

# Get current config
current_config = config.get(os.environ.get('FLASK_ENV', 'default'), DevelopmentConfig)
