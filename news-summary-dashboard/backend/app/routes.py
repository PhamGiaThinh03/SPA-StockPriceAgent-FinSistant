from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from .config import current_config
from .services import get_news_from_db, get_bookmarks, add_bookmark, delete_bookmark, get_user_from_token, get_stock_data_from_redis, check_bookmark_exists, remove_bookmark_by_article

# Initialize Flask application
app = Flask(__name__)

# Apply configuration
app.config.from_object(current_config)

# Force production environment for HF Spaces
if os.environ.get('SPACE_ID'):  # HF Spaces sets this automatically
    os.environ['ENVIRONMENT'] = 'production'

# CORS configuration
if current_config.ENVIRONMENT == 'production' or os.environ.get('SPACE_ID'):
    # Production: allow specific origins
    allowed_origins = [
        "https://*.vercel.app",
        "https://localhost:3000",
        "http://localhost:3000",
        "*"  # Temporarily allow all for testing
    ]
    CORS(app, origins=allowed_origins, supports_credentials=True)
else:
    # Development: allow all origins
    CORS(app, supports_credentials=True)

# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring"""
    return jsonify({
        "status": "healthy",
        "message": "News Summary Dashboard API is running"
    }), 200

# Define API endpoint named '/api/news'
@app.route('/api/news', methods=['GET'])
def news_endpoint():
    """
    This endpoint will be called by the frontend.
    It fetches data from the database, converts it to JSON, and returns it with pagination.
    """
    try:
        # Get all parameters from URL
        industry_filter = request.args.get('industry')
        sentiment_filter = request.args.get('sentiment')
        date_filter = request.args.get('date') # Add date parameter
        
        # Pagination parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 5))
        
        # Validate pagination parameters
        if page < 1:
            page = 1
        if limit < 1 or limit > 100:  # Max 100 items per page
            limit = 5

        # Pass all parameters to the service function
        result = get_news_from_db(
            industry=industry_filter, 
            sentiment=sentiment_filter,
            date=date_filter,
            page=page,
            limit=limit
        )

        return jsonify(result)   

    except Exception as e:
        print(f"Error fetching news: {e}")
        return jsonify({"error": "Cannot fetch data from server"}), 500
    
# --- NEW ENDPOINTS FOR BOOKMARKS ---

@app.route('/api/bookmarks', methods=['GET'])
def handle_get_bookmarks():
    try:
        user = get_user_from_token(request)
        if not user:
            return jsonify({"error": "Invalid authentication"}), 401
        
        bookmarks = get_bookmarks(user.id)
        return jsonify(bookmarks)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/bookmarks', methods=['POST'])
def handle_add_bookmark():
    try:
        user = get_user_from_token(request)
        if not user:
            return jsonify({"error": "Invalid authentication"}), 401
        
        article_data = request.get_json()
        new_bookmark = add_bookmark(user.id, article_data)
        return jsonify(new_bookmark), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 409  # Conflict
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/bookmarks/toggle', methods=['POST'])
def handle_toggle_bookmark():
    """Toggle bookmark - add if not exists, remove if exists."""
    try:
        user = get_user_from_token(request)
        if not user:
            return jsonify({"error": "Invalid authentication"}), 401
        
        article_data = request.get_json()
        # Prefer using article_id from frontend, fallback to id/news_id
        article_id = (article_data.get('article_id') or 
                    article_data.get('id') or 
                    article_data.get('news_id') or 
                    str(hash(str(article_data))))
        
        # Check if bookmark exists
        if check_bookmark_exists(user.id, article_id):
            # Remove bookmark
            remove_bookmark_by_article(user.id, article_id)
            return jsonify({"action": "removed", "bookmarked": False}), 200
        else:
            # Add bookmark
            new_bookmark = add_bookmark(user.id, article_data)
            return jsonify({"action": "added", "bookmarked": True, "bookmark": new_bookmark}), 201
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/bookmarks/<int:bookmark_id>', methods=['DELETE'])
def handle_delete_bookmark(bookmark_id):
    try:
        user = get_user_from_token(request)
        if not user:
            return jsonify({"error": "Invalid authentication"}), 401
        
        delete_bookmark(user.id, bookmark_id)
        return jsonify({"message": "Bookmark has been deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/stocks/<string:ticker>/history', methods=['GET'])
def stock_history_endpoint(ticker):
    """
    This endpoint returns historical price data for a stock
    fetched from cache on Redis.
    """
    try:
        # Get 'range' parameter from URL, default to 'all' if not present
        time_range = request.args.get('range', 'all')
        
        # Convert ticker code to uppercase for consistency
        ticker_upper = ticker.upper()
        
        print(f"Fetching stock data for {ticker_upper} with range {time_range}")
        
        # Call new service function with both ticker and time_range
        stock_data = get_stock_data_from_redis(ticker_upper, time_range)

        if not stock_data:
            return jsonify({"error": f"No data found for {ticker_upper} with time range {time_range}"}), 404

        return jsonify(stock_data)

    except Exception as e:
        print(f"Error fetching stock history: {e}")
        return jsonify({"error": "Error fetching historical data from server"}), 500

# Debug endpoint to check Redis stock keys
@app.route('/api/debug/redis-stock-keys', methods=['GET'])
def debug_redis_stock_keys():
    """Debug endpoint to view keys in Redis stock"""
    try:
        from .services import redis_client_stock
        if not redis_client_stock:
            return jsonify({"error": "Redis stock connection not available"}), 500
        
        # Get all keys with pattern stock:*
        keys = redis_client_stock.keys('stock:*')
        return jsonify({"keys": keys, "total": len(keys)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
