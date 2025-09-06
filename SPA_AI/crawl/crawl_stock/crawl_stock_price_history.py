from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import pandas as pd
from datetime import datetime
import sys
import os
import warnings
import logging

# Turn off all warnings and unnecessary logs
warnings.filterwarnings("ignore")
logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.getLogger('selenium').setLevel(logging.ERROR)

# Turn off Chrome logs at system level
os.environ['WDM_LOG_LEVEL'] = '0'
os.environ['WDM_PRINT_FIRST_LINE'] = 'False'

# Import centralized database system
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database import SupabaseManager, DatabaseConfig

# Helper functions
def get_database_manager():
    """Get database manager instance"""
    return SupabaseManager()

# Convert date format for Supabase
def convert_date_for_supabase(date_str):
    """Convert date format from DD/MM/YYYY to YYYY-MM-DD for Supabase"""
    try:
        # Handle multiple date formats
        if not date_str or date_str.strip() == "" or date_str.strip() == "-":
            print(f"Error: empty date string")
            return None
            
        date_str = date_str.strip()
        
        # Try DD/MM/YYYY format
        try:
            dt = datetime.strptime(date_str, "%d/%m/%Y")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
            
        # Try DD-MM-YYYY format
        try:
            dt = datetime.strptime(date_str, "%d-%m-%Y")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
            
        # Try YYYY-MM-DD format (already correct)
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
            
        print(f"Error: {date_str} does not match any format")
        return None
        
    except Exception as e:
        print(f"Error parsing date {date_str}: {e}")
        return None


# Upsert (insert or update) with Supabase API - returns True if updated
def upsert_stock_data(db_manager, table_name, row):
    """
    Insert or update stock data into Supabase
    - If date does not exist: INSERT new
    - If date exists: UPDATE with new values
    
    Returns:
        bool: True if there is a change (insert or update), False otherwise
    """
    try:
        formatted_date = convert_date_for_supabase(row["date"])
        if not formatted_date:
            print(f"Error: invalid date {row['date']}")
            return False

        # Helper to convert price to float
        def safe_float(value_str):
            """Convert string with commas to float"""
            if not value_str or value_str == "" or value_str == "-":
                return 0.0
            return float(str(value_str).replace(",", ""))

        # Prepare data
        data_to_upsert = {
            "date": formatted_date,
            "open_price": f"{safe_float(row['open_price']):,.0f}" if safe_float(row["open_price"]) > 0 else "EMPTY",
            "high_price": f"{safe_float(row['high_price']):,.0f}" if safe_float(row["high_price"]) > 0 else "EMPTY", 
            "low_price": f"{safe_float(row['low_price']):,.0f}" if safe_float(row["low_price"]) > 0 else "EMPTY",
            "close_price": f"{safe_float(row['close_price']):,.0f}" if safe_float(row["close_price"]) > 0 else "EMPTY",
            "change": row["change"],
            "change_pct": row["change_pct"],
            "volume": row["volume"]
        }

        supabase_client = db_manager.get_supabase_client()
        
        # Check if data already exists for this date
        existing = supabase_client.table(table_name).select("*").eq("date", formatted_date).execute()
        
        if existing.data:
            # Update existing data
            existing_record = existing.data[0]
            
            # Compare to see if values changed
            def safe_compare(existing_val, new_val):
                """Safely compare old and new values"""
                try:
                    if isinstance(existing_val, str) and existing_val != "EMPTY":
                        existing_float = float(existing_val.replace(",", ""))
                    else:
                        existing_float = float(existing_val) if existing_val and existing_val != "EMPTY" else 0.0
                    
                    if isinstance(new_val, str) and new_val != "EMPTY":
                        new_float = float(new_val.replace(",", ""))
                    else:
                        new_float = float(new_val) if new_val and new_val != "EMPTY" else 0.0
                        
                    return existing_float != new_float
                except (ValueError, TypeError):
                    return True  # If cannot convert, consider it changed
            
            needs_update = (
                safe_compare(existing_record.get('close_price', 0), data_to_upsert['close_price']) or
                safe_compare(existing_record.get('open_price', 0), data_to_upsert['open_price']) or
                safe_compare(existing_record.get('high_price', 0), data_to_upsert['high_price']) or
                safe_compare(existing_record.get('low_price', 0), data_to_upsert['low_price'])
            )
            
            if needs_update:
                result = supabase_client.table(table_name).update(data_to_upsert).eq("date", formatted_date).execute()
                if result.data:
                    return True
                else:
                    print(f"Error updating {row['date']}")
                    return False
            return False
        else:
            # Insert new data
            result = supabase_client.table(table_name).insert(data_to_upsert).execute()
            
            if result.data:
                return True
            else:
                print(f"Error inserting {row['date']}")
                return False
                
    except Exception as e:
        print(f"Error in upsert_stock_data: {e}")
        print(f"   Data: {row}")
        return False

