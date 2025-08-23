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

# 🔇 Tắt hoàn toàn các warning và log không cần thiết
warnings.filterwarnings("ignore")
logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.getLogger('selenium').setLevel(logging.ERROR)

# Tắt Chrome logs tại system level
os.environ['WDM_LOG_LEVEL'] = '0'
os.environ['WDM_PRINT_FIRST_LINE'] = 'False'

# Import centralized database system
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database import SupabaseManager, DatabaseConfig

# Helper functions
def get_database_manager():
    """Get database manager instance"""
    return SupabaseManager()

# 🔹 Chuyển đổi định dạng ngày cho Supabase
def convert_date_for_supabase(date_str):
    """Chuyển đổi định dạng ngày từ DD/MM/YYYY sang YYYY-MM-DD cho Supabase"""
    try:
        # 🔧 FIX: Xử lý nhiều format ngày khác nhau
        if not date_str or date_str.strip() == "" or date_str.strip() == "-":
            print(f"❌ Lỗi format ngày: empty string")
            return None
            
        date_str = date_str.strip()
        
        # Thử format DD/MM/YYYY
        try:
            dt = datetime.strptime(date_str, "%d/%m/%Y")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
            
        # Thử format DD-MM-YYYY  
        try:
            dt = datetime.strptime(date_str, "%d-%m-%Y")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
            
        # Thử format YYYY-MM-DD (đã đúng format)
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
            
        print(f"❌ Lỗi format ngày: {date_str} (không match format nào)")
        return None
        
    except Exception as e:
        print(f"❌ Lỗi format ngày: {date_str} - {e}")
        return None


# 🔹 Hàm upsert (insert hoặc update) với Supabase API - return True nếu có update
def upsert_stock_data(db_manager, table_name, row):
    """
    Insert hoặc Update dữ liệu stock vào Supabase
    - Nếu ngày chưa tồn tại: INSERT mới
    - Nếu ngày đã tồn tại: UPDATE với giá trị mới
    
    Returns:
        bool: True nếu có thay đổi (insert hoặc update), False nếu không thay đổi
    """
    try:
        formatted_date = convert_date_for_supabase(row["date"])
        if not formatted_date:
            print(f"❌ Lỗi format ngày: {row['date']}")
            return False

        # Hàm helper để chuyển đổi giá sang float
        def safe_float(value_str):
            """Chuyển đổi chuỗi số có dấu phẩy thành float"""
            if not value_str or value_str == "" or value_str == "-":
                return 0.0
            return float(str(value_str).replace(",", ""))

        # Chuẩn bị dữ liệu
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
        
        # Kiểm tra dữ liệu đã tồn tại theo ngày
        existing = supabase_client.table(table_name).select("*").eq("date", formatted_date).execute()
        
        if existing.data:
            # CẬP NHẬT dữ liệu hiện có
            existing_record = existing.data[0]
            
            # So sánh để xem có thay đổi không (sử dụng safe comparison)
            def safe_compare(existing_val, new_val):
                """So sánh an toàn giữa giá trị cũ và mới"""
                try:
                    # Nếu existing_val là string có dấu phẩy, xóa dấu phẩy trước khi so sánh
                    if isinstance(existing_val, str) and existing_val != "EMPTY":
                        existing_float = float(existing_val.replace(",", ""))
                    else:
                        existing_float = float(existing_val) if existing_val and existing_val != "EMPTY" else 0.0
                    
                    # Nếu new_val là string có dấu phẩy, xóa dấu phẩy
                    if isinstance(new_val, str) and new_val != "EMPTY":
                        new_float = float(new_val.replace(",", ""))
                    else:
                        new_float = float(new_val) if new_val and new_val != "EMPTY" else 0.0
                        
                    return existing_float != new_float
                except (ValueError, TypeError):
                    return True  # Nếu không convert được thì coi như có thay đổi
            
            needs_update = (
                safe_compare(existing_record.get('close_price', 0), data_to_upsert['close_price']) or
                safe_compare(existing_record.get('open_price', 0), data_to_upsert['open_price']) or
                safe_compare(existing_record.get('high_price', 0), data_to_upsert['high_price']) or
                safe_compare(existing_record.get('low_price', 0), data_to_upsert['low_price'])
            )
            
            if needs_update:
                result = supabase_client.table(table_name).update(data_to_upsert).eq("date", formatted_date).execute()
                if result.data:
                    return True  # Có cập nhật
                else:
                    print(f"❌ Lỗi khi cập nhật: {row['date']}")
                    return False
            # Không print gì nếu không có thay đổi để tránh gây hiểu lầm
            return False  # Không có thay đổi
        else:
            # THÊM MỚI dữ liệu
            result = supabase_client.table(table_name).insert(data_to_upsert).execute()
            
            if result.data:
                return True  # Có thêm mới
            else:
                print(f"❌ Lỗi khi thêm: {row['date']}")
                return False
                
    except Exception as e:
        print(f"❌ Lỗi upsert_stock_data: {e}")
        print(f"   Dữ liệu: {row}")
        return False

