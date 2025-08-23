# -*- coding: utf-8 -*-
"""
🏭 IMEXPHARM (IMP) CRAWLER - SPA-VIP PROFESSIONAL EDITION
==========================================================
Crawl chuyên nghiệp từ imexpharm.com với:
- Centralized database integration (chỉ dành cho IMP_News table)
- Professional error handling & logging  
- Deduplication logic
- Standard SPA-VIP architecture
- Enhanced datetime parsing for IMP format
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
IMP_BASE_URL = "https://www.imexpharm.com"
IMP_NEWS_URL = "https://www.imexpharm.com/tin-tuc/ban-tin-imexpharm"

# ============================================
# 🔧 HELPER FUNCTIONS
# ============================================
def get_recent_links_from_db(db_manager, table_name="IMP_News", limit=100):
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

def get_table_name():
    """Get IMP table name"""
    config = DatabaseConfig()
    return config.get_table_name(stock_code="IMP")

def clean_text(s: str) -> str:
    """Dọn dẹp text: loại bỏ whitespace thừa và ký tự đặc biệt"""
    if not s:
        return ""
    s = s.replace("\xa0", " ")  # Non-breaking space
    s = re.sub(r"\s+", " ", s)
    return s.strip()

# ============================================
# 🕐 DATETIME PARSING FUNCTIONS
# ============================================
def parse_imp_datetime(raw_text):
    """
    Parse datetime từ imexpharm.com
    Format thường gặp: 
    - "14/08/2025"
    - "14/08/2025 10:30"
    - "hôm nay"
    - "hôm qua"
    """
    if not raw_text:
        return None
        
    raw_text = raw_text.strip()
    original_text = raw_text
    raw_text = raw_text.lower()
    
    try:
        # Xử lý "hôm nay" và "hôm qua"
        if "hôm nay" in raw_text:
            return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        if "hôm qua" in raw_text:
            return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)

        # Xử lý các format chuẩn
        # Pattern 1: "14/08/2025 10:30"
        date_time_pattern = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})\s*(\d{1,2}):(\d{2})", original_text)
        if date_time_pattern:
            day, month, year, hour, minute = map(int, date_time_pattern.groups())
            return datetime(year, month, day, hour, minute)
            
        # Pattern 2: Chỉ có ngày "14/08/2025"
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
        print(f"⚠️ Lỗi parse datetime IMP: '{original_text}' ({e})")
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
    options.add_argument("--window-size=1400,1000")
    options.page_load_strategy = "eager"
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(60)
    return driver

# ============================================
# 🔍 LINK COLLECTION FUNCTIONS
# ============================================
def collect_article_links(driver):
    """
    Thu thập tất cả links từ trang tin tức IMP
    """
    # Mở trang tin tức IMP
    driver.get(IMP_NEWS_URL)
    
    # Đợi page load
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.news-item"))
        )
    except TimeoutException:
        print("⚠️ Không tìm thấy danh sách bài viết")
        return []
    
    # Thu thập links và dates
    links_with_dates = []
    cards = driver.find_elements(By.CSS_SELECTOR, "div.news-item")
    
    for card in cards:
        try:
            # Lấy link từ tiêu đề
            link_element = card.find_element(By.CSS_SELECTOR, "h3.head-title a.text-clamp-18")
            href = link_element.get_attribute("href")
            
            # Lấy date từ thẻ time
            date_element = card.find_element(By.CSS_SELECTOR, "time")
            date_text = clean_text(date_element.text)
            
            if href and href.startswith("https://"):
                links_with_dates.append({
                    'url': href,
                    'date_text': date_text
                })
                
        except Exception as e:
            print(f"⚠️ Lỗi lấy link từ card: {e}")
            continue
    
    print(f"✅ Found {len(links_with_dates)} articles from IMP")
    return links_with_dates

# ============================================
# 📄 ARTICLE EXTRACTION FUNCTIONS  
# ============================================
def extract_article(driver, article_info):
    """
    Trích xuất thông tin chi tiết từ một bài viết IMP
    """
    url = article_info['url']
    fallback_date = article_info['date_text']
    
    try:
        driver.get(url)
        
        # Đợi page load
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1.block-title.text-clamp-40"))
            )
        except TimeoutException:
            time.sleep(3)
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # 📰 Title
        title = ""
        title_selectors = [
            "h1.block-title.text-clamp-40",
            "h1.block-title",
            "h1",
            ".entry-title"
        ]
        
        for selector in title_selectors:
            title_element = soup.select_one(selector)
            if title_element:
                title = clean_text(title_element.get_text())
                break
        
        # 🕐 Time
        time_text = fallback_date
        time_selectors = [
            "section.news-detail time",
            "time",
            ".entry-date",
            ".publish-date"
        ]
        
        for selector in time_selectors:
            time_element = soup.select_one(selector)
            if time_element:
                time_text = clean_text(time_element.get_text())
                break
        
        # 📝 Content
        content_parts = []
        
        # Thử lấy content từ div.fullcontent.pt-6 trước (IMP specific)
        content_div = soup.select_one("div.fullcontent.pt-6")
        if content_div:
            paragraphs = content_div.find_all("p")
            for p in paragraphs:
                txt = clean_text(p.get_text())
                if txt and len(txt) > 10:  # Lọc bỏ đoạn quá ngắn
                    content_parts.append(txt)
        else:
            # Fallback: lấy từ section.news-detail
            news_detail = soup.select_one("section.news-detail")
            if news_detail:
                paragraphs = news_detail.find_all("p")
                for p in paragraphs:
                    txt = clean_text(p.get_text())
                    if txt and len(txt) > 10:
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
    """Tìm link gốc trong bài viết IMP (nếu có)"""
    try:
        # Tìm trong div.fullcontent hoặc main content
        content_div = soup.select_one("div.fullcontent") or soup.select_one("section.news-detail")
        if not content_div:
            return None

        anchors = content_div.select("a[href]")
        if not anchors:
            return None

        def normalize_href(href: str) -> str:
            href = (href or "").strip()
            if not href:
                return ""
            return urljoin(IMP_BASE_URL, href) if href.startswith("/") else href

        def is_external(href: str) -> bool:
            try:
                u = urlparse(href)
                return bool(u.netloc) and ("imexpharm.com" not in u.netloc.lower())
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
            parsed_date = parse_imp_datetime(article_data["fuzzy_time"])
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
def crawl_imp(table_name="IMP_News", db_manager=None):
    """
    Crawl imexpharm.com chỉ cho bảng IMP_News
    """
    start_time = time.time()
    
    # Tạo db_manager nếu không được truyền vào
    if db_manager is None:
        db_manager = get_database_manager()
    
    print(f"\n===============================================================================")
    print(f"🏭 Imexpharm Crawler - Stock: IMP")
    print(f"📋 Table: {table_name}")
    
    # Lấy existing links từ DB
    existing_links = get_recent_links_from_db(db_manager, table_name, 100)
    print(f"📊 Found {len(existing_links)} existing articles in DB (last 100)")
    
    print(f"🔍 Searching Imexpharm news")
    print(f"🌐 URL: {IMP_NEWS_URL}")
    
    driver = setup_driver()
    
    try:
        # Thu thập links
        articles_info = collect_article_links(driver)
        
        if not articles_info:
            print("❌ Không tìm thấy bài viết nào")
            return {
                'stock_code': 'IMP',
                'duration': time.time() - start_time,
                'total_found': 0,
                'crawled_count': 0,
                'new_articles': 0,
                'stopped_early': False
            }
        
        # Lọc bỏ những link đã có trong DB
        articles_to_crawl = [article for article in articles_info if article['url'] not in existing_links]
        
        if len(articles_to_crawl) > 0:
            print(f"🎯 Crawling {len(articles_to_crawl)} new articles (skipping {len(articles_info) - len(articles_to_crawl)} existing)")
        else:
            print(f"📰 No new news - all {len(articles_info)} articles already in DB")
        
        new_articles = 0
        crawled_count = 0
        duplicate_count = 0
        
        # Crawl từng bài viết mới
        for idx, article_info in enumerate(articles_to_crawl):
            try:
                print(f"📄 [{idx+1}/{len(articles_to_crawl)}] {article_info['url']}")
                raw_data = extract_article(driver, article_info)
                
                if not raw_data.get("title"):
                    print(f"⚠️ Bỏ qua bài không có title")
                    continue
                
                # Parse datetime
                if raw_data.get("fuzzy_time"):
                    dt = parse_imp_datetime(raw_data["fuzzy_time"])
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
                        print(f"⚠️ ... và {len(articles_to_crawl) - idx - 1} duplicates khác (không hiển thị)")
                
                crawled_count += 1
                time.sleep(2)  # Delay giữa các requests
                
            except Exception as e:
                print(f"❌ Lỗi crawl bài {article_info['url']}: {e}")
                continue
        
    except Exception as e:
        print(f"❌ Lỗi crawl IMP: {e}")
    finally:
        driver.quit()
    
    # Tính toán kết quả
    end_time = time.time()
    duration = end_time - start_time
    
    return {
        'stock_code': 'IMP',
        'duration': duration,
        'total_found': len(articles_info) if 'articles_info' in locals() else 0,
        'crawled_count': crawled_count,
        'new_articles': new_articles,
        'stopped_early': False
    }

# ============================================
# 🚀 MAIN FUNCTION WITH DASHBOARD
# ============================================
def main_imp():
    """Main function với dashboard timing và thống kê"""
    start_time = time.time()
    start_time_str = datetime.now().strftime("%H:%M:%S")
    
    print("\n" + "═" * 60)
    print("🏭 IMEXPHARM (IMP) CRAWLER DASHBOARD".center(60))
    print(f"⏰ Started: {start_time_str}".center(60))
    print("═" * 60)

    db_manager = get_database_manager()
    table_name = get_table_name()
    
    print(f"\n🚀 Processing Stock: IMP")
    print(f"📋 Save to: {table_name}")
    
    result = crawl_imp(table_name=table_name, db_manager=db_manager)

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
    type_name = "IMP".ljust(24)[:24]
    duration = result['duration']
    new_count = result['new_articles']
    
    status = "No new news" if new_count == 0 else "New news"
    results_text = f"{new_count} saved"
    
    print(f"│ {type_name} │ {duration:>6.1f}s │ {status:<12} │ {results_text:<17} │")
    
    # Table footer
    print("└──────────────────────────┴────────┴──────────────┴───────────────────┘")
    
    # Summary
    print("\n" + "═" * 60)
    print("📊 SUMMARY IMP CRAWLING".center(60))
    print("─" * 60)
    print(f"⏱️  Total Time      : {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
    print(f"📊 Total Found     : {result['total_found']} articles")
    print(f"🎯 Total Crawled   : {result['crawled_count']} articles")
    print(f"✅ Total New       : {result['new_articles']} articles")
    print("═" * 60)
    print("🎯 IMEXPHARM CRAWLING COMPLETED!")
    print("═" * 60)

if __name__ == "__main__":
    main_imp()
