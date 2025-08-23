import redis
import json
from datetime import datetime
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create config object directly instead of importing
class Config:
    REDIS_HOST_NEWS = os.environ.get('REDIS_HOST_NEW')
    REDIS_PORT_NEWS = os.environ.get('REDIS_PORT_NEW') 
    REDIS_PASSWORD_NEWS = os.environ.get('REDIS_PASSWORD_NEW')
    REDIS_HOST_STOCK = os.environ.get('REDIS_HOST_STOCK')
    REDIS_PORT_STOCK = os.environ.get('REDIS_PORT_STOCK')
    REDIS_PASSWORD_STOCK = os.environ.get('REDIS_PASSWORD_STOCK')
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')

config = Config()

# --- Redis cho phần tin tức ---
try:
    pool_news = redis.ConnectionPool(
        host=config.REDIS_HOST_NEWS,
        port=config.REDIS_PORT_NEWS,
        password=config.REDIS_PASSWORD_NEWS,
        decode_responses=True
    )
    redis_client_news = redis.Redis(connection_pool=pool_news)
    redis_client_news.ping()
    print("Đã tạo Redis connection pool và client thành công cho phần tin tức.")
except Exception as e:
    print(f"Lỗi khi khởi tạo Redis News: {e}")
    redis_client_news = None

# --- Redis cho phần cổ phiếu ---
try:
    pool_stock = redis.ConnectionPool(
        host=config.REDIS_HOST_STOCK,
        port=config.REDIS_PORT_STOCK,
        password=config.REDIS_PASSWORD_STOCK,
        decode_responses=True
    )
    redis_client_stock = redis.Redis(connection_pool=pool_stock)
    redis_client_stock.ping()
    print("Đã tạo Redis connection pool và client thành công cho phần cổ phiếu.")
except Exception as e:
    print(f"Lỗi khi khởi tạo Redis Stock: {e}")
    redis_client_stock = None

# Supabase Client
try:
    supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
    print("Kết nối Supabase thành công.")
except Exception as e:
    print(f"Lỗi kết nối Supabase: {e}")
    supabase = None

# --- HÀM LẤY DỮ LIỆU ĐÃ CẬP NHẬT VỚI PAGINATION ---
def get_news_from_db(industry=None, sentiment=None, date=None, page=1, limit=5):
    if not redis_client_news:
        return {
            "items": [],
            "total": 0,
            "page": page,
            "limit": limit,
            "total_pages": 0
        }

    # 1. Xác định key Redis để lấy dữ liệu ngành
    redis_key = f"news:{industry}" if industry else "news:all"
    print(f"Đang lấy dữ liệu từ Redis với key: '{redis_key}' - Page: {page}, Limit: {limit}")

    try:
        json_data = redis_client_news.get(redis_key)
        if not json_data:
            return {
                "items": [],
                "total": 0,
                "page": page,
                "limit": limit,
                "total_pages": 0
            }

        filtered_data = json.loads(json_data)

        # 2. LỌC THEO SENTIMENT (NẾU CÓ)
        if sentiment:
            print(f"Thực hiện lọc với sentiment: {sentiment}")
            filtered_data = [
                news for news in filtered_data 
                if sentiment in news.get('influence', [])
            ]

        # 3. LỌC THEO NGÀY (NẾU CÓ)
        if date:
            print(f"Thực hiện lọc với ngày: {date}")
            # Chuyển định dạng ngày từ YYYY-MM-DD (frontend) sang DD/MM/YYYY (trong cache)
            try:
                date_obj = datetime.strptime(date, '%Y-%m-%d')
                date_to_compare = date_obj.strftime('%d/%m/%Y')
                
                filtered_data = [
                    news for news in filtered_data
                    if news.get('date') == date_to_compare
                ]
            except ValueError:
                # Bỏ qua nếu định dạng ngày không hợp lệ
                print(f"Định dạng ngày không hợp lệ: {date}")
                pass

        # 4. PAGINATION LOGIC
        total_items = len(filtered_data)
        total_pages = (total_items + limit - 1) // limit  # Ceiling division
        
        # Calculate start and end indices for pagination
        start_index = (page - 1) * limit
        end_index = start_index + limit
        
        # Slice the data for current page
        paginated_data = filtered_data[start_index:end_index]
        
        # Return paginated result with metadata
        return {
            "items": paginated_data,
            "total": total_items,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }

    except Exception as e:
        print(f"Đã xảy ra lỗi khi xử lý dữ liệu từ Redis: {e}")
        return {
            "items": [],
            "total": 0,
            "page": page,
            "limit": limit,
            "total_pages": 0
        }