def setup_driver():
    """Setup Chrome driver với các options tối ưu và tắt hoàn toàn mọi log"""
    options = Options()
    options.add_argument("--headless")  # Chạy ẩn browser
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    # 🔇 Tắt hoàn toàn các log không cần thiết
    options.add_argument("--disable-logging")
    options.add_argument("--log-level=3")  # Chỉ hiện FATAL errors
    options.add_argument("--silent")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-images")
    options.add_argument("--disable-javascript-harmony-shipping")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-features=TranslateUI,VizDisplayCompositor")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-sync")
    options.add_argument("--metrics-recording-only")
    options.add_argument("--no-first-run")
    
    # Tắt WebRTC và các services khác
    options.add_argument("--disable-webrtc")
    options.add_argument("--disable-web-security")
    
    # 🔇 Tắt DevTools và các thông báo debugging
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
    
    # 🔇 Tắt hoàn toàn console output
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_experimental_option('useAutomationExtension', False)
    
    return webdriver.Chrome(options=options)

# Global variables for dashboard tracking
dashboard_results = []
total_start_time = None
total_start_time_str = None

def print_dashboard_header():
    """Print dashboard header"""
    print("\n" + "█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + "� SPA VIP STOCK PRICE CRAWLER DASHBOARD".center(78) + "█")
    print("█" + " " * 78 + "█")
    print("█" + f"⏰ Started: {total_start_time_str}".center(78) + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)

def print_stock_progress(current, total, stock_code):
    """Print current stock progress"""
    progress_bar = "█" * int((current / total) * 30)
    empty_bar = "░" * (30 - int((current / total) * 30))
    percentage = (current / total) * 100
    
    print(f"\n┌─{'─' * 76}─┐")
    print(f"│ 📊 PROCESSING STOCK [{current}/{total}]: {stock_code}".ljust(77) + " │")
    print(f"│ Progress: [{progress_bar}{empty_bar}] {percentage:.1f}%".ljust(77) + " │")
    print(f"└─{'─' * 76}─┘")

def print_stock_result(stock_code, duration, updated_dates, crawled_count, status="SUCCESS"):
    """Store stock result for dashboard"""
    result = {
        'stock': stock_code,
        'status': status,
        'duration': duration,
        'updated_dates': updated_dates,
        'crawled_count': crawled_count
    }
    dashboard_results.append(result)
    
    # Print individual result
    status_icon = "✅" if status == "SUCCESS" else "❌"
    update_info = f"{len(updated_dates)} updates" if updated_dates else "No changes"
    
    print(f"│ {status_icon} {stock_code}: {duration:.1f}s | {update_info} | {crawled_count} rows processed".ljust(77) + " │")

def print_dashboard_summary():
    """Print final dashboard summary"""
    total_end_time = time.time()
    total_end_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_duration = total_end_time - total_start_time
    
    successful_stocks = [r for r in dashboard_results if r['status'] == 'SUCCESS']
    failed_stocks = [r for r in dashboard_results if r['status'] == 'FAILED']
    total_updates = sum(len(r['updated_dates']) for r in dashboard_results)
    
    print("\n" + "█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + "🎉 CRAWLING COMPLETED - SUMMARY DASHBOARD".center(78) + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)
    
    print(f"┌─{'─' * 76}─┐")
    print(f"│ ⏰ TIMING INFORMATION".ljust(77) + " │")
    print(f"│ {'─' * 76} │")
    print(f"│ Start Time    : {total_start_time_str}".ljust(77) + " │")
    print(f"│ End Time      : {total_end_time_str}".ljust(77) + " │")
    print(f"│ Total Duration: {total_duration:.2f}s ({total_duration/60:.1f} minutes)".ljust(77) + " │")
    print(f"│ Avg per Stock : {total_duration/len(dashboard_results):.2f}s".ljust(77) + " │")
    print(f"└─{'─' * 76}─┘")
    
    print(f"┌─{'─' * 76}─┐")
    print(f"│ 📊 PROCESSING STATISTICS".ljust(77) + " │")
    print(f"│ {'─' * 76} │")
    print(f"│ Total Stocks  : {len(dashboard_results)}".ljust(77) + " │")
    print(f"│ Successful    : {len(successful_stocks)} ✅".ljust(77) + " │")
    print(f"│ Failed        : {len(failed_stocks)} ❌".ljust(77) + " │")
    print(f"│ Total Updates : {total_updates} records".ljust(77) + " │")
    print(f"│ Success Rate  : {len(successful_stocks)/len(dashboard_results)*100:.1f}%".ljust(77) + " │")
    print(f"└─{'─' * 76}─┘")
    
    print(f"┌─{'─' * 76}─┐")
    print(f"│ 📋 DETAILED RESULTS".ljust(77) + " │")
    print(f"│ {'─' * 76} │")
    for result in dashboard_results:
        status_icon = "✅" if result['status'] == 'SUCCESS' else "❌"
        update_count = len(result['updated_dates'])
        update_dates = ', '.join(result['updated_dates'][:3]) + ('...' if len(result['updated_dates']) > 3 else '')
        
        print(f"│ {status_icon} {result['stock']:<4} │ {result['duration']:>5.1f}s │ {update_count:>2} updates │ {result['crawled_count']:>2} rows".ljust(77) + " │")
        if result['updated_dates']:
            print(f"│      └─ Dates: {update_dates}".ljust(77) + " │")
    print(f"└─{'─' * 76}─┘")
    
    print("\n" + "█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + "🎯 STOCK PRICE CRAWLING COMPLETED SUCCESSFULLY!".center(78) + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)
def crawl_and_save_stock(stock_code, max_rows=5):
    """
    Crawl dữ liệu cổ phiếu từ Simplize (chỉ crawl 5 dòng đầu tiên để tối ưu)
    
    Args:
        stock_code: Mã cổ phiếu (VD: FPT, GAS, VCB, IMP)
        max_rows: Số dòng tối đa cần crawl (mặc định: 5 ngày gần nhất)
    """
    start_time = time.time()
    
    driver = setup_driver()
    db_manager = get_database_manager()

    url = f"https://simplize.vn/co-phieu/{stock_code}/lich-su-gia"
    driver.get(url)
    wait = WebDriverWait(driver, 10)
    time.sleep(2)

    table_name = f"{stock_code}_Stock"
    crawled_count = 0  # Đếm số dòng đã crawl
    updated_dates = []  # Track các ngày được update

    try:
        time.sleep(2)

        try:
            # Đợi table load
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "tr.simplize-table-row-level-0")))
            
            # Lấy tất cả rows sử dụng CSS selector chính xác từ fix
            rows = driver.find_elements(By.CSS_SELECTOR, "tr.simplize-table-row-level-0")
                        
            for row in rows:
                # ⚡ Dừng khi đã crawl đủ số dòng cần thiết
                if crawled_count >= max_rows:
                    break
                    
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", row)
                    time.sleep(0.1)  # Cho DOM kịp render

                    # Lấy dữ liệu từ dòng hiện tại
                    cols = row.find_elements(By.CSS_SELECTOR, "td")
                    if len(cols) >= 8:
                        # 🔧 FIX: Lấy text từ h6 element như trong fix_simplize_crawl.py
                        date = cols[0].find_element(By.TAG_NAME, "h6").text.strip()
                        values = []
                        
                        for i in range(1, 8):
                            try:
                                val = cols[i].find_element(By.TAG_NAME, "h6").text.strip()
                            except:
                                val = "-"
                            values.append(val)

                        data_row = {
                            "date": date,               # Ngày
                            "open_price": values[0],    # Giá mở cửa
                            "high_price": values[1],    # Giá cao nhất
                            "low_price": values[2],     # Giá thấp nhất
                            "close_price": values[3],   # Giá đóng cửa
                            "change": values[4],        # Thay đổi giá
                            "change_pct": values[5],    # % Thay đổi
                            "volume": values[6]         # Khối lượng
                        }

                        # Check nếu có update và track ngày
                        if upsert_stock_data(db_manager, table_name, data_row):
                            updated_dates.append(date)
                        
                        crawled_count += 1
                        
                except Exception as e:
                    print(f"❌ Lỗi dòng: {e}")
                    continue

        except Exception as e:
            print(f"❌ Không lấy được dữ liệu cho mã {stock_code}: {e}")

    except Exception as e:
        print(f"❌ Lỗi trong quá trình crawl: {e}")
    finally:
        driver.quit()
        db_manager.close_connections()
        
        # Tính toán thời gian
        end_time = time.time()
        duration = end_time - start_time
        
        # Store result simply
        result = {
            'stock': stock_code,
            'duration': duration,
            'updated_dates': updated_dates,
            'crawled_count': crawled_count
        }
        dashboard_results.append(result)
        
        # Không print gì ở đây, sẽ hiển thị trong bảng cuối cùng

def main_stock_simplize():
    """Hàm chính để crawl nhiều mã cổ phiếu - hiển thị bảng cuối cùng"""
    global total_start_time, dashboard_results
    
    stock_codes = ["FPT","GAS","VCB","IMP"]  
    dashboard_results = []

    # Bắt đầu
    total_start_time = time.time()
    start_time_str = datetime.now().strftime("%H:%M:%S")
    
    print("\n" + "═" * 60)
    print("🚀 SPA STOCK PRICE CRAWLER".center(60))
    print(f"⏰ Started: {start_time_str}".center(60))
    print(f"📋 Stocks: {', '.join(stock_codes)}".center(60))
    print("═" * 60)
    print("\n🔄 Processing stocks")
    print("─" * 60)
    
    for i, code in enumerate(stock_codes, 1):
        try:
            print(f"[{i}/{len(stock_codes)}] Crawling {code}...")
            crawl_and_save_stock(code, max_rows=5)  
            
            if i < len(stock_codes):
                time.sleep(3)
                
        except Exception as e:
            # Add failed result
            result = {
                'stock': code,
                'duration': 0,
                'updated_dates': [],
                'crawled_count': 0,
                'status': 'FAILED'
            }
            dashboard_results.append(result)
            continue
    
    # Hiển thị bảng kết quả cuối cùng
    total_end_time = time.time()
    total_duration = total_end_time - total_start_time
    total_updates = sum(len(r['updated_dates']) for r in dashboard_results)
    
    print("\n" + "═" * 60)
    print("🎉 CRAWLING COMPLETED - RESULTS".center(60))
    print("═" * 60)
    
    # Table header
    print("┌──────┬────────┬──────────────┬─────────────────────┐")
    print("│ Code │ Time   │ Status       │ Updated Dates       │")
    print("├──────┼────────┼──────────────┼─────────────────────┤")
    
    # Table rows
    for result in dashboard_results:
        status = result.get('status', 'SUCCESS')
        if status == 'FAILED':
            print(f"│ ❌ {result['stock']:<4} │   ERROR │ Failed       │ No updates          │")
        else:
            update_count = len(result['updated_dates'])
            if update_count > 0:
                # Hiển thị tối đa 2 ngày đầu tiên, nếu nhiều hơn thì thêm "..."
                dates_display = ', '.join(result['updated_dates'][:2])
                if update_count > 2:
                    dates_display += f" +{update_count-2} more"
                status_text = f"{update_count} updates"
            else:
                dates_display = "No changes"
                status_text = "No changes"
            
            print(f"│ ✅ {result['stock']:<4} │ {result['duration']:>6.1f}s │ {status_text:<12} │ {dates_display:<19} │")
    
    # Table footer
    print("└──────┴────────┴──────────────┴─────────────────────┘")
    
    # Summary
    print("\n" + "═" * 60)
    print("📊 STOCK PRICE - SIMPLIZE".center(60))
    print("─" * 60)
    print(f"⏱️  Total Time    : {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
    print(f"📊 Total Updates : {total_updates} records")
    print(f"📈 Success Rate  : {len([r for r in dashboard_results if r.get('status', 'SUCCESS') == 'SUCCESS'])}/{len(stock_codes)} stocks")
    print(f"⚡ Avg per Stock : {total_duration/len(stock_codes):.1f}s")
    print("═" * 60)
if __name__ == "__main__":
    main_stock_simplize()
