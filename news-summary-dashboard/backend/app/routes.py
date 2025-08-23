from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from .config import current_config
from .services import get_news_from_db, get_bookmarks, add_bookmark, delete_bookmark, get_user_from_token, get_stock_data_from_redis, check_bookmark_exists, remove_bookmark_by_article

# Khởi tạo ứng dụng Flask
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

# Định nghĩa API endpoint tên là '/api/news'
@app.route('/api/news', methods=['GET'])
def news_endpoint():
    """
    Endpoint này sẽ được frontend gọi đến.
    Nó lấy dữ liệu từ database, chuyển thành JSON và trả về với pagination.
    """
    try:
        # Lấy tất cả các tham số từ URL
        industry_filter = request.args.get('industry')
        sentiment_filter = request.args.get('sentiment')
        date_filter = request.args.get('date') # Thêm tham số date
        
        # Pagination parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 5))
        
        # Validate pagination parameters
        if page < 1:
            page = 1
        if limit < 1 or limit > 100:  # Max 100 items per page
            limit = 5

        # Truyền tất cả các tham số vào hàm service
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
        return jsonify({"error": "Không thể lấy dữ liệu từ server"}), 500
    
# --- CÁC ENDPOINT MỚI CHO BOOKMARK ---

@app.route('/api/bookmarks', methods=['GET'])
def handle_get_bookmarks():
    try:
        user = get_user_from_token(request)
        if not user:
            return jsonify({"error": "Xác thực không hợp lệ"}), 401
        
        bookmarks = get_bookmarks(user.id)
        return jsonify(bookmarks)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/bookmarks', methods=['POST'])
def handle_add_bookmark():
    try:
        user = get_user_from_token(request)
        if not user:
            return jsonify({"error": "Xác thực không hợp lệ"}), 401
        
        article_data = request.get_json()
        new_bookmark = add_bookmark(user.id, article_data)
        return jsonify(new_bookmark), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 409  # Conflict
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/bookmarks/toggle', methods=['POST'])
def handle_toggle_bookmark():
    """Toggle bookmark - thêm nếu chưa có, xóa nếu đã có."""
    try:
        user = get_user_from_token(request)
        if not user:
            return jsonify({"error": "Xác thực không hợp lệ"}), 401
        
        article_data = request.get_json()
        # Ưu tiên sử dụng article_id từ frontend, fallback về id/news_id
        article_id = (article_data.get('article_id') or 
                    article_data.get('id') or 
                    article_data.get('news_id') or 
                    str(hash(str(article_data))))
        
        # Kiểm tra bookmark đã tồn tại
        if check_bookmark_exists(user.id, article_id):
            # Xóa bookmark
            remove_bookmark_by_article(user.id, article_id)
            return jsonify({"action": "removed", "bookmarked": False}), 200
        else:
            # Thêm bookmark
            new_bookmark = add_bookmark(user.id, article_data)
            return jsonify({"action": "added", "bookmarked": True, "bookmark": new_bookmark}), 201
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/bookmarks/<int:bookmark_id>', methods=['DELETE'])
def handle_delete_bookmark(bookmark_id):
    try:
        user = get_user_from_token(request)
        if not user:
            return jsonify({"error": "Xác thực không hợp lệ"}), 401
        
        delete_bookmark(user.id, bookmark_id)
        return jsonify({"message": "Bookmark đã được xóa"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/stocks/<string:ticker>/history', methods=['GET'])
def stock_history_endpoint(ticker):
    """
    Endpoint này trả về dữ liệu lịch sử giá của một cổ phiếu
    lấy từ cache trên Redis.
    """
    try:
        # Lấy tham số 'range' từ URL, nếu không có thì mặc định là 'all'
        time_range = request.args.get('range', 'all')
        
        # Chuyển mã ticker thành chữ hoa để đảm bảo tính nhất quán
        ticker_upper = ticker.upper()
        
        print(f"Fetching stock data for {ticker_upper} with range {time_range}")
        
        # Gọi hàm service mới với cả ticker và time_range
        stock_data = get_stock_data_from_redis(ticker_upper, time_range)

        if not stock_data:
            return jsonify({"error": f"Không tìm thấy dữ liệu cho {ticker_upper} với khung thời gian {time_range}"}), 404

        return jsonify(stock_data)

    except Exception as e:
        print(f"Error fetching stock history: {e}")
        return jsonify({"error": "Lỗi khi lấy dữ liệu lịch sử từ server"}), 500

# Debug endpoint để kiểm tra Redis stock keys
@app.route('/api/debug/redis-stock-keys', methods=['GET'])
def debug_redis_stock_keys():
    """Debug endpoint để xem có keys nào trong Redis stock"""
    try:
        from .services import redis_client_stock
        if not redis_client_stock:
            return jsonify({"error": "Redis stock connection not available"}), 500
        
        # Lấy tất cả keys pattern stock:*
        keys = redis_client_stock.keys('stock:*')
        return jsonify({"keys": keys, "total": len(keys)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