# --- CÁC HÀM MỚI CHO BOOKMARK ---

def get_user_from_token(request):
    """Xác thực JWT và lấy thông tin người dùng."""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    jwt_token = auth_header.split(' ')[1]
    user_response = supabase.auth.get_user(jwt_token)
    return user_response.user

def get_bookmarks(user_id: str):
    """Lấy tất cả bookmark của một người dùng."""
    response = supabase.table('bookmarks').select('*').eq('user_id', user_id).order('created_at', desc=True).execute()
    return response.data

def check_bookmark_exists(user_id: str, article_id: str):
    """Kiểm tra xem bookmark đã tồn tại hay chưa."""
    response = supabase.table('bookmarks').select('id').eq('user_id', user_id).eq('article_id', article_id).execute()
    return len(response.data) > 0

def add_bookmark(user_id: str, article_data: dict):
    """Thêm một bookmark mới với duplicate check."""
    # Ưu tiên article_id từ frontend, fallback về logic cũ
    article_id = (article_data.get('article_id') or 
                article_data.get('id') or 
                article_data.get('news_id') or 
                str(hash(str(article_data))))
    
    # Kiểm tra duplicate
    if check_bookmark_exists(user_id, article_id):
        raise ValueError("Bài báo đã được bookmark")
    
    # Thêm user_id và article_id vào dữ liệu trước khi insert
    response = supabase.table('bookmarks').insert({
        'user_id': user_id,
        'article_id': article_id,
        'article_data': article_data
    }).execute()
    return response.data[0]

def remove_bookmark_by_article(user_id: str, article_id: str):
    """Xóa bookmark dựa trên article_id."""
    response = supabase.table('bookmarks').delete().eq('user_id', user_id).eq('article_id', article_id).execute()
    return response.data

def delete_bookmark(user_id: str, bookmark_id: int):
    """Xóa một bookmark dựa trên ID của nó và user_id."""
    supabase.table('bookmarks').delete().eq('id', bookmark_id).eq('user_id', user_id).execute()

# Mở file services.py và thêm hàm này vào cuối file

def get_stock_data_from_redis(ticker: str, time_range: str = 'all'):
    """
    Lấy dữ liệu lịch sử giá của một cổ phiếu từ cache trên Redis.
    Hàm này nhận vào mã ticker và khung thời gian (ví dụ: '1M', '1Y', 'all').
    """
    if not redis_client_stock:
        print("Lỗi: Kết nối Redis chưa được thiết lập.")
        return []

    # 1. Xây dựng key Redis dựa trên ticker và khung thời gian
    # Ví dụ: "stock:FPT:1Y" hoặc "stock:VCB:all"
    redis_key = f"stock:{ticker}:{time_range}"
    
    print(f"Đang lấy dữ liệu từ Redis với key: '{redis_key}'")

    try:
        # 2. Lấy dữ liệu dạng chuỗi JSON từ Redis
        json_data = redis_client_stock.get(redis_key)

        # 3. Kiểm tra xem key có tồn tại hay không
        if not json_data:
            print(f"Key '{redis_key}' không tồn tại trong Redis.")
            return []

        # 4. Chuyển đổi chuỗi JSON thành đối tượng Python và trả về
        filtered_data = json.loads(json_data)
        return filtered_data

    except Exception as e:
        print(f"Đã xảy ra lỗi khi xử lý dữ liệu cổ phiếu từ Redis: {e}")
        return []