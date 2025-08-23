import psycopg2
import psycopg2.extras
import redis
import json
from dotenv import load_dotenv
import os
import logging # Thư viện logging chuyên nghiệp
from fastapi import FastAPI, HTTPException

# --- CẤU HÌNH LOGGING ---
# Sử dụng logging thay cho print để dễ quản lý hơn trên server
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# --- CẤU HÌNH VÀ KẾT NỐI ---
def get_db_connection():
    load_dotenv()
    conn = psycopg2.connect(user=os.getenv("user"), password=os.getenv("password"), host=os.getenv("host"), port=os.getenv("port"), dbname=os.getenv("dbname"))
    return conn

def get_redis_connection():
    load_dotenv()
    r = redis.Redis(host=os.getenv("REDIS_HOST"), port=os.getenv("REDIS_PORT"), password=os.getenv("REDIS_PASSWORD"), decode_responses=True)
    return r

# --- HÀM PHỤ TRỢ MỚI ĐỂ TÁI SỬ DỤNG ---
def fetch_and_process_data_for_table(cursor, table_name: str):
    """
    Hàm này nhận vào tên bảng, truy vấn 5 ngày gần nhất,
    xử lý dữ liệu và trả về một danh sách các bản ghi đã được làm sạch.
    """
    logging.info(f"Bắt đầu lấy dữ liệu cho bảng: {table_name}...")
    
    # Sử dụng psycopg2 để truyền tên bảng một cách an toàn
    query = f"""
        SELECT * FROM "{table_name}" WHERE "date" IN (
            SELECT DISTINCT "date" FROM "{table_name}" WHERE "date" IS NOT NULL ORDER BY "date" DESC LIMIT 5
        ) ORDER BY "date" DESC;
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    logging.info(f"Đã lấy được {len(rows)} dòng từ bảng '{table_name}'.")

    processed_rows = []
    for row in rows:
        formatted_date = row['date'].strftime('%d/%m/%Y') if row.get('date') else ""
        
        # Áp dụng logic xử lý chung
        data = {
            'date': formatted_date,
            'industry': row.get('industry', ''),
            'title': row.get('title', ''),
            'summary': row.get('ai_summary', ''),
            'influence': row.get('sentiment', ''),
            'link': row.get('link', '')
        }

        industry_map = {"Finance": "Tài chính", "Technology": "Công nghệ", "Energy": "Năng lượng", "Healthcare": "Sức khỏe", "Other": "Khác"}
        data['industry'] = industry_map.get(data['industry'], data['industry'])
        
        influence_map = {"Positive": "Tích_cực", "Negative": "Tiêu_cực", "Neutral": "Trung_tính"}
        # Đổi tên key từ 'influence' thành 'hashtags' để nhất quán với frontend nếu cần
        data['influence'] = influence_map.get(data.pop('influence'), [])
        data['influence'] = data['influence'].split() if isinstance(data['influence'], str) else []

        processed_rows.append(data)
    
    return processed_rows

# --- HÀM CHÍNH ĐÃ ĐƯỢC CẬP NHẬT ---
def sync_postgres_to_redis():
    logging.info("Bắt đầu quá trình đồng bộ...")
    pg_conn = None
    try:
        pg_conn = get_db_connection()
        cursor = pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # =================================================================
        # PHẦN 1: XỬ LÝ DỮ LIỆU CHUNG (General_News) VÀ PHÂN LOẠI THEO NGÀNH
        # =================================================================
        general_news_data = fetch_and_process_data_for_table(cursor, "General_News")
        
        data_by_industry = {
            "Finance": [], "Technology": [], "Energy": [], "Healthcare": [], "Other": [],
            "all": general_news_data # Key 'all' sẽ chứa tất cả tin tức chung
        }

        # Phân loại tin tức chung vào các ngành
        for news_item in general_news_data:
            original_industry = next((key for key, value in {"Finance": "Tài chính", "Technology": "Công nghệ", "Energy": "Năng lượng", "Healthcare": "Sức khỏe", "Other": "Khác"}.items() if value == news_item['industry']), None)
            if original_industry and original_industry in data_by_industry:
                data_by_industry[original_industry].append(news_item)

        logging.info("Xử lý và phân loại dữ liệu 'General_News' hoàn tất.")
        
        # =================================================================
        # PHẦN 2: XỬ LÝ DỮ LIỆU RIÊNG CHO TỪNG CÔNG TY
        # =================================================================
        company_tables = ["FPT_News", "VCB_News", "IMP_News", "GAS_News"]
        data_by_company = {}

        for table in company_tables:
            company_news_data = fetch_and_process_data_for_table(cursor, table)
            # Lấy tên công ty từ tên bảng, ví dụ: "FPT_News" -> "FPT"
            company_name = table.split('_')[0]
            data_by_company[company_name] = company_news_data
        
        logging.info("Xử lý dữ liệu cho các công ty hoàn tất.")

        # =================================================================
        # PHẦN 3: ĐẨY TẤT CẢ DỮ LIỆU LÊN REDIS
        # =================================================================
        redis_conn = get_redis_connection()
        total_records_pushed = 0
        
        with redis_conn.pipeline() as pipe:
            # Đẩy dữ liệu đã phân loại theo ngành
            for industry_name, data_list in data_by_industry.items():
                if data_list:
                    redis_key = f"news:{industry_name}"
                    json_data = json.dumps(data_list, ensure_ascii=False)
                    pipe.set(redis_key, json_data, ex=86400)
                    logging.info(f"Đã chuẩn bị đẩy {len(data_list)} mục cho key ngành '{redis_key}'.")
                    total_records_pushed += len(data_list)
            
            # Đẩy dữ liệu của từng công ty
            for company_name, data_list in data_by_company.items():
                if data_list:
                    redis_key = f"news:{company_name}" # Tạo key mới, ví dụ: news:FPT
                    json_data = json.dumps(data_list, ensure_ascii=False)
                    pipe.set(redis_key, json_data, ex=86400)
                    logging.info(f"Đã chuẩn bị đẩy {len(data_list)} mục cho key công ty '{redis_key}'.")

            pipe.execute()
        
        logging.info("Đã đẩy thành công tất cả các key lên Redis.")
        return total_records_pushed # Trả về tổng số bản ghi đã xử lý

    except Exception as e:
        logging.error(f"Đã xảy ra lỗi trong quá trình đồng bộ: {e}")
        raise e
    finally:
        if pg_conn:
            pg_conn.close()
            logging.info("Đã đóng kết nối PostgreSQL.")
# --- TẠO ỨNG DỤNG VÀ API ENDPOINT ---

app = FastAPI()

# --- ENDPOINT MỚI ĐƯỢC THÊM VÀO ---
@app.get("/")
async def health_check():
    """
    Endpoint này chỉ dùng để kiểm tra xem server có hoạt động không.
    Google Apps Script sẽ gọi đến đây để giữ cho server không bị "ngủ".
    """
    return {"status": "alive"}


@app.post("/push_data")
async def trigger_sync_endpoint():
    """
    Endpoint này được gọi bởi n8n để kích hoạt quá trình đồng bộ dữ liệu.
    """
    try:
        # Gọi hàm logic chính
        record_count = sync_postgres_to_redis()
        # Trả về thông báo thành công
        return {"status": "success", "message": f"Data synced successfully. {record_count} records processed."}
    except Exception as e:
        # Nếu có lỗi, trả về mã lỗi 500
        raise HTTPException(status_code=500, detail=str(e))