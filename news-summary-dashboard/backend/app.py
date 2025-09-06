import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import app from routes module  
from app.routes import app

# Export app for gunicorn
application = app

# Configuration for Hugging Face Spaces
if __name__ == '__main__':
    # Hugging Face Spaces uses port 7860, do not get from .env to avoid conflict with DB port
    port = 7860
    print(f"Starting News Summary API on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
