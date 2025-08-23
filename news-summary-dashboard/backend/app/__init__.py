# backend/app/__init__.py
from flask import Flask
from flask_cors import CORS
from .config import config
import os

def create_app(config_name=None):
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    config_name = config_name or os.environ.get('FLASK_ENV', 'default')
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    CORS(app)
    
    # Register blueprints
    from .routes import app as routes_app
    # Note: routes.py uses app directly, so we need to adapt this
    
    return app
