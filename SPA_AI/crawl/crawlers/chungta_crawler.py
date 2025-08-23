from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import requests
import re
from datetime import datetime
import warnings
import logging

# 🔇 Tắt hoàn toàn các warning và log không cần thiết
warnings.filterwarnings("ignore")
logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.getLogger('selenium').setLevel(logging.ERROR)

# Import centralized database system
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database import SupabaseManager, DatabaseConfig, format_datetime_for_db

# Constants
STOCK_CODES = ["FPT", "GAS", "IMP", "VCB"]

# Helper functions
def get_database_manager():
    """Get database manager instance"""
    return SupabaseManager()

def get_table_name(stock_code=None, is_general=False):
    """Get table name using new config"""
    config = DatabaseConfig()
    return config.get_table_name(stock_code=stock_code, is_general=is_general)

def get_recent_links_from_db(db_manager, table_name, limit=50):
    """Lấy 50 link bài viết gần nhất từ database cho chungta crawling"""
    try:
        supabase_client = db_manager.get_supabase_client()
        # Thử dùng id thay vì created_at nếu không có created_at
        try:
            result = supabase_client.table(table_name).select("link").order("created_at", desc=True).limit(limit).execute()
        except Exception:
            # Fallback: sử dụng id hoặc không order
            try:
                result = supabase_client.table(table_name).select("link").order("id", desc=True).limit(limit).execute()
            except Exception:
                # Fallback cuối: chỉ lấy link không order
                result = supabase_client.table(table_name).select("link").limit(limit).execute()
        
        if result.data:
            return set(item['link'] for item in result.data if item.get('link'))
        return set()
    except Exception as e:
        print(f"❌ Lỗi khi lấy links từ DB: {e}")
        return set()

def check_stop_condition(links_to_check, existing_links):
    """
    Kiểm tra điều kiện dừng: 3 bài liên tiếp có trong DB
    Args:
        links_to_check: List các link cần kiểm tra (theo thứ tự từ trên xuống)
        existing_links: Set các link đã có trong DB
    Returns:
        int: Index để dừng (nếu tìm thấy 3 bài liên tiếp), -1 nếu không
    """
    consecutive_found = 0
    
    for i, link in enumerate(links_to_check):
        if link in existing_links:
            consecutive_found += 1
            if consecutive_found >= 3:
                # Dừng tại vị trí bài thứ 3 liên tiếp
                return i - 2  # Trả về index của bài đầu tiên trong 3 bài liên tiếp
        else:
            consecutive_found = 0  # Reset nếu không liên tiếp
    
    return -1  # Không tìm thấy 3 bài liên tiếp

def insert_article_to_database(db_manager, table_name, article_data, date_parser_func=None):
    """Insert article using new database system"""
    # Parse date if parser provided
    if date_parser_func and article_data.get("date"):
        try:
            parsed_date = date_parser_func(article_data["date"])
            if parsed_date:
                article_data["date"] = parsed_date
        except Exception:
            pass
    
    return db_manager.insert_article(table_name, article_data)

def normalize_date_only(raw_text):
    if not raw_text or raw_text.strip() == "" or raw_text.strip().upper() == "EMPTY":
        return None

    raw_text = raw_text.strip()

    # Trường hợp dạng 23-07-2025 - 06:57 AM
    try:
        dt = datetime.strptime(raw_text, "%d-%m-%Y - %I:%M %p")
        return format_datetime_for_db(dt)
    except:
        pass

    # Trường hợp dạng Thứ sáu, 25/7/2025 | 18:08GMT hoặc 30/7/2025
    try:
        match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", raw_text)
        if match:
            day, month, year = match.groups()
            dt = datetime(int(year), int(month), int(day))
            return format_datetime_for_db(dt)
    except:
        pass
    return None

# 🔹 Crawl dữ liệu từ Chungta.vn với tối ưu
def crawl_chungta(url, table_name, db_manager):
    """Crawl Chungta.vn với logic tối ưu"""
    start_time = time.time()
    
    existing_links = get_recent_links_from_db(db_manager, table_name, 100)  #100 news gần nhất

    options = Options()
    options.add_argument("--headless")  # Chạy ẩn để tránh bị interrupt
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Tắt logs
    options.add_argument("--disable-logging")
    options.add_argument("--log-level=3")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(options=options)

    driver.get(url)
    wait = WebDriverWait(driver, 10)

    MAX_PAGE = 1
    print(f"🔄 LOAD PAGE {MAX_PAGE}...")

    for i in range(MAX_PAGE):
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            button = wait.until(EC.element_to_be_clickable((By.ID, "load_more_redesign")))
            button.click()
            time.sleep(4)
        except:
            print(f"  ⚠️ Không thể load thêm trang (dừng tại page {i})")
            break

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    articles = soup.select("h3.title-news a")
    print(f"📄 Total {len(articles)} news from {MAX_PAGE} pages")
    # Tạo list các links để check
    all_links = []
    for a in articles:
        link = "https://chungta.vn" + a.get("href")
        all_links.append(link)
    
    # Kiểm tra điều kiện dừng (3 bài liên tiếp có trong DB)
    stop_index = check_stop_condition(all_links, existing_links)
    
    if stop_index >= 0:
        links_to_crawl = all_links[:stop_index]
        if len(links_to_crawl) > 0:
            print(f"🎯 Crawl {len(links_to_crawl)} bài viết mới")
        else:
            print(f"📰 No new news")
    else:
        # Lọc chỉ những link chưa có trong DB
        links_to_crawl = [link for link in all_links if link not in existing_links]
        if len(links_to_crawl) > 0:
            print(f"🎯 Crawl {len(links_to_crawl)} bài viết mới")
        else:
            print(f"📰 No new news")

    # Crawl các bài viết được chọn
    new_articles = 0
    crawled_count = 0
    duplicate_count = 0
    headers = {"User-Agent": "Mozilla/5.0"}

    for i, link in enumerate(links_to_crawl):
        try:
            print(f"🔗 [{i+1}/{len(links_to_crawl)}] {link}")
            
            res = requests.get(link, headers=headers, timeout=10)
            article_soup = BeautifulSoup(res.text, "html.parser")

            # Lấy title từ link ban đầu
            title_element = None
            for a in articles:
                if "https://chungta.vn" + a.get("href") == link:
                    title_element = a
                    break
            
            title_preview = title_element.get_text(strip=True) if title_element else ""
            
            title = article_soup.select_one("h1.title-detail")
            title = title.get_text(strip=True) if title else title_preview

            date = article_soup.select_one("span.time")
            date = date.get_text(strip=True) if date else "Không rõ ngày"

            content = article_soup.select_one("article.fck_detail.width_common")
            content = content.get_text(separator="\n", strip=True) if content else ""

            article_data = {
                "title": title,
                "date": date,
                "link": link,
                "content": content,
                "ai_summary": "" 
            }
            
            success = insert_article_to_database(db_manager, table_name, article_data, normalize_date_only)
            if success:
                new_articles += 1
                print(f"✅ Đã lưu bài viết: {title[:50]}...")
            else:
                duplicate_count += 1
                # Chỉ hiển thị 3 duplicate đầu tiên để tránh spam
                if duplicate_count <= 3:
                    print(f"⚠️  Duplicate title - skipped: {title[:50]}...")
                elif duplicate_count == 4:
                    print(f"⚠️  ... và {len(links_to_crawl) - i - 1} duplicates khác (không hiển thị)")
            
            crawled_count += 1
            time.sleep(1)  # Delay between requests

        except Exception as e:
            print(f"❌ Lỗi lấy bài {link}: {e}")
            continue

    # Tính toán kết quả
    end_time = time.time()
    duration = end_time - start_time
    
    return {
        'url': url,
        'duration': duration,
        'total_found': len(articles),
        'crawled_count': crawled_count,
        'new_articles': new_articles,
        'stopped_early': stop_index >= 0
    }

def main_chungta():
    """Main function với dashboard timing và thống kê"""
    start_time = time.time()
    start_time_str = datetime.now().strftime("%H:%M:%S")
    
    print("\n" + "═" * 60)
    print("🚀 CHUNGTA CRAWLER DASHBOARD".center(60))
    print(f"⏰ Started: {start_time_str}".center(60))
    print("═" * 60)

    urls = [
        "https://chungta.vn/kinh-doanh",
        "https://chungta.vn/cong-nghe"
    ]
    table_name = "FPT_News"  # Chung Ta lưu vào FPT_News vì có nhiều tin về FPT
    db_manager = get_database_manager()

    results = []
    
    for i, url in enumerate(urls, 1):
        print(f"\n🚀 ═════════ Processing URL [{i}/{len(urls)}]: {url} ═════════")
        print(f"📋 Save to ====>>>  {table_name}")
        
        result = crawl_chungta(url, table_name, db_manager)
        results.append(result)
        
        # Delay between URLs
        if i < len(urls):
            time.sleep(3)

    db_manager.close_connections()
    
    # Hiển thị dashboard kết quả
    end_time = time.time()
    total_duration = end_time - start_time
    total_found = sum(r['total_found'] for r in results)
    total_crawled = sum(r['crawled_count'] for r in results)
    total_new = sum(r['new_articles'] for r in results)
    
    print("\n" + "═" * 60)
    print("🎉 CRAWLING COMPLETED - RESULTS".center(60))
    print("═" * 60)
    
    # Table header
    print("┌──────────────────────────┬────────┬──────────────┬───────────────────┐")
    print("│ URL                      │ Time   │ Status       │ Saved Articles    │")
    print("├──────────────────────────┼────────┼──────────────┼───────────────────┤")
    
    # Table rows
    for result in results:
        url_short = result['url'].replace("https://chungta.vn/", "").ljust(24)[:24]
        duration = result['duration']
        new_count = result['new_articles']
        stopped = result['stopped_early']
        
        # Status đơn giản
        status = "No new news" if new_count == 0 else "New news"
        # Saved Articles = số bài thực sự được lưu
        results_text = f"{new_count} saved"
        
        print(f"│ {url_short} │ {duration:>6.1f}s │ {status:<12} │ {results_text:<17} │")
    
    # Table footer
    print("└──────────────────────────┴────────┴──────────────┴───────────────────┘")
    
    # Summary
    print("\n" + "═" * 60)
    print("📊 SUMMARY".center(60))
    print("─" * 60)
    print(f"⏱️  Total Time      : {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
    print(f"📊 Total Found     : {total_found} articles")
    print(f"✅ Total New       : {total_new} articles")
    print(f"⚡ Avg per URL     : {total_duration/len(results):.1f}s")
    print("═" * 60)
    print("🎯 CHUNGTA CRAWLING COMPLETED!")
    print("═" * 60)

if __name__ == "__main__":
    main_chungta()