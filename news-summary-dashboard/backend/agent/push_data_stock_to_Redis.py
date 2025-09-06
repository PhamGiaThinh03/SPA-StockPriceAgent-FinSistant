import psycopg2
import psycopg2.extras
import redis
import json
from dotenv import load_dotenv
import os
import logging
from fastapi import FastAPI, HTTPException

# --- LOGGING CONFIGURATION ---
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

# --- LOGIC FUNCTIONS ---

def process_rows(rows, price_column_name='close_price'):
    """
    Helper function to process data rows, convert and clean (for common cases).
    """
    processed_rows = []
    for row in rows:
        if row.get('date') is None or row.get(price_column_name) is None:
            logging.warning(f"Skipping row with missing data: date or {price_column_name} is NULL. Data: {row}")
            continue
        
        try:
            processed_rows.append({
                'date': row['date'].strftime('%Y-%m-%d'),
                'close_price': float(str(row[price_column_name]).replace(',', ''))
            })
        except (ValueError, TypeError) as e:
            logging.error(f"Cannot convert value {price_column_name} to number: '{row[price_column_name]}'. Error: {e}. Skipping this row.")
            continue
    return processed_rows

def process_rows_with_prediction(rows, price_column_name='close_price', keep_original_label=False):
    """
    Function to process data with the ability to keep the original label for predict_price.
    """
    processed_rows = []
    for row in rows:
        if row.get('date') is None or row.get(price_column_name) is None:
            logging.warning(f"Skipping row with missing data: date or {price_column_name} is NULL. Data: {row}")
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
            logging.error(f"Cannot convert value {price_column_name} to number: '{row[price_column_name]}'. Error: {e}. Skipping this row.")
            continue
    return processed_rows

def fetch_stock_data(cursor, stock_ticker: str, time_condition: str):
    """
    Helper function to fetch and process data for a stock with a specific time condition.
    Applies to cases: all, 1Y, 5Y.
    """
    table_name = f'"{stock_ticker}_Stock"'
    logging.info(f"Starting to fetch data for table: {table_name} with condition: {time_condition or 'All'}...")
    
    query = f"""
        SELECT "date", "close_price" 
        FROM {table_name} 
        {time_condition}
        ORDER BY "date" ASC;
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    logging.info(f"Fetched {len(rows)} rows.")
    
    return process_rows(rows, 'close_price')

def fetch_stock_data_combined(cursor, stock_ticker: str, interval_str: str):
    """
    NEW function: Fetch historical and prediction data within a specific interval,
    along with prediction data for the next 10 days.
    """
    table_name = f'"{stock_ticker}_Stock"'
    range_label = interval_str.replace("'", "").replace(" ", "_") # e.g., '1_month'
    logging.info(f"Starting to fetch COMBINED data ({range_label}) for table: {table_name}...")

    # 1. Fetch historical data (close_price) in the given interval
    past_historical_query = f"""
        SELECT "date", "close_price"
        FROM {table_name}
        WHERE "date" >= (NOW() - INTERVAL {interval_str}) AND "date" <= NOW()::date
        ORDER BY "date" ASC;
    """
    cursor.execute(past_historical_query)
    past_historical_rows = cursor.fetchall()
    logging.info(f"{range_label} - Past (close_price): Fetched {len(past_historical_rows)} rows.")
    processed_past_historical = process_rows(past_historical_rows, 'close_price')
    
    # 2. Fetch past prediction data (if any)
    past_prediction_query = f"""
        SELECT "date", "predict_price"
        FROM {table_name}
        WHERE "date" >= (NOW() - INTERVAL {interval_str}) AND "date" < NOW()::date
        AND "predict_price" IS NOT NULL
        ORDER BY "date" ASC;
    """
    cursor.execute(past_prediction_query)
    past_prediction_rows = cursor.fetchall()
    logging.info(f"{range_label} - Past (predict_price): Fetched {len(past_prediction_rows)} rows.")
    processed_past_predictions = process_rows_with_prediction(past_prediction_rows, 'predict_price', keep_original_label=True)

    # 3. Fetch prediction data from today to the next 10 days
    future_query = f"""
        SELECT "date", "predict_price"
        FROM {table_name}
        WHERE "date" >= NOW()::date AND "date" <= (NOW()::date + INTERVAL '10 days')
        ORDER BY "date" ASC;
    """
    cursor.execute(future_query)
    future_rows = cursor.fetchall()
    logging.info(f"{range_label} - Prediction: Fetched {len(future_rows)} rows.")
    processed_future_data = process_rows_with_prediction(future_rows, 'predict_price', keep_original_label=True)
    
    # 4. Combine all data
    all_past_data = processed_past_historical + processed_past_predictions
    combined_data = all_past_data + processed_future_data
    logging.info(f"{range_label} - Total: {len(combined_data)} rows after combining.")
    
    return combined_data

def sync_stock_data_to_redis():
    """
    Main function to synchronize stock price data from Postgres to Redis.
    """
    logging.info("Starting STOCK DATA synchronization process...")
    pg_conn = None
    
    STOCKS_TO_PROCESS = ["FPT", "GAS", "IMP", "VCB"]
    
    # --- UPDATE: Mark 3M as a special case ---
    TIME_RANGES = {
        "all": "",
        "1M": "SPECIAL_CASE",
        "3M": "SPECIAL_CASE",
        "1Y": "WHERE \"date\" >= NOW() - INTERVAL '1 year'",
        "5Y": "WHERE \"date\" >= NOW() - INTERVAL '5 years'",
    }

    # --- UPDATE: Create a map to define intervals for special cases ---
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
                    
                    # --- UPDATE: Logic to handle special cases flexibly ---
                    if condition == "SPECIAL_CASE":
                        # Get corresponding interval from map
                        interval = SPECIAL_CASE_INTERVALS.get(range_key)
                        if interval:
                            # Call new combined function with corresponding interval
                            stock_data = fetch_stock_data_combined(cursor, ticker, interval)
                        else:
                            logging.warning(f"Interval definition not found for special case: {range_key}")
                    else:
                        # Keep old logic for other cases (all, 1Y, 5Y)
                        stock_data = fetch_stock_data(cursor, ticker, condition)
                    
                    if stock_data:
                        redis_key = f"stock:{ticker}:{range_key}"
                        json_data = json.dumps(stock_data)
                        pipe.set(redis_key, json_data, ex=86400) # Expire after 1 day
                        logging.info(f"Prepared to push {len(stock_data)} records for key '{redis_key}'.")

            pipe.execute()
        
        logging.info("Successfully pushed all stock data to Redis.")
        return {"status": "success", "message": "Stock data synced successfully."}

    except Exception as e:
        logging.error(f"An error occurred during stock data synchronization: {e}")
        raise e
    finally:
        if pg_conn:
            pg_conn.close()
            logging.info("Closed PostgreSQL connection.")


# --- CREATE APPLICATION AND API ENDPOINT ---
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