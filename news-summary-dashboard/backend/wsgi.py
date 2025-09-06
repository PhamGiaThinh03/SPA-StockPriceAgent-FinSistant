#!/usr/bin/env python3
"""
WSGI entry point for Hugging Face Spaces deployment
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Add current directory to Python path to ensure imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    # Import the Flask app from routes
    from app.routes import app
    
    # Create WSGI application
    application = app
    
    print("Successfully loaded Flask app from app.routes")
    
except ImportError as e:
    print(f"Import error: {e}")
    print("Creating fallback Flask app...")
    
    # Fallback: create a simple Flask app if import fails
    from flask import Flask, jsonify
    from flask_cors import CORS
    
    app = Flask(__name__)
    CORS(app, origins=["*"], supports_credentials=True)
    
    @app.route('/', methods=['GET'])
    def root():
        return jsonify({
            "message": "Fallback Flask app is running",
            "status": "error",
            "error": "Main app import failed"
        })
    
    @app.route('/api/health', methods=['GET'])
    def health():
        return jsonify({
            "status": "unhealthy", 
            "message": "Running fallback app due to import error"
        })
    
    application = app

except Exception as e:
    print(f"Unexpected error: {e}")
    # Last resort fallback
    from flask import Flask, jsonify
    app = Flask(__name__)
    
    @app.route('/')
    def emergency():
        return jsonify({"error": str(e), "status": "emergency fallback"})
    
    application = app

if __name__ == '__main__':
    # Force port 7860 for HF Spaces (ignore PORT from .env to avoid DB port conflict)
    port = 7860
    print(f"Starting WSGI app on port {port}")
    application.run(host='0.0.0.0', port=port, debug=False)