def setup_driver():
    """Setup Chrome driver with optimized options and suppress all logs"""
    options = Options()
    options.add_argument("--headless")  # Run browser headless
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    # Suppress unnecessary logs
    options.add_argument("--disable-logging")
    options.add_argument("--log-level=3")  # Only FATAL errors
    options.add_argument("--silent")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-images")
    options.add_argument("--disable-javascript-harmony-shipping")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-features=TranslateUI,VizDisplayCompositor")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-sync")
    options.add_argument("--metrics-recording-only")
    options.add_argument("--no-first-run")
    
    # Disable WebRTC and other services
    options.add_argument("--disable-webrtc")
    options.add_argument("--disable-web-security")
    
    # Disable DevTools and debugging messages
    options.add_argument("--disable-dev-tools")
    options.add_argument("--disable-remote-debugging")
    options.add_argument("--disable-remote-debugging-port")
    options.add_argument("--disable-component-extensions-with-background-pages")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-background-mode")
    options.add_argument("--disable-hang-monitor")
    options.add_argument("--disable-prompt-on-repost")
    options.add_argument("--disable-client-side-phishing-detection")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-translate")
    
    # Suppress all console output
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_experimental_option('useAutomationExtension', False)
    
    return webdriver.Chrome(options=options)

# Global variables for tracking
dashboard_results = []
total_start_time = None
total_start_time_str = None

def crawl_and_save_stock(stock_code, max_rows=5):
    """
    Crawl stock data from Simplize (only crawl first N rows to optimize)
    
    Args:
        stock_code: Stock symbol (e.g., FPT, GAS, VCB, IMP)
        max_rows: Maximum number of rows to crawl (default: last 5 days)
    """
    start_time = time.time()
    
    driver = setup_driver()
    db_manager = get_database_manager()

    url = f"https://simplize.vn/co-phieu/{stock_code}/lich-su-gia"
    driver.get(url)
    wait = WebDriverWait(driver, 10)
    time.sleep(2)

    table_name = f"{stock_code}_Stock"
    crawled_count = 0  # Count crawled rows
    updated_dates = []  # Track updated dates

    try:
        time.sleep(2)

        try:
            # Wait for table to load
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "tr.simplize-table-row-level-0")))
            
            # Get all rows using precise CSS selector
            rows = driver.find_elements(By.CSS_SELECTOR, "tr.simplize-table-row-level-0")
                        
            for row in rows:
                # Stop if enough rows crawled
                if crawled_count >= max_rows:
                    break
                    
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", row)
                    time.sleep(0.1)  # Allow DOM to render

                    # Get row data
                    cols = row.find_elements(By.CSS_SELECTOR, "td")
                    if len(cols) >= 8:
                        date = cols[0].find_element(By.TAG_NAME, "h6").text.strip()
                        values = []
                        
                        for i in range(1, 8):
                            try:
                                val = cols[i].find_element(By.TAG_NAME, "h6").text.strip()
                            except:
                                val = "-"
                            values.append(val)

                        data_row = {
                            "date": date,
                            "open_price": values[0],
                            "high_price": values[1],
                            "low_price": values[2],
                            "close_price": values[3],
                            "change": values[4],
                            "change_pct": values[5],
                            "volume": values[6]
                        }

                        # Check updates and track dates
                        if upsert_stock_data(db_manager, table_name, data_row):
                            updated_dates.append(date)
                        
                        crawled_count += 1
                        
                except Exception as e:
                    print(f"Row error: {e}")
                    continue

        except Exception as e:
            print(f"Cannot get data for stock {stock_code}: {e}")

    except Exception as e:
        print(f"Crawl error: {e}")
    finally:
        driver.quit()
        db_manager.close_connections()
