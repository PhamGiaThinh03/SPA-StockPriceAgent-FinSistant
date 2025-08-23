from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, timedelta
from dateutil import parser
import time
import re
import warnings
import logging
from urllib.parse import urljoin, urlparse  # ✅ NEW

# 🔇 Tắt hoàn toàn các warning và log không cần thiết
warnings.filterwarnings("ignore")
logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.getLogger('selenium').setLevel(logging.ERROR)

# Import centralized database system
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database import SupabaseManager, DatabaseConfig, format_datetime_for_db

# Constants from old config
FIREANT_BASE_URL = "https://fireant.vn"
FIREANT_STOCK_URL = "https://fireant.vn/ma-chung-khoan"
FIREANT_ARTICLE_URL = "https://fireant.vn/bai-viet"
STOCK_CODES = ["FPT", "GAS", "IMP", "VCB"]

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

def get_stock_url(stock_code):
    """Generate stock URL"""
    return f"{FIREANT_STOCK_URL}/{stock_code}"

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

# Configuration constants
MAX_SCROLLS = 5  # Số lần scroll 

def parse_fuzzy_datetime(raw_text, current_year):
    if not raw_text:
        return None
        
    raw_text = raw_text.strip()
    original_text = raw_text
    raw_text = raw_text.lower()
    
    try:
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

        # Xử lý "20 phút", "22 phút", "30 phút" trước
        match = re.match(r"(\d+)\s*phút", raw_text)
        if match:
            minutes_ago = int(match.group(1))
            return datetime.now() - timedelta(minutes=minutes_ago)

        elif "khoảng" in raw_text or "trước" in raw_text:
            return None 

        # Danh sách các format ngày có thể
        date_formats = [
            "%Y-%m-%d",           # 2025-08-02
            "%d/%m/%Y",           # 02/08/2025  
            "%d-%m-%Y",           # 02-08-2025
            "%d/%m %H:%M",        # 02/08 14:30
            "%d-%m-%Y %H:%M",     # 02-08-2025 14:30
            "%Y-%m-%d %H:%M:%S",  # 2025-08-02 14:30:00
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
                
        # Nếu không match format nào thì return None
        return None

    except Exception as e:
        print(f"⚠️ Lỗi parse fuzzy time: '{original_text}' ({e})")
        return None

# def format_datetime_obj(dt):
#     return dt.strftime("%d-%m-%Y - %I:%M %p")

# def format_datetime_obj(dt):
#     day = dt.day
#     month = dt.month
#     year = dt.year
#     return f"{day}/{month}/{year}"

def format_datetime_obj(dt):
    return format_datetime_for_db(dt)

def fireant_date_parser(raw_text, current_year=2025):
    """Date parser cho FireAnt"""
    return parse_fuzzy_datetime(raw_text, current_year)


def setup_driver():
    options = Options()
    options.add_argument("--headless")  
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-logging")
    options.add_argument("--log-level=3")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_experimental_option('useAutomationExtension', False)
    return webdriver.Chrome(options=options)

# ============================================
# 🔗 NEW: Lấy link gốc trong #post_content
# ============================================
def extract_source_link_from_post(soup):
    """Tìm link gốc trong phần #post_content của bài viết FireAnt."""
    content_div = soup.find("div", id="post_content")
    if not content_div:
        return None

    anchors = content_div.select("a[href]")
    if not anchors:
        return None

    def normalize_href(href: str) -> str:
        href = (href or "").strip()
        if not href:
            return ""
        return urljoin(FIREANT_BASE_URL, href) if href.startswith("/") else href

    def is_external(href: str) -> bool:
        try:
            u = urlparse(href)
            return bool(u.netloc) and ("fireant.vn" not in u.netloc.lower())
        except Exception:
            return False

    KEYWORDS = ("Link gốc", "nguồn", "source", "xem thêm", "đọc thêm",)

    # Ưu tiên các anchor có text phù hợp, duyệt từ dưới lên (cuối bài trước)
    for a in reversed(anchors):
        text = (a.get_text(strip=True) or "").lower()
        href = normalize_href(a.get("href", ""))
        if any(k in text for k in KEYWORDS) and is_external(href):
            return href

    # Fallback: lấy external link cuối cùng trong phần nội dung
    for a in reversed(anchors):
        href = normalize_href(a.get("href", ""))
        if is_external(href):
            return href

    return None

def scroll_and_collect_links(driver, stock_code="FPT", scroll_step=500):
    url = get_stock_url(stock_code)
    driver.get(url)
    time.sleep(5)

    # Thu thập links theo thứ tự xuất hiện từ trên xuống
    links = []
    seen_links = set()  # Để track các link đã thấy
    scroll_position = 0

    # Đầu tiên thu thập links ở top của trang
    initial_articles = driver.find_elements(By.CSS_SELECTOR, "div.flex.flex-row.h-full.border-b-1 a[href^='/bai-viet/']")
    for article in initial_articles:
        try:
            href = article.get_attribute("href")
            if href and href.startswith("https://fireant.vn/bai-viet/"):
                clean_href = href.split("?")[0]
                if clean_href not in seen_links:
                    links.append(clean_href)
                    seen_links.add(clean_href)
        except:
            continue

    for i in range(MAX_SCROLLS):
        print(f"🔽 Scroll {i+1}/{MAX_SCROLLS}")
        scroll_position += scroll_step
        driver.execute_script(f"window.scrollTo(0, {scroll_position});")
        time.sleep(4)

        # Chỉ thu thập các link MỚI xuất hiện sau khi scroll
        current_articles = driver.find_elements(By.CSS_SELECTOR, "div.flex.flex-row.h-full.border-b-1 a[href^='/bai-viet/']")
        new_links_found = 0
        
        for article in current_articles:
            try:
                href = article.get_attribute("href")
                if href and href.startswith("https://fireant.vn/bai-viet/"):
                    clean_href = href.split("?")[0]
                    if clean_href not in seen_links:
                        links.append(clean_href)
                        seen_links.add(clean_href)
                        new_links_found += 1
            except:
                continue
        
        if new_links_found > 0:
            print(f"📰 Tìm thấy {new_links_found} bài mới sau scroll {i+1}")

        # Kiểm tra xem đã scroll hết chưa
        if scroll_position >= driver.execute_script("return document.body.scrollHeight"):
            print("🔚 Đã scroll hết trang, dừng")
            break

    print(f"✅ Found {len(links)} news in order from top to bottom.")
    return links

def extract_article(driver, url):
    try:
        driver.get(url)
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, "html.parser")

        title_tag = soup.select_one("div.mt-3.mb-5.text-3xl.font-semibold.leading-10")
        title = title_tag.get_text(strip=True) if title_tag else ""

        fuzzy_time = ""
        dt = None

        time_tag = soup.select_one("time[datetime]")
        if time_tag:
            fuzzy_time = time_tag.get_text(strip=True)
            try:
                raw_iso = time_tag.get("datetime") or time_tag.get("title")
                if raw_iso:
                    dt = parser.parse(raw_iso)
            except Exception as e:
                print(f"⚠️ Lỗi parse ISO datetime: {e}")

        if not dt:
            fuzzy_tags = soup.select("span.text-gray-500")
            if fuzzy_tags:
                for tag in fuzzy_tags:
                    parts = tag.get_text(strip=True).split("|")
                    if len(parts) >= 1:
                        fuzzy_time = parts[-1].strip()  # Lấy phần cuối (thời gian)

        content_div = soup.find("div", id="post_content")
        content = ""
        if content_div:
            paragraphs = content_div.find_all("p")
            content = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

        # 🔗 NEW: lấy link gốc (nếu có)
        source_link = extract_source_link_from_post(soup)

        try:
            ai_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Tóm tắt tin tức bằng AI')]"))
            )
            ai_button.click()
            time.sleep(10)
            soup = BeautifulSoup(driver.page_source, "html.parser")
            ai_summary_tag = soup.select_one("div.italic:not(.font-bold)")
            ai_summary = ai_summary_tag.get_text(strip=True) if ai_summary_tag else ""
        except Exception as e:
            print(f"⚠️ AI summary lỗi: {e}")
            ai_summary = ""

        return {
            "title": title,
            "content": content,
            "link": url,
            "ai_summary": ai_summary,
            "fuzzy_time": fuzzy_time,
            "source_link": source_link,  # ✅ NEW
        }
    except Exception as e:
        print(f"❌ Lỗi khi crawl bài viết: {url} ({e})")
        return {}

def insert_to_supabase(db_manager, table_name, data):
    """Wrapper function để tương thích với code cũ - sử dụng hàm chung"""
    # Tạo date parser function cho FireAnt
    def fireant_date_parser_wrapper(date_str):
        dt = parse_fuzzy_datetime(date_str, 2025)
        return format_datetime_for_db(dt) if dt else None
    
    return insert_article_to_database(db_manager, table_name, data, fireant_date_parser_wrapper)

def crawl_fireant(stock_code="FPT", table_name="FPT_News", db_manager=None):
    """Crawl FireAnt với logic tối ưu - chỉ check duplicate từ DB"""
    start_time = time.time()
    
    # Tạo db_manager nếu không được truyền vào
    if db_manager is None:
        db_manager = get_database_manager()
    
    print("\n===============================================================================")
    print(f"🔍 Đang kiểm tra database cho stock: {stock_code}")
    existing_links = get_recent_links_from_db(db_manager, table_name, 100)
    print(f"📊 Tìm thấy {len(existing_links)} bài viết trong DB (100 bài gần nhất)")

    driver = setup_driver()
    article_links = scroll_and_collect_links(driver, stock_code=stock_code)
    
    # Chỉ lọc bỏ những link đã có trong DB để tránh crawl trùng
    links_to_crawl = [link for link in article_links if link not in existing_links]
    
    if len(links_to_crawl) > 0:
        print(f"🎯 Crawl {len(links_to_crawl)} bài viết mới (bỏ qua {len(article_links) - len(links_to_crawl)} bài đã có)")
    else:
        print(f"📰 No new news - tất cả {len(article_links)} bài đều đã có trong DB")

    current_year = 2025
    new_articles = 0
    crawled_count = 0
    duplicate_count = 0
    
    for idx, link in enumerate(links_to_crawl):
        try:
            print(f"� [{idx+1}/{len(links_to_crawl)}] {link}")
            raw_data = extract_article(driver, link)

            dt = parse_fuzzy_datetime(raw_data.get("fuzzy_time", ""), current_year)
            raw_data["date"] = format_datetime_obj(dt) if dt else ""

            success = insert_to_supabase(db_manager, table_name, raw_data)
            if success:
                new_articles += 1
                print(f"✅ Đã lưu bài viết: {raw_data.get('title', '')[:50]}...")
            else:
                duplicate_count += 1
                # Chỉ hiển thị 3 duplicate đầu tiên để tránh spam
                if duplicate_count <= 3:
                    print(f"⚠️  Duplicate title - skipped: {raw_data.get('title', '')[:50]}...")
                elif duplicate_count == 4:
                    print(f"⚠️  ... và {len(links_to_crawl) - idx - 1} duplicates khác (không hiển thị)")
            
            crawled_count += 1
            time.sleep(1)  # Delay between requests
            
        except Exception as e:
            print(f"❌ Lỗi lấy bài {link}: {e}")
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

def scroll_and_collect_general_articles(driver):
    """DEPRECATED - Function removed as general news crawling is no longer needed"""
    print("⚠️ General news crawling has been disabled")
    return []

def crawl_fireant_general(table_name="General_News", db_manager=None):
    """DEPRECATED - General news crawling disabled"""
    print("⚠️ General news crawling has been disabled - only stock-specific news are processed")
    return {
        'type': 'General',
        'duration': 0,
        'total_found': 0,
        'crawled_count': 0,
        'new_articles': 0,
        'stopped_early': False
    }

def main_fireant():
    """Main function với dashboard timing và thống kê"""
    start_time = time.time()
    start_time_str = datetime.now().strftime("%H:%M:%S")
    
    print("\n" + "═" * 60)
    print("🚀 FIREANT CRAWLER DASHBOARD".center(60))
    print(f"⏰ Started: {start_time_str}".center(60))
    print("═" * 60)

    db_manager = get_database_manager()
    results = []
    
    # Crawl cho từng stock code
    for i, code in enumerate(STOCK_CODES, 1):
        print(f"\n🚀 Processing Stock [{i}/{len(STOCK_CODES)}]: {code}")
        table_name = get_table_name(stock_code=code)
        print(f"📋 Save to: {table_name}")
        
        result = crawl_fireant(stock_code=code, table_name=table_name, db_manager=db_manager)
        results.append(result)
        
        # Delay between stocks
        if i < len(STOCK_CODES):
            time.sleep(3)
    
    print(f"\n� General News crawling has been disabled - only processing 4 stock codes: {STOCK_CODES}")

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
    print("│ Type                     │ Time   │ Status       │ Saved Articles    │")
    print("├──────────────────────────┼────────┼──────────────┼───────────────────┤")
    
    # Table rows
    for result in results:
        type_name = result.get('stock_code', result.get('type', 'Unknown')).ljust(24)[:24]
        duration = result['duration']
        new_count = result['new_articles']
        stopped = result['stopped_early']
        
        # Status đơn giản
        status = "No new news" if new_count == 0 else "New news"
        # Saved Articles = số bài thực sự được lưu
        results_text = f"{new_count} saved"
        
        print(f"│ {type_name} │ {duration:>6.1f}s │ {status:<12} │ {results_text:<17} │")
    
    # Table footer
    print("└──────────────────────────┴────────┴──────────────┴───────────────────┘")
    
    # Summary
    print("\n" + "═" * 60)
    print("📊 SUMMARY FIREANT CRAWLING".center(60))
    print("─" * 60)
    print(f"⏱️  Total Time      : {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
    print(f"📊 Total Found     : {total_found} articles")
    print(f"🎯 Total Crawled   : {total_crawled} articles")
    print(f"✅ Total New       : {total_new} articles")
    print("═" * 60)
    print("🎯 FIREANT CRAWLING COMPLETED!")
    print("═" * 60)

if __name__ == "__main__":
    main_fireant()

