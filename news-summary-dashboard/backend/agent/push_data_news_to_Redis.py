import psycopg2
import psycopg2.extras
import redis
import json
from dotenv import load_dotenv
import os
import logging # Professional logging library
from fastapi import FastAPI, HTTPException

# --- LOGGING CONFIGURATION ---
# Use logging instead of print for better management on the server
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# --- CONFIGURATION AND CONNECTION ---
def get_db_connection():
    load_dotenv()
    conn = psycopg2.connect(user=os.getenv("user"), password=os.getenv("password"), host=os.getenv("host"), port=os.getenv("port"), dbname=os.getenv("dbname"))
    return conn

def get_redis_connection():
    load_dotenv()
    r = redis.Redis(host=os.getenv("REDIS_HOST"), port=os.getenv("REDIS_PORT"), password=os.getenv("REDIS_PASSWORD"), decode_responses=True)
    return r

# --- NEW HELPER FUNCTION FOR REUSE ---
def fetch_and_process_data_for_table(cursor, table_name: str):
    """
    This function takes a table name, queries the last 5 days,
    processes the data, and returns a list of cleaned records.
    """
    logging.info(f"Starting to fetch data for table: {table_name}...")
    # Use psycopg2 to safely pass the table name
    query = f"""
        SELECT * FROM "{table_name}" WHERE "date" IN (
            SELECT DISTINCT "date" FROM "{table_name}" WHERE "date" IS NOT NULL ORDER BY "date" DESC LIMIT 5
        ) ORDER BY "date" DESC;
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    logging.info(f"Fetched {len(rows)} rows from table '{table_name}'.")

    processed_rows = []
    for row in rows:
        formatted_date = row['date'].strftime('%d/%m/%Y') if row.get('date') else ""
        # Apply common processing logic
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
        # Rename key from 'influence' to 'hashtags' for consistency with frontend if needed
        data['influence'] = influence_map.get(data.pop('influence'), [])
        data['influence'] = data['influence'].split() if isinstance(data['influence'], str) else []

        processed_rows.append(data)
    return processed_rows

# --- UPDATED MAIN FUNCTION ---
def sync_postgres_to_redis():
    logging.info("Starting synchronization process...")
    pg_conn = None
    try:
        pg_conn = get_db_connection()
        cursor = pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        # =================================================================
        # PART 1: PROCESS GENERAL NEWS DATA AND CLASSIFY BY INDUSTRY
        # =================================================================
        general_news_data = fetch_and_process_data_for_table(cursor, "General_News")
        data_by_industry = {
            "Finance": [], "Technology": [], "Energy": [], "Healthcare": [], "Other": [],
            "all": general_news_data # Key 'all' will contain all general news
        }
        # Classify general news into industries
        for news_item in general_news_data:
            original_industry = next((key for key, value in {"Finance": "Tài chính", "Technology": "Công nghệ", "Energy": "Năng lượng", "Healthcare": "Sức khỏe", "Other": "Khác"}.items() if value == news_item['industry']), None)
            if original_industry and original_industry in data_by_industry:
                data_by_industry[original_industry].append(news_item)
        logging.info("Processing and classifying 'General_News' data completed.")
        # =================================================================
        # PART 2: PROCESS DATA FOR EACH COMPANY
        # =================================================================
        company_tables = ["FPT_News", "VCB_News", "IMP_News", "GAS_News"]
        data_by_company = {}
        for table in company_tables:
            company_news_data = fetch_and_process_data_for_table(cursor, table)
            # Get company name from table name, e.g., "FPT_News" -> "FPT"
            company_name = table.split('_')[0]
            data_by_company[company_name] = company_news_data
        logging.info("Processing data for companies completed.")
        # =================================================================
        # PART 3: PUSH ALL DATA TO REDIS
        # =================================================================
        redis_conn = get_redis_connection()
        total_records_pushed = 0
        with redis_conn.pipeline() as pipe:
            # Push data classified by industry
            for industry_name, data_list in data_by_industry.items():
                if data_list:
                    redis_key = f"news:{industry_name}"
                    json_data = json.dumps(data_list, ensure_ascii=False)
                    pipe.set(redis_key, json_data, ex=86400)
                    logging.info(f"Prepared to push {len(data_list)} items for industry key '{redis_key}'.")
                    total_records_pushed += len(data_list)
            # Push data for each company
            for company_name, data_list in data_by_company.items():
                if data_list:
                    redis_key = f"news:{company_name}" # Create new key, e.g.: news:FPT
                    json_data = json.dumps(data_list, ensure_ascii=False)
                    pipe.set(redis_key, json_data, ex=86400)
                    logging.info(f"Prepared to push {len(data_list)} items for company key '{redis_key}'.")
            pipe.execute()
        logging.info("Successfully pushed all keys to Redis.")
        return total_records_pushed # Return total number of processed records
    except Exception as e:
        logging.error(f"An error occurred during synchronization: {e}")
        raise e
    finally:
        if pg_conn:
            pg_conn.close()
            logging.info("Closed PostgreSQL connection.")
# --- CREATE APPLICATION AND API ENDPOINT ---

app = FastAPI()

# --- NEW ENDPOINT ADDED ---
@app.get("/")
async def health_check():
    """
    This endpoint is only used to check if the server is running.
    Google Apps Script will call this to keep the server awake.
    """
    return {"status": "alive"}


@app.post("/push_data")
async def trigger_sync_endpoint():
    """
    This endpoint is called by n8n to trigger the data synchronization process.
    """
    try:
        # Call main logic function
        record_count = sync_postgres_to_redis()
        # Return success message
        return {"status": "success", "message": f"Data synced successfully. {record_count} records processed."}
    except Exception as e:
        # If error occurs, return 500 error code
        raise HTTPException(status_code=500, detail=str(e))