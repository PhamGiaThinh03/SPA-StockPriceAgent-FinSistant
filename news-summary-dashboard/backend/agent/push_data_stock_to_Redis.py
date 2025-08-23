import psycopg2
import psycopg2.extras
import redis
import json
from dotenv import load_dotenv
import os
import logging
from fastapi import FastAPI, HTTPException

# --- CẤU HÌNH LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_db_connection():
    load_dotenv()
    conn = psycopg2.connect(
        user=os.getenv("user"),
        password=os.getenv("password"),
        host=os.getenv("host"),
        port=os.getenv("port"),
        dbname=os.getenv("dbname")
    )
    return conn

def get_redis_connection():
    load_dotenv()
    r = redis.Redis(
        host=os.getenv("REDIS_HOST"),
        port=os.getenv("REDIS_PORT"),
        password=os.getenv("REDIS_PASSWORD"),
        decode_responses=True
    )
    return r

# --- HÀM LOGIC ---

def process_rows(rows, price_column_name='close_price'):
    """
    Hàm phụ trợ để xử lý các dòng dữ liệu, chuyển đổi và làm sạch (cho các trường hợp thông thường).
    """
    processed_rows = []
    for row in rows:
        if row.get('date') is None or row.get(price_column_name) is None:
            logging.warning(f"Bỏ qua dòng dữ liệu bị thiếu: date hoặc {price_column_name} là NULL. Dữ liệu: {row}")
            continue
        
        try:
            processed_rows.append({
                'date': row['date'].strftime('%Y-%m-%d'),
                'close_price': float(str(row[price_column_name]).replace(',', ''))
            })
        except (ValueError, TypeError) as e:
            logging.error(f"Không thể chuyển đổi giá trị {price_column_name} thành số: '{row[price_column_name]}'. Lỗi: {e}. Bỏ qua dòng này.")
            continue
    return processed_rows

def process_rows_with_prediction(rows, price_column_name='close_price', keep_original_label=False):
    """
    Hàm xử lý dữ liệu với khả năng giữ nguyên label gốc cho predict_price.
    """
    processed_rows = []
    for row in rows:
        if row.get('date') is None or row.get(price_column_name) is None:
            logging.warning(f"Bỏ qua dòng dữ liệu bị thiếu: date hoặc {price_column_name} là NULL. Dữ liệu: {row}")
            continue
        
        try:
            processed_row = {
                'date': row['date'].strftime('%Y-%m-%d'),
            }
            
            if keep_original_label and price_column_name == 'predict_price':
                processed_row['predict_price'] = float(str(row[price_column_name]).replace(',', ''))
            else:
                processed_row['close_price'] = float(str(row[price_column_name]).replace(',', ''))
                
            processed_rows.append(processed_row)
        except (ValueError, TypeError) as e:
            logging.error(f"Không thể chuyển đổi giá trị {price_column_name} thành số: '{row[price_column_name]}'. Lỗi: {e}. Bỏ qua dòng này.")
            continue
    return processed_rows

def fetch_stock_data(cursor, stock_ticker: str, time_condition: str):
    """
    Hàm phụ trợ để lấy và xử lý dữ liệu cho một cổ phiếu với một điều kiện thời gian cụ thể.
    Áp dụng cho các trường hợp: all, 1Y, 5Y.
    """
    table_name = f'"{stock_ticker}_Stock"'
    logging.info(f"Bắt đầu lấy dữ liệu cho bảng: {table_name} với điều kiện: {time_condition or 'Tất cả'}...")
    
    query = f"""
        SELECT "date", "close_price" 
        FROM {table_name} 
        {time_condition}
        ORDER BY "date" ASC;
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    logging.info(f"Đã lấy được {len(rows)} dòng.")
    
    return process_rows(rows, 'close_price')

def fetch_stock_data_combined(cursor, stock_ticker: str, interval_str: str):
    """
    Hàm MỚI: Lấy dữ liệu lịch sử và dữ liệu dự đoán trong một khoảng thời gian (interval) nhất định,
    cùng với dữ liệu dự đoán 10 ngày tới.
    """
    table_name = f'"{stock_ticker}_Stock"'
    range_label = interval_str.replace("'", "").replace(" ", "_") # e.g., '1_month'
    logging.info(f"Bắt đầu lấy dữ liệu KẾT HỢP ({range_label}) cho bảng: {table_name}...")

    # 1. Lấy dữ liệu quá khứ (close_price) trong khoảng thời gian đã cho
    past_historical_query = f"""
        SELECT "date", "close_price"
        FROM {table_name}
        WHERE "date" >= (NOW() - INTERVAL {interval_str}) AND "date" <= NOW()::date
        ORDER BY "date" ASC;
    """
    cursor.execute(past_historical_query)
    past_historical_rows = cursor.fetchall()
    logging.info(f"{range_label} - Quá khứ (close_price): Đã lấy được {len(past_historical_rows)} dòng.")
    processed_past_historical = process_rows(past_historical_rows, 'close_price')
    
    # 2. Lấy dữ liệu predict_price của quá khứ (nếu có)
    past_prediction_query = f"""
        SELECT "date", "predict_price"
        FROM {table_name}
        WHERE "date" >= (NOW() - INTERVAL {interval_str}) AND "date" < NOW()::date
        AND "predict_price" IS NOT NULL
        ORDER BY "date" ASC;
    """
    cursor.execute(past_prediction_query)
    past_prediction_rows = cursor.fetchall()
    logging.info(f"{range_label} - Quá khứ (predict_price): Đã lấy được {len(past_prediction_rows)} dòng.")
    processed_past_predictions = process_rows_with_prediction(past_prediction_rows, 'predict_price', keep_original_label=True)

    # 3. Lấy dữ liệu dự đoán (predict_price) từ hôm nay đến 10 ngày sau
    future_query = f"""
        SELECT "date", "predict_price"
        FROM {table_name}
        WHERE "date" >= NOW()::date AND "date" <= (NOW()::date + INTERVAL '10 days')
        ORDER BY "date" ASC;
    """
    cursor.execute(future_query)
    future_rows = cursor.fetchall()
    logging.info(f"{range_label} - Dự đoán: Đã lấy được {len(future_rows)} dòng.")
    processed_future_data = process_rows_with_prediction(future_rows, 'predict_price', keep_original_label=True)
    
    # 4. Kết hợp tất cả dữ liệu
    all_past_data = processed_past_historical + processed_past_predictions
    combined_data = all_past_data + processed_future_data
    logging.info(f"{range_label} - Tổng cộng: {len(combined_data)} dòng sau khi kết hợp.")
    
    return combined_data

def sync_stock_data_to_redis():
    """
    Hàm chính để đồng bộ dữ liệu giá cổ phiếu từ Postgres sang Redis.
    """
    logging.info("Bắt đầu quá trình đồng bộ dữ liệu CỔ PHIẾU...")
    pg_conn = None
    
    STOCKS_TO_PROCESS = ["FPT", "GAS", "IMP", "VCB"]
    
    # --- CẬP NHẬT: Đánh dấu 3M là trường hợp đặc biệt ---
    TIME_RANGES = {
        "all": "",
        "1M": "SPECIAL_CASE",
        "3M": "SPECIAL_CASE",
        "1Y": "WHERE \"date\" >= NOW() - INTERVAL '1 year'",
        "5Y": "WHERE \"date\" >= NOW() - INTERVAL '5 years'",
    }

    # --- CẬP NHẬT: Tạo một map để định nghĩa interval cho các trường hợp đặc biệt ---
    SPECIAL_CASE_INTERVALS = {
        "1M": "'1 month'",
        "3M": "'3 months'"
    }

    try:
        pg_conn = get_db_connection()
        cursor = pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        redis_conn = get_redis_connection()

        with redis_conn.pipeline() as pipe:
            for ticker in STOCKS_TO_PROCESS:
                for range_key, condition in TIME_RANGES.items():
                    stock_data = []
                    
                    # --- CẬP NHẬT: Logic để xử lý các trường hợp đặc biệt một cách linh hoạt ---
                    if condition == "SPECIAL_CASE":
                        # Lấy interval tương ứng từ map
                        interval = SPECIAL_CASE_INTERVALS.get(range_key)
                        if interval:
                            # Gọi hàm kết hợp mới với interval tương ứng
                            stock_data = fetch_stock_data_combined(cursor, ticker, interval)
                        else:
                            logging.warning(f"Không tìm thấy định nghĩa interval cho trường hợp đặc biệt: {range_key}")
                    else:
                        # Giữ nguyên logic cũ cho các trường hợp khác (all, 1Y, 5Y)
                        stock_data = fetch_stock_data(cursor, ticker, condition)
                    
                    if stock_data:
                        redis_key = f"stock:{ticker}:{range_key}"
                        json_data = json.dumps(stock_data)
                        pipe.set(redis_key, json_data, ex=86400) # Hết hạn sau 1 ngày
                        logging.info(f"Đã chuẩn bị đẩy {len(stock_data)} bản ghi cho key '{redis_key}'.")

            pipe.execute()
        
        logging.info("Đã đẩy thành công tất cả dữ liệu cổ phiếu lên Redis.")
        return {"status": "success", "message": "Stock data synced successfully."}

    except Exception as e:
        logging.error(f"Đã xảy ra lỗi trong quá trình đồng bộ dữ liệu cổ phiếu: {e}")
        raise e
    finally:
        if pg_conn:
            pg_conn.close()
            logging.info("Đã đóng kết nối PostgreSQL.")


# --- TẠO ỨNG DỤNG VÀ API ENDPOINT ---
app = FastAPI()

@app.get("/")
async def health_check():
    return {"status": "alive"}

@app.post("/push_stock_data")
async def trigger_stock_sync_endpoint():
    try:
        result = sync_stock_data_to_redis()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))