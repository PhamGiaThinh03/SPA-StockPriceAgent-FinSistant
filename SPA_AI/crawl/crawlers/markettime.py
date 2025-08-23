"""
MarketTimes Crawler
Professional crawler for markettimes.vn following SPA_VIP standards
Author: Auto-generated
Date: August 17, 2025
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dateutil import parser
import time
import re
import warnings
import logging
from urllib.parse import urljoin, urlparse

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
MARKETTIMES_BASE_URL = "https://markettimes.vn"
MARKETTIMES_SEARCH_URL = "https://markettimes.vn/search"
STOCK_CODES = ["FPT", "GAS", "IMP", "VCB"]

# Configuration constants
HEADLESS = True  # Chuyển về True để tối ưu performance
SCROLL_PAUSE = 1.2
SCROLL_PATIENCE = 3
IMPLICIT_WAIT = 5
TIMEOUT = 10
MAX_SCROLLS = 5  # Số lần scroll tối đa

# Helper functions to replace old config functions
def get_recent_links_from_db(db_manager, table_name, limit=100):
    """Lấy 100 link bài viết gần nhất từ database để tối ưu crawling"""
    try:
        supabase_client = db_manager.get_supabase_client()
        # Thử dùng created_at trước, fallback sang id
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

def get_database_manager():
    """Get database manager instance"""
    return SupabaseManager()

def get_table_name(stock_code=None, is_general=False):
    """Get table name using new config"""
    config = DatabaseConfig()
    return config.get_table_name(stock_code=stock_code, is_general=is_general)

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

def parse_markettimes_datetime(raw_text, current_year=2025):
    """Parse datetime từ MarketTimes format"""
    if not raw_text:
        return None
        
    raw_text = raw_text.strip()
    original_text = raw_text
    raw_text = raw_text.lower()
    
    try:
        # Xử lý "hôm nay", "hôm qua"
        if "hôm nay" in raw_text:
            time_part = raw_text.replace("hôm nay", "").strip()
            dt = datetime.strptime(time_part, "%H:%M")
            today = datetime.now()
            return today.replace(hour=dt.hour, minute=dt.minute, second=0, microsecond=0)

        if "hôm qua" in raw_text:
            time_part = raw_text.replace("hôm qua", "").strip()
            dt = datetime.strptime(time_part, "%H:%M")
            yesterday = datetime.now() - timedelta(days=1)
            return yesterday.replace(hour=dt.hour, minute=dt.minute, second=0, microsecond=0)

        # Xử lý "X phút trước", "X giờ trước"
        match = re.match(r"(\d+)\s*phút", raw_text)
        if match:
            minutes_ago = int(match.group(1))
            return datetime.now() - timedelta(minutes=minutes_ago)

        match = re.match(r"(\d+)\s*giờ", raw_text)
        if match:
            hours_ago = int(match.group(1))
            return datetime.now() - timedelta(hours=hours_ago)

        # 🔥 NEW: Xử lý format cụ thể của MarketTimes: "17:22 17/08/2025"
        # Pattern: HH:MM DD/MM/YYYY
        match = re.match(r"(\d{1,2}):(\d{2})\s+(\d{1,2})/(\d{1,2})/(\d{4})", original_text)
        if match:
            hour, minute, day, month, year = match.groups()
            dt = datetime(int(year), int(month), int(day), int(hour), int(minute))
            return dt

        # Danh sách các format ngày khác có thể từ MarketTimes
        date_formats = [
            "%H:%M %d/%m/%Y",     # 17:22 17/08/2025 (chính xác format từ HTML)
            "%d/%m/%Y %H:%M",     # 17/08/2025 17:22
            "%d-%m-%Y %H:%M",     # 17-08-2025 17:22
            "%Y-%m-%d %H:%M:%S",  # 2025-08-17 17:22:00
            "%d/%m/%Y",           # 17/08/2025
            "%d-%m-%Y",           # 17-08-2025
            "%Y-%m-%d",           # 2025-08-17
        ]
        
        for fmt in date_formats:
            try:
                dt = datetime.strptime(original_text, fmt)
                # Nếu không có năm thì dùng current_year
                if "%Y" not in fmt:
                    dt = dt.replace(year=current_year)
                return dt
            except:
                continue
                
        return None

    except Exception as e:
        print(f"⚠️ Lỗi parse datetime MarketTimes: '{original_text}' ({e})")
        return None

def format_datetime_obj(dt):
    """Format datetime object theo chuẩn database"""
    return format_datetime_for_db(dt)

def markettimes_date_parser(raw_text, current_year=2025):
    """Date parser cho MarketTimes"""
    return parse_markettimes_datetime(raw_text, current_year)

def clean_text(s: str) -> str:
    """Clean and normalize text"""
    if not s:
        return ""
    s = s.replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def setup_driver():
    """Setup Chrome driver với cấu hình tối ưu cho production"""
    options = Options()
    if HEADLESS:
        options.add_argument("--headless")  
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-logging")
    options.add_argument("--log-level=3")
    options.add_argument("--start-maximized")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(IMPLICIT_WAIT)
    return driver

def scroll_to_bottom(driver, pause=SCROLL_PAUSE, patience=SCROLL_PATIENCE):
    """Scroll to bottom với patience control"""
    still = 0
    last_h = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)
        new_h = driver.execute_script("return document.body.scrollHeight")
        still = still + 1 if new_h <= last_h else 0
        last_h = new_h
        if still >= patience:
            break

def get_search_url(keyword: str) -> str:
    """Generate search URL for keyword"""
    return f"{MARKETTIMES_SEARCH_URL}?q={keyword}"

def collect_article_links(driver, keyword: str):
    """Thu thập tất cả links từ search page với scroll"""
    url = get_search_url(keyword)
    print(f"🔍 Searching MarketTimes for: {keyword}")
    driver.get(url)
    
    try:
        WebDriverWait(driver, TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.c-head-list, ul.loadAjax"))
        )
    except TimeoutException:
        print(f"⚠️ Không thấy vùng kết quả cho: {keyword}")
        return []
    
    # Scroll để load thêm nội dung
    scroll_to_bottom(driver)
    
    # Thu thập links
    anchors = driver.find_elements(By.CSS_SELECTOR,
        ".c-head-list a, ul.loadAjax li.loadArticle h4.b-grid__title a")
    
    links, seen = [], set()
    for a in anchors:
        href = (a.get_attribute("href") or "").strip()
        if href and "markettimes.vn" in href and href not in seen:
            seen.add(href)
            links.append(href)
    
    print(f"✅ Found {len(links)} unique links for {keyword}")
    return links

def extract_article(driver, url: str) -> dict:
    """Extract article data từ MarketTimes page"""
    try:
        driver.get(url)
        WebDriverWait(driver, TIMEOUT).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "h1, div.c-news-detail, div.content-main-normal.descriptionx")
            )
        )
    except TimeoutException:
        print(f"⚠️ Timeout loading article: {url}")

    try:
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Title - thử các selector khác nhau
        title = ""
        title_selectors = ["h1.c-detail-head__title", "h1", ".c-detail-head__title"]
        for sel in title_selectors:
            try:
                title_element = soup.select_one(sel)
                if title_element:
                    title = clean_text(title_element.get_text())
                    if title.strip(): 
                        break
            except Exception:
                continue

        # Description (lead) - merge vào content
        description = ""
        desc_selectors = ["h2.desc", "h2", ".desc"]
        for sel in desc_selectors:
            try:
                desc_element = soup.select_one(sel)
                if desc_element:
                    description = clean_text(desc_element.get_text())
                    if description.strip(): 
                        break
            except Exception:
                continue

        # Publish time - cập nhật selector dựa trên HTML structure thực tế
        publish_time = ""
        time_selectors = [
            "span.c-detail-head__time",           # Format: "17:22 17/08/2025"
            ".c-detail-head__row .c-detail-head__time", 
            ".c-detail-head__time"
        ]
        for sel in time_selectors:
            try:
                time_element = soup.select_one(sel)
                if time_element:
                    publish_time = clean_text(time_element.get_text())
                    print(f"🕒 Found time: '{publish_time}'")  # Debug log
                    if publish_time.strip(): 
                        break
            except Exception:
                continue

        # Author
        author = ""
        author_selectors = ["span.c-detail-head__author", ".c-detail-head__author"]
        for sel in author_selectors:
            try:
                author_element = soup.select_one(sel)
                if author_element:
                    author = clean_text(author_element.get_text())
                    if author.strip(): 
                        break
            except Exception:
                continue

        # Content paragraphs
        content = ""
        content_selectors = ["div.c-news-detail", "div.b-maincontent", "div.content-main-normal.descriptionx"]
        for sel in content_selectors:
            try:
                container = soup.select_one(sel)
                if container:
                    paragraphs = container.select("p")
                    content_parts = []
                    
                    # Gộp description vào đầu content nếu có
                    if description:
                        content_parts.append(description)
                    
                    for p in paragraphs:
                        txt = clean_text(p.get_text())
                        if txt:
                            content_parts.append(txt)
                    
                    content = "\n\n".join(content_parts)
                    break
            except Exception:
                continue

        # Fallback cho content nếu không extract được
        if not content:
            try:
                body_text = soup.select_one("body").get_text() if soup.select_one("body") else ""
                content = clean_text((description + " " + body_text) if description else body_text)
            except Exception:
                content = description  # fallback cuối

        # Parse datetime với improved logic
        current_year = datetime.now().year
        dt = parse_markettimes_datetime(publish_time, current_year)
        
        # Fallback: nếu không parse được thì dùng ngày hiện tại
        if not dt:
            print(f"⚠️ Cannot parse time '{publish_time}', using current date")
            dt = datetime.now()
            
        formatted_date = format_datetime_obj(dt) if dt else ""

        # Debug log
        print(f"🕒 Raw time: '{publish_time}' → Parsed: {dt} → Formatted: '{formatted_date}'")

        return {
            "title": title,
            "content": content,
            "link": url,
            "date": formatted_date,
            "publish_time": publish_time,  # Raw time for debugging
            "author": author,
        }

    except Exception as e:
        print(f"❌ Lỗi extract article {url}: {e}")
        return {
            "title": "",
            "content": "",
            "link": url,
            "date": "",
            "publish_time": "",
            "author": "",
        }

def insert_to_supabase(db_manager, table_name, data):
    """Wrapper function để tương thích với code cũ - sử dụng hàm chung"""
    # Tạo date parser function cho MarketTimes
    def markettimes_date_parser_wrapper(date_str):
        dt = parse_markettimes_datetime(date_str, 2025)
        return format_datetime_for_db(dt) if dt else None
    
    return insert_article_to_database(db_manager, table_name, data, markettimes_date_parser_wrapper)

def crawl_markettimes(stock_code="FPT", table_name="FPT_News", db_manager=None):
    """
    Crawl MarketTimes cho specific stock code với logic tối ưu
    
    Args:
        stock_code: Mã cổ phiếu cần crawl
        table_name: Tên bảng database
        db_manager: Database manager instance
    """
    start_time = time.time()
    
    # Tạo db_manager nếu không được truyền vào
    if db_manager is None:
        db_manager = get_database_manager()
    
    print(f"\n===============================================================================")
    print(f"� MarketTimes Crawler - Stock: {stock_code}")
    print(f"📋 Table: {table_name}")
    
    # Lấy existing links từ database
    existing_links = get_recent_links_from_db(db_manager, table_name, 100)
    print(f"� Found {len(existing_links)} existing articles in DB (last 100)")

    driver = setup_driver()
    article_links = collect_article_links(driver, stock_code)
    
    # Lọc bỏ những link đã có trong DB
    links_to_crawl = [link for link in article_links if link not in existing_links]
    
    if len(links_to_crawl) > 0:
        print(f"🎯 Crawling {len(links_to_crawl)} new articles (skipping {len(article_links) - len(links_to_crawl)} existing)")
    else:
        print(f"📰 No new articles - all {len(article_links)} already in DB")

    new_articles = 0
    crawled_count = 0
    duplicate_count = 0
    
    for idx, link in enumerate(links_to_crawl):
        try:
            print(f"📄 [{idx+1}/{len(links_to_crawl)}] {link}")
            article_data = extract_article(driver, link)
            
            success = insert_to_supabase(db_manager, table_name, article_data)
            if success:
                new_articles += 1
                print(f"✅ Saved: {article_data.get('title', '')[:50]}...")
            else:
                duplicate_count += 1
                if duplicate_count <= 3:
                    print(f"⚠️  Duplicate - skipped: {article_data.get('title', '')[:50]}...")
                elif duplicate_count == 4:
                    print(f"⚠️  ... và {len(links_to_crawl) - idx - 1} duplicates khác")
            
            crawled_count += 1
            time.sleep(1)  # Delay between requests
            
        except Exception as e:
            print(f"❌ Error crawling {link}: {e}")
            continue
    
    driver.quit()
    
    # Tính toán kết quả
    end_time = time.time()
    duration = end_time - start_time
    
    return {
        'stock_code': stock_code,
        'duration': duration,
        'total_found': len(article_links),
        'crawled_count': crawled_count,
        'new_articles': new_articles,
        'stopped_early': False
    }

def crawl_markettimes_general(table_name="General_News", db_manager=None):
    """
    Crawl MarketTimes cho general news
    
    Args:
        table_name: Tên bảng database
        db_manager: Database manager instance
    """
    start_time = time.time()
    
    # Tạo db_manager nếu không được truyền vào
    if db_manager is None:
        db_manager = get_database_manager()
    
    print(f"\n🔍 MarketTimes General Crawler")
    print(f"📋 Table: {table_name}")
    
    # Lấy existing links từ database
    existing_links = get_recent_links_from_db(db_manager, table_name, 100)
    print(f"📊 Found {len(existing_links)} existing articles in DB")

    driver = setup_driver()
    
    # Crawl các keyword chung
    general_keywords = ["chứng khoán"]
    all_links = []
    
    for keyword in general_keywords:
        print(f"🔎 Searching for: {keyword}")
        keyword_links = collect_article_links(driver, keyword)
        for link in keyword_links:
            if link not in all_links:
                all_links.append(link)
    
    # Lọc bỏ những link đã có trong DB
    links_to_crawl = [link for link in all_links if link not in existing_links]
    
    if len(links_to_crawl) > 0:
        print(f"🎯 Crawling {len(links_to_crawl)} new articles")
    else:
        print(f"📰 No new articles found")

    new_articles = 0
    crawled_count = 0
    
    for idx, link in enumerate(links_to_crawl):
        try:
            print(f"📄 [{idx+1}/{len(links_to_crawl)}] {link}")
            article_data = extract_article(driver, link)
            
            success = insert_to_supabase(db_manager, table_name, article_data)
            if success:
                new_articles += 1
                print(f"✅ Saved: {article_data.get('title', '')[:50]}...")
            else:
                print(f"⚠️  Duplicate - skipped")
            
            crawled_count += 1
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ Error crawling {link}: {e}")
            continue
    
    driver.quit()
    
    end_time = time.time()
    duration = end_time - start_time
    
    return {
        'type': 'General',
        'duration': duration,
        'total_found': len(all_links),
        'crawled_count': crawled_count,
        'new_articles': new_articles,
        'stopped_early': False
    }

def main_markettimes():
    """Main function với dashboard timing và thống kê theo chuẩn SPA_VIP"""
    start_time = time.time()
    start_time_str = datetime.now().strftime("%H:%M:%S")
    
    print("\n" + "═" * 60)
    print("🚀 MARKETTIMES CRAWLER DASHBOARD".center(60))
    print(f"⏰ Started: {start_time_str}".center(60))
    print("═" * 60)

    db_manager = get_database_manager()
    results = []
    
    # Crawl cho từng stock code
    for i, code in enumerate(STOCK_CODES, 1):
        print(f"\n🚀 Processing Stock [{i}/{len(STOCK_CODES)}]: {code}")
        table_name = get_table_name(stock_code=code)
        print(f"📋 Save to: {table_name}")
        
        result = crawl_markettimes(stock_code=code, table_name=table_name, db_manager=db_manager)
        results.append(result)
        
        # Delay between stocks
        if i < len(STOCK_CODES):
            time.sleep(3)
    
    # Crawl general news
    print(f"\n🚀 Processing General News")
    general_table = get_table_name(is_general=True)
    print(f"📋 Save to: {general_table}")
    
    general_result = crawl_markettimes_general(table_name=general_table, db_manager=db_manager)
    results.append(general_result)

    db_manager.close_connections()
    
    # Display dashboard results
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
    print("│ Type                     │ Time   │ Status       │ Saved Articles    │")
    print("├──────────────────────────┼────────┼──────────────┼───────────────────┤")
    
    # Table rows
    for result in results:
        type_name = result.get('stock_code', result.get('type', 'Unknown')).ljust(24)[:24]
        duration = result['duration']
        new_count = result['new_articles']
        
        status = "No new news" if new_count == 0 else "New news"
        results_text = f"{new_count} saved"
        
        print(f"│ {type_name} │ {duration:>6.1f}s │ {status:<12} │ {results_text:<17} │")
    
    # Table footer
    print("└──────────────────────────┴────────┴──────────────┴───────────────────┘")
    
    # Summary
    print("\n" + "═" * 60)
    print("📊 SUMMARY MARKETTIMES CRAWLING".center(60))
    print("─" * 60)
    print(f"⏱️  Total Time      : {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
    print(f"📊 Total Found     : {total_found} articles")
    print(f"🎯 Total Crawled   : {total_crawled} articles")
    print(f"✅ Total New       : {total_new} articles")
    print("═" * 60)
    print("🎯 MARKETTIMES CRAWLING COMPLETED!")
    print("═" * 60)

if __name__ == "__main__":
    main_markettimes()
