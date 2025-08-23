# -*- coding: utf-8 -*-
"""
⛽ PETROTIMES.VN CRAWLER - SPA-VIP PROFESSIONAL EDITION
=======================================================
Crawl chuyên nghiệp từ petrotimes.vn với:
- Centralized database integration
- Professional error handling & logging  
- Deduplication logic
- Multi-source crawling (PV GAS focus)
- Standard SPA-VIP architecture
- Specialized for GAS_News table
"""

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
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

# ============================================
# 🔧 CONSTANTS & CONFIGURATION
# ============================================
PETROTIMES_BASE_URL = "https://petrovietnam.petrotimes.vn"
PETROTIMES_PVGAS_URL = "https://petrovietnam.petrotimes.vn/tag/pv-gas-5931.tag"
PETROTIMES_GENERAL_URL = "https://petrovietnam.petrotimes.vn/dau-khi"

WAIT_SEC = 5  # Timeout cho WebDriverWait

# ============================================
# 🔧 HELPER FUNCTIONS
# ============================================
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

def get_database_manager():
    """Get database manager instance"""
    return SupabaseManager()

def get_table_name(stock_code=None, is_general=False):
    """Get table name using new config"""
    config = DatabaseConfig()
    return config.get_table_name(stock_code=stock_code, is_general=is_general)

def clean_text(s: str) -> str:
    """Dọn dẹp text: loại bỏ whitespace thừa"""
    if not s:
        return ""
    s = re.sub(r"\s+", " ", s)
    return s.strip()

# ============================================
# 🕐 DATETIME PARSING FUNCTIONS
# ============================================
def parse_petrotimes_datetime(raw_text):
    """
    Parse datetime từ petrotimes.vn
    Format thường gặp: 
    - "19:37 | 15/08/2025"
    - "15:30 | 16/08/2025"
    - "hôm nay 10:30"
    - "hôm qua 15:45"
    """
    if not raw_text:
        return None
        
    raw_text = raw_text.strip()
    original_text = raw_text
    raw_text = raw_text.lower()
    
    try:
        # Xử lý "hôm nay" và "hôm qua"
        if "hôm nay" in raw_text:
            time_match = re.search(r"(\d{1,2}):(\d{2})", raw_text)
            if time_match:
                hour, minute = map(int, time_match.groups())
                today = datetime.now()
                return today.replace(hour=hour, minute=minute, second=0, microsecond=0)

        if "hôm qua" in raw_text:
            time_match = re.search(r"(\d{1,2}):(\d{2})", raw_text)
            if time_match:
                hour, minute = map(int, time_match.groups())
                yesterday = datetime.now() - timedelta(days=1)
                return yesterday.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # Xử lý format Petrotimes: "19:37 | 15/08/2025"
        petrotimes_pattern = re.search(r"(\d{1,2}):(\d{2})\s*\|\s*(\d{1,2})/(\d{1,2})/(\d{4})", original_text)
        if petrotimes_pattern:
            hour, minute, day, month, year = map(int, petrotimes_pattern.groups())
            return datetime(year, month, day, hour, minute)
            
        # Pattern 2: "15/08/2025 10:30"
        date_time_pattern = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{2})", original_text)
        if date_time_pattern:
            day, month, year, hour, minute = map(int, date_time_pattern.groups())
            return datetime(year, month, day, hour, minute)
            
        # Pattern 3: Chỉ có ngày "15/08/2025"
        date_pattern = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", original_text)
        if date_pattern:
            day, month, year = map(int, date_pattern.groups())
            return datetime(year, month, day, 0, 0)
        
        # Fallback: thử parse với dateutil
        try:
            return parser.parse(original_text, fuzzy=True)
        except:
            pass
            
        return None

    except Exception as e:
        print(f"⚠️ Lỗi parse datetime Petrotimes: '{original_text}' ({e})")
        return None

def format_datetime_obj(dt):
    """Format datetime object cho database"""
    return format_datetime_for_db(dt)

# ============================================
# 🔧 SELENIUM SETUP
# ============================================
def setup_driver():
    """Setup Chrome driver với các option tối ưu"""
    options = Options()
    options.add_argument("--headless")  # Chạy ẩn để tối ưu performance
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-logging")
    options.add_argument("--log-level=3")
    options.add_argument("--disable-notifications")
    options.add_argument("--start-maximized")
    options.add_argument("--window-size=1366,900")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(60)
    return driver

# ============================================
# 🔍 LINK COLLECTION FUNCTIONS
# ============================================
def collect_article_links_on_tag_page(driver):
    """
    Thu thập link bài viết trên trang tag Petrotimes
    """
    links = []
    
    # Các selector khả dĩ cho Petrotimes
    selectors = [
        "ul.list-news li h2 a",
        "ul.list-news li h3 a", 
        "ul li h3 a.bx-title",
        "ul li h2 a.bx-title",
        "a.bx-title[href]",
        ".list-news .bx-title",
        "h3 a[href]",
        "h2 a[href]"
    ]
    
    for css in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, css)
            for el in elements:
                href = el.get_attribute("href")
                if href and href.startswith("http") and "petrotimes.vn" in href:
                    if href not in links:
                        links.append(href)
        except Exception:
            continue
    
    # Fallback: tìm tất cả links có chứa petrotimes
    if not links:
        try:
            all_links = driver.find_elements(By.CSS_SELECTOR, "a[href]")
            for link in all_links:
                href = link.get_attribute("href")
                if href and "petrotimes.vn" in href and "/details/" in href:
                    if href not in links:
                        links.append(href)
        except Exception:
            pass
    
    return links

def collect_links_from_single_page(driver):
    """
    Thu thập links từ trang hiện tại (chỉ 1 trang)
    """
    current_links = collect_article_links_on_tag_page(driver)
    return current_links

# ============================================
# 📄 ARTICLE EXTRACTION FUNCTIONS  
# ============================================
def extract_article(driver, url):
    """
    Trích xuất thông tin chi tiết từ một bài viết Petrotimes
    """
    try:
        driver.get(url)
        
        # Đợi page load
        try:
            WebDriverWait(driver, WAIT_SEC).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "h1, .detail-title, .titleDetails")
                )
            )
        except TimeoutException:
            time.sleep(3)
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # 📰 Title
        title = ""
        title_selectors = [
            "h1.detail-title",
            "h1.titleDetails", 
            "h1.__MB_MASTERCMS_EL.clearfix",
            "h1",
            ".detail-title",
            ".titleDetails"
        ]
        
        for selector in title_selectors:
            title_element = soup.select_one(selector)
            if title_element:
                title = clean_text(title_element.get_text())
                break
        
        # 🕐 Time - Format Petrotimes: "19:37 | 15/08/2025"
        time_text = ""
        time_selectors = [
            "div.published-dated.clearfix p",
            "div.published-dated p",
            "div.published-dated",
            "div.date",
            "p.published-dated",
            "p.published-date", 
            "div.colLeftDetails .date",
            ".date-time",
            ".publish-time"
        ]
        
        for selector in time_selectors:
            time_element = soup.select_one(selector)
            if time_element:
                time_text = clean_text(time_element.get_text())
                break
        
        # 📝 Content
        content_parts = []
        
        # Thử lấy content từ các container của Petrotimes
        content_selectors = [
            "div.colLeftDetails div.boxTextDetails",
            "div.colLeftDetails",
            "div.boxTextDetails.__MASTERCMS_CONTENT",
            "div#__MB_MASTERCMS_EL_3",
            "div#__MB_MASTERCMS_EL_2",
            "div.detail-content",
            ".article-content",
            ".content-detail"
        ]
        
        for selector in content_selectors:
            content_div = soup.select_one(selector)
            if content_div:
                paragraphs = content_div.find_all("p")
                for p in paragraphs:
                    txt = clean_text(p.get_text())
                    if txt and len(txt) > 20:  # Lọc bỏ đoạn ngắn
                        content_parts.append(txt)
                if content_parts:
                    break
        
        # Fallback: lấy tất cả <p> trong body
        if not content_parts:
            paragraphs = soup.find_all("p")
            for p in paragraphs:
                txt = clean_text(p.get_text())
                if txt and len(txt) > 20:
                    content_parts.append(txt)
        
        content = "\n\n".join(content_parts).strip()
        
        # 🔗 Source link extraction (nếu có)
        source_link = extract_source_link_from_article(soup)
        
        print(f"🕒 Found time: '{time_text}'")
        
        return {
            "title": title,
            "content": content,
            "link": url,
            "ai_summary": "",  # Có thể thêm AI summary sau
            "fuzzy_time": time_text,
            "source_link": source_link,
        }
        
    except Exception as e:
        print(f"❌ Lỗi khi crawl bài viết: {url} ({e})")
        return {}

def extract_source_link_from_article(soup):
    """Tìm link gốc trong bài viết Petrotimes (nếu có)"""
    try:
        # Tìm trong div content hoặc main content
        content_div = soup.select_one("div.colLeftDetails") or soup.select_one(".detail-content")
        if not content_div:
            return None

        anchors = content_div.select("a[href]")
        if not anchors:
            return None

        def normalize_href(href: str) -> str:
            href = (href or "").strip()
            if not href:
                return ""
            return urljoin(PETROTIMES_BASE_URL, href) if href.startswith("/") else href

        def is_external(href: str) -> bool:
            try:
                u = urlparse(href)
                return bool(u.netloc) and ("petrotimes.vn" not in u.netloc.lower())
            except Exception:
                return False

        KEYWORDS = ("nguồn", "source", "xem thêm", "đọc thêm", "chi tiết")

        # Ưu tiên các anchor có text phù hợp
        for a in reversed(anchors):
            text = (a.get_text(strip=True) or "").lower()
            href = normalize_href(a.get("href", ""))
            if any(k in text for k in KEYWORDS) and is_external(href):
                return href

        # Fallback: lấy external link cuối cùng
        for a in reversed(anchors):
            href = normalize_href(a.get("href", ""))
            if is_external(href):
                return href

        return None
    except Exception:
        return None

# ============================================
# 💾 DATABASE OPERATIONS
# ============================================
def insert_article_to_database(db_manager, table_name, article_data):
    """Insert article using centralized database system"""
    # Parse date if available
    if article_data.get("fuzzy_time"):
        try:
            parsed_date = parse_petrotimes_datetime(article_data["fuzzy_time"])
            if parsed_date:
                article_data["date"] = format_datetime_obj(parsed_date)
            else:
                article_data["date"] = datetime.now().strftime("%Y-%m-%d")
        except Exception:
            article_data["date"] = datetime.now().strftime("%Y-%m-%d")
    else:
        article_data["date"] = datetime.now().strftime("%Y-%m-%d")
    
    return db_manager.insert_article(table_name, article_data)

# ============================================
# 🎯 MAIN CRAWLING FUNCTIONS
# ============================================
def crawl_petrotimes_gas(table_name="GAS_News", db_manager=None):
    """
    Crawl petrotimes.vn cho GAS (PV GAS) - chuyên biệt cho bảng GAS_News
    """
    start_time = time.time()
    
    # Tạo db_manager nếu không được truyền vào
    if db_manager is None:
        db_manager = get_database_manager()
    
    print(f"\n===============================================================================")
    print(f"⛽ Petrotimes Crawler - Stock: GAS (PV GAS)")
    print(f"📋 Table: {table_name}")
    
    # Lấy existing links từ DB
    existing_links = get_recent_links_from_db(db_manager, table_name, 100)
    print(f"📊 Found {len(existing_links)} existing articles in DB (last 100)")
    
    source_url = PETROTIMES_PVGAS_URL
    print(f"🔍 Searching Petrotimes for: PV GAS")
    print(f"🌐 URL: {source_url}")
    
    driver = setup_driver()
    
    try:
        # Mở trang
        driver.get(source_url)
        
        # Đợi page load
        try:
            WebDriverWait(driver, WAIT_SEC).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.bx-title, ul.list-news li a"))
            )
        except TimeoutException:
            print("⚠️ Không tìm thấy danh sách bài viết")
            return {
                'stock_code': 'GAS',
                'duration': time.time() - start_time,
                'total_found': 0,
                'crawled_count': 0,
                'new_articles': 0,
                'stopped_early': False
            }
        
        # Thu thập links từ trang hiện tại
        article_links = collect_links_from_single_page(driver)
        print(f"✅ Found {len(article_links)} unique links for GAS")
        
        # Lọc bỏ những link đã có trong DB
        links_to_crawl = [link for link in article_links if link not in existing_links]
        
        if len(links_to_crawl) > 0:
            print(f"🎯 Crawling {len(links_to_crawl)} new articles (skipping {len(article_links) - len(links_to_crawl)} existing)")
        else:
            print(f"📰 No new news - all {len(article_links)} articles already in DB")
        
        new_articles = 0
        crawled_count = 0
        duplicate_count = 0
        
        # Crawl từng bài viết mới
        for idx, link in enumerate(links_to_crawl):
            try:
                print(f"📄 [{idx+1}/{len(links_to_crawl)}] {link}")
                raw_data = extract_article(driver, link)
                
                if not raw_data.get("title"):
                    print(f"⚠️ Bỏ qua bài không có title")
                    continue
                
                # Parse datetime
                if raw_data.get("fuzzy_time"):
                    dt = parse_petrotimes_datetime(raw_data["fuzzy_time"])
                    if dt:
                        print(f"🕒 Raw time: '{raw_data['fuzzy_time']}' → Parsed: {dt} → Formatted: '{format_datetime_obj(dt)}'")
                
                success = insert_article_to_database(db_manager, table_name, raw_data)
                if success:
                    new_articles += 1
                    print(f"✅ Saved: {raw_data.get('title', '')[:50]}...")
                else:
                    duplicate_count += 1
                    if duplicate_count <= 3:
                        print(f"⚠️ Duplicate - skipped: {raw_data.get('title', '')[:50]}...")
                    elif duplicate_count == 4:
                        print(f"⚠️ ... và {len(links_to_crawl) - idx - 1} duplicates khác (không hiển thị)")
                
                crawled_count += 1
                time.sleep(1)  # Delay between requests
                
            except Exception as e:
                print(f"❌ Lỗi crawl bài {link}: {e}")
                continue
        
    except Exception as e:
        print(f"❌ Lỗi crawl GAS: {e}")
    finally:
        driver.quit()
    
    # Tính toán kết quả
    end_time = time.time()
    duration = end_time - start_time
    
    return {
        'stock_code': 'GAS',
        'duration': duration,
        'total_found': len(article_links) if 'article_links' in locals() else 0,
        'crawled_count': crawled_count,
        'new_articles': new_articles,
        'stopped_early': False
    }

# ============================================
# 🚀 MAIN FUNCTION WITH DASHBOARD
# ============================================
def main_petrotimes():
    """Main function với dashboard timing và thống kê cho GAS"""
    start_time = time.time()
    start_time_str = datetime.now().strftime("%H:%M:%S")
    
    print("\n" + "═" * 60)
    print("⛽ PETROTIMES CRAWLER DASHBOARD".center(60))
    print(f"⏰ Started: {start_time_str}".center(60))
    print("═" * 60)

    db_manager = get_database_manager()
    
    # Crawl cho GAS_News
    print(f"\n🚀 Processing Stock: GAS (PV GAS)")
    table_name = get_table_name(stock_code="GAS")
    print(f"📋 Save to: {table_name}")
    
    result = crawl_petrotimes_gas(table_name=table_name, db_manager=db_manager)

    db_manager.close_connections()
    
    # Hiển thị dashboard kết quả
    end_time = time.time()
    total_duration = end_time - start_time
    
    print("\n" + "═" * 60)
    print("🎉 CRAWLING COMPLETED - RESULTS".center(60))
    print("═" * 60)
    
    # Table header
    print("┌──────────────────────────┬────────┬──────────────┬───────────────────┐")
    print("│ Type                     │ Time   │ Status       │ Saved Articles    │")
    print("├──────────────────────────┼────────┼──────────────┼───────────────────┤")
    
    # Table row
    type_name = result.get('stock_code', 'GAS').ljust(24)[:24]
    duration = result['duration']
    new_count = result['new_articles']
    
    # Status đơn giản
    status = "No new news" if new_count == 0 else "New news"
    results_text = f"{new_count} saved"
    
    print(f"│ {type_name} │ {duration:>6.1f}s │ {status:<12} │ {results_text:<17} │")
    
    # Table footer
    print("└──────────────────────────┴────────┴──────────────┴───────────────────┘")
    
    # Summary
    print("\n" + "═" * 60)
    print("📊 SUMMARY PETROTIMES CRAWLING".center(60))
    print("─" * 60)
    print(f"⏱️  Total Time      : {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
    print(f"📊 Total Found     : {result['total_found']} articles")
    print(f"🎯 Total Crawled   : {result['crawled_count']} articles")
    print(f"✅ Total New       : {result['new_articles']} articles")
    print("═" * 60)
    print("🎯 PETROTIMES CRAWLING COMPLETED!")
    print("═" * 60)

if __name__ == "__main__":
    main_petrotimes()
