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

# --- Redis for news section ---
try:
    pool_news = redis.ConnectionPool(
        host=config.REDIS_HOST_NEWS,
        port=config.REDIS_PORT_NEWS,
        password=config.REDIS_PASSWORD_NEWS,
        decode_responses=True
    )
    redis_client_news = redis.Redis(connection_pool=pool_news)
    redis_client_news.ping()
    print("Successfully created Redis connection pool and client for news section.")
except Exception as e:
    print(f"Error initializing Redis News: {e}")
    redis_client_news = None

# --- Redis for stock section ---
try:
    pool_stock = redis.ConnectionPool(
        host=config.REDIS_HOST_STOCK,
        port=config.REDIS_PORT_STOCK,
        password=config.REDIS_PASSWORD_STOCK,
        decode_responses=True
    )
    redis_client_stock = redis.Redis(connection_pool=pool_stock)
    redis_client_stock.ping()
    print("Successfully created Redis connection pool and client for stock section.")
except Exception as e:
    print(f"Error initializing Redis Stock: {e}")
    redis_client_stock = None

# Supabase Client
try:
    supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
    print("Supabase connection successful.")
except Exception as e:
    print(f"Supabase connection error: {e}")
    supabase = None

# --- FUNCTION TO GET UPDATED DATA WITH PAGINATION ---
def get_news_from_db(industry=None, sentiment=None, date=None, page=1, limit=5):
    if not redis_client_news:
        return {
            "items": [],
            "total": 0,
            "page": page,
            "limit": limit,
            "total_pages": 0
        }
    # 1. Determine Redis key to get industry data
    redis_key = f"news:{industry}" if industry else "news:all"
    print(f"Fetching data from Redis with key: '{redis_key}' - Page: {page}, Limit: {limit}")
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
        # 2. FILTER BY SENTIMENT (IF ANY)
        if sentiment:
            print(f"Filtering with sentiment: {sentiment}")
            filtered_data = [
                news for news in filtered_data 
                if sentiment in news.get('influence', [])
            ]
        # 3. FILTER BY DATE (IF ANY)
        if date:
            print(f"Filtering with date: {date}")
            # Convert date format from YYYY-MM-DD (frontend) to DD/MM/YYYY (in cache)
            try:
                date_obj = datetime.strptime(date, '%Y-%m-%d')
                date_to_compare = date_obj.strftime('%d/%m/%Y')
                filtered_data = [
                    news for news in filtered_data
                    if news.get('date') == date_to_compare
                ]
            except ValueError:
                # Skip if date format is invalid
                print(f"Invalid date format: {date}")
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
        print(f"Error processing data from Redis: {e}")
        return {
            "items": [],
            "total": 0,
            "page": page,
            "limit": limit,
            "total_pages": 0
        }

# --- NEW FUNCTIONS FOR BOOKMARKS ---

def get_user_from_token(request):
    """Authenticate JWT and get user information."""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    jwt_token = auth_header.split(' ')[1]
    user_response = supabase.auth.get_user(jwt_token)
    return user_response.user

def get_bookmarks(user_id: str):
    """Get all bookmarks of a user."""
    response = supabase.table('bookmarks').select('*').eq('user_id', user_id).order('created_at', desc=True).execute()
    return response.data

def check_bookmark_exists(user_id: str, article_id: str):
    """Check if a bookmark already exists."""
    response = supabase.table('bookmarks').select('id').eq('user_id', user_id).eq('article_id', article_id).execute()
    return len(response.data) > 0

def add_bookmark(user_id: str, article_data: dict):
    """Add a new bookmark with duplicate check."""
    # Prefer article_id from frontend, fallback to old logic
    article_id = (article_data.get('article_id') or 
                article_data.get('id') or 
                article_data.get('news_id') or 
                str(hash(str(article_data))))
    # Check for duplicate
    if check_bookmark_exists(user_id, article_id):
        raise ValueError("Article already bookmarked")
    # Add user_id and article_id to data before insert
    response = supabase.table('bookmarks').insert({
        'user_id': user_id,
        'article_id': article_id,
        'article_data': article_data
    }).execute()
    return response.data[0]

def remove_bookmark_by_article(user_id: str, article_id: str):
    """Remove bookmark by article_id."""
    response = supabase.table('bookmarks').delete().eq('user_id', user_id).eq('article_id', article_id).execute()
    return response.data

def delete_bookmark(user_id: str, bookmark_id: int):
    """Delete a bookmark by its ID and user_id."""
    supabase.table('bookmarks').delete().eq('id', bookmark_id).eq('user_id', user_id).execute()

# Open services.py and add this function at the end of the file

def get_stock_data_from_redis(ticker: str, time_range: str = 'all'):
    """
    Get historical price data of a stock from cache on Redis.
    This function takes a ticker and time range (e.g.: '1M', '1Y', 'all').
    """
    if not redis_client_stock:
        print("Error: Redis connection not established.")
        return []
    # 1. Build Redis key based on ticker and time range
    # Example: "stock:FPT:1Y" or "stock:VCB:all"
    redis_key = f"stock:{ticker}:{time_range}"
    print(f"Fetching data from Redis with key: '{redis_key}'")
    try:
        # 2. Get JSON string data from Redis
        json_data = redis_client_stock.get(redis_key)
        # 3. Check if key exists
        if not json_data:
            print(f"Key '{redis_key}' does not exist in Redis.")
            return []
        # 4. Convert JSON string to Python object and return
        filtered_data = json.loads(json_data)
        return filtered_data
    except Exception as e:
        print(f"Error processing stock data from Redis: {e}")
        return []