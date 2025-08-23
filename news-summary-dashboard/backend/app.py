import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import app from routes module  
from app.routes import app

# Export app cho gunicorn
application = app

# Cấu hình cho Hugging Face Spaces
if __name__ == '__main__':
    # Hugging Face Spaces sử dụng port 7860, không lấy từ .env để tránh conflict với DB port
    port = 7860
    print(f"Starting News Summary API on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
