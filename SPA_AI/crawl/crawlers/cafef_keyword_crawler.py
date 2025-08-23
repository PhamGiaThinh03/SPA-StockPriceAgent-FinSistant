from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from datetime import datetime
import time
import warnings
import logging
from urllib.parse import urlparse  # ✅ NEW
from typing import Union

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

def get_recent_links_from_db(db_manager, table_name, limit=100):
    """Lấy 100 link bài viết gần nhất từ database cho keyword crawling"""
    try:
        supabase_client = db_manager.get_supabase_client()
        # Thử dùng id thay vì created_at nếu không có created_at
        try:
            result = supabase_client.table(table_name).select("link").order("created_at", desc=True).limit(limit).execute()
        except Exception:
            try:
                result = supabase_client.table(table_name).select("link").order("id", desc=True).limit(limit).execute()
            except Exception:
                result = supabase_client.table(table_name).select("link").limit(limit).execute()
        if result.data:
            return set(item['link'] for item in result.data if item.get('link'))
        return set()
    except Exception as e:
        print(f"❌ Lỗi khi lấy links từ DB: {e}")
        return set()

def check_stop_condition(links_to_check, existing_links):
    """Dừng khi 3 bài liên tiếp đã có trong DB"""
    consecutive_found = 0
    for i, link in enumerate(links_to_check):
        if link in existing_links:
            consecutive_found += 1
            if consecutive_found >= 3:
                return i - 2
        else:
            consecutive_found = 0
    return -1

def insert_article_to_database(db_manager, table_name, article_data, date_parser_func=None):
    """Insert article using new database system"""
    if date_parser_func and article_data.get("date"):
        try:
            parsed_date = date_parser_func(article_data["date"])
            if parsed_date:
                article_data["date"] = parsed_date
        except Exception:
            pass
    return db_manager.insert_article(table_name, article_data)

# ================== FORMAT NGÀY ==================
def convert_date(date_str):
    if not date_str or date_str.strip() == "":
        return None
    formats = [
        "%d-%m-%Y - %I:%M %p",  # 25-07-2025 - 05:52 PM
        "%d-%m-%Y - %H:%M %p",  # 25-07-2025 - 17:52 PM (nếu site hiếm gặp)
        "%d-%m-%Y",
        "%d/%m/%Y",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return format_datetime_for_db(dt)
        except:
            continue
    print(f"⚠️ Không parse được ngày: {date_str}")
    return None

# ================== HÀM INSERT CHỐNG TRÙNG ==================
def insert_to_supabase(db_manager, table_name, data):
    """Wrapper function để tương thích với code cũ - sử dụng hàm chung"""
    return insert_article_to_database(db_manager, table_name, data, convert_date)

# ================== HÀM SETUP SELENIUM ==================
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

# ================== NEW: Helpers lấy source_link từ CafeF ==================
def _clean_url(u: str) -> Union[str, None]:
    if not u:
        return None
    u = u.strip().strip('"').strip("'").replace("\u00a0", " ").strip()
    if u.startswith("http://") or u.startswith("https://"):
        return u
    return None

def _is_external(u: str) -> bool:
    try:
        host = urlparse(u).netloc.lower()
        return bool(host) and ("cafef.vn" not in host)
    except Exception:
        return False

def extract_source_link_cafef(soup) -> Union[str, None]:
    """
    Lấy URL nguồn gốc trong bài CafeF:
      1) span.link-source-full (text)
      2) .btn-copy-link-source[data-clipboard-text]
      3) <a href> hợp lệ trong .link-source-wrapper (loại javascript:)
    """
    wrapper = soup.select_one("div.link-source-wrapper")
    if not wrapper:
        return None

    full = wrapper.select_one("span.link-source-full")
    if full:
        u = _clean_url(full.get_text(strip=True))
        if u and _is_external(u):
            return u

    btn = wrapper.select_one(".btn-copy-link-source")
    if btn and btn.has_attr("data-clipboard-text"):
        u = _clean_url(btn["data-clipboard-text"])
        if u and _is_external(u):
            return u

    for a in wrapper.select("a[href]"):
        href = (a.get("href") or "").strip()
        if href.lower().startswith("javascript"):
            continue
        u = _clean_url(href)
        if u and _is_external(u):
            return u

    return None
# ===========================================================================

# ================== TRÍCH XUẤT DỮ LIỆU BÀI VIẾT ==================
def extract_article_data(driver):
    soup = BeautifulSoup(driver.page_source, "html.parser")
    try:
        title_tag = soup.select_one("h1.title")
        date_tag = soup.select_one("span.pdate[data-role='publishdate']")
        content_container = soup.select_one("div.detail-content.afcbc-body")

        if not (title_tag and date_tag and content_container):
            return None

        content = " ".join(p.get_text(strip=True) for p in content_container.select("p"))

        # 🔗 NEW: lấy link bài gốc
        source_link = extract_source_link_cafef(soup)

        return {
            "title": title_tag.get_text(strip=True),
            "date": date_tag.get_text(strip=True),
            "content": content,
            "link": driver.current_url,
            "ai_summary": None,           # (nếu sau này có thể thêm)
            "source_link": source_link,   # ✅ THÊM VÀO DB
        }
    except:
        return None

# ================== CRAWL THEO TỪ KHÓA VỚI TỐI ƯU ==================
def crawl_articles_sequentially(keyword="FPT", table_name="FPT_News", max_pages=1):
    """Crawl articles với tối ưu thời gian"""
    start_time = time.time()
    
    driver = setup_driver()
    wait = WebDriverWait(driver, 10)
    db_manager = get_database_manager()
    
    try:
        existing_links = get_recent_links_from_db(db_manager, table_name, 50)
        all_links = []
        crawled_count = 0
        new_articles = 0
        
        # Lấy links từ các trang
        for page in range(1, max_pages + 1):
            search_url = f"https://cafef.vn/tim-kiem/trang-{page}.chn?keywords={keyword.replace(' ', '%20')}"
            print(f"🔎 PAGE {page}: {search_url}")
            driver.get(search_url)
            time.sleep(2)

            article_links = driver.find_elements(By.CSS_SELECTOR, "div.item h3.titlehidden a")
            page_links = [link.get_attribute("href") for link in article_links if link.get_attribute("href")]
            all_links.extend(page_links)

        print(f"📄 Total {len(all_links)} news from {max_pages} pages")

        # 🚀 IMPROVED: Kiểm tra và lọc bỏ existing links trước
        links_to_crawl = []
        consecutive_existing = 0
        
        for link in all_links:
            if link in existing_links:
                consecutive_existing += 1
                # Nếu 3 bài liên tiếp đã có → dừng luôn
                if consecutive_existing >= 3:
                    print(f"🛑 Found {consecutive_existing} consecutive existing articles - stopping here")
                    break
            else:
                consecutive_existing = 0  # Reset nếu gặp bài mới
                links_to_crawl.append(link)
        
        print(f"🎯 Crawl {len(links_to_crawl)} bài viết mới" if links_to_crawl else "📰 No new news")

        # Crawl các bài viết được chọn
        duplicate_count = 0
        consecutive_duplicates = 0  # Track liên tiếp duplicate
        
        for i, url in enumerate(links_to_crawl):
            try:
                print(f"🔗 [{i+1}/{len(links_to_crawl)}] {url}")
                driver.get(url)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1.title")))
                time.sleep(1)
                
                data = extract_article_data(driver)
                if data:
                    success = insert_to_supabase(db_manager, table_name, data)
                    if success:
                        new_articles += 1
                        consecutive_duplicates = 0  # Reset khi có bài mới
                        print(f"✅ Đã lưu bài viết: {data['title'][:50]}...")
                    else:
                        duplicate_count += 1
                        consecutive_duplicates += 1
                        
                        if duplicate_count <= 3:
                            print(f"⚠️  Duplicate title - skipped: {data['title'][:50]}...")
                        elif duplicate_count == 4:
                            print(f"⚠️  ... và {len(links_to_crawl) - i - 1} duplicates khác (ẩn bớt log)")
                        
                        # 🚀 EARLY STOP: Nếu 5 bài liên tiếp duplicate → dừng ngay
                        if consecutive_duplicates >= 5:
                            print(f"🛑 Stopped crawling - Found {consecutive_duplicates} consecutive duplicates")
                            print(f"📊 Saved {new_articles} new articles, skipped {duplicate_count} duplicates")
                            break
                else:
                    print("⚠️  Không lấy được dữ liệu bài viết")
                
                crawled_count += 1
                time.sleep(1)
            except Exception as e:
                print(f"❌ Lỗi khi crawl bài viết {i+1}: {e}")
                continue

    except Exception as e:
        print(f"❌ Lỗi chung cho keyword {keyword}: {e}")
    finally:
        driver.quit()
        db_manager.close_connections()
        
        duration = time.time() - start_time
        return {
            'keyword': keyword,
            'table_name': table_name,
            'duration': duration,
            'total_found': len(all_links),
            'crawled_count': crawled_count,
            'new_articles': new_articles,
            'stopped_early': consecutive_existing >= 3
        }

# ================== MAIN VỚI DASHBOARD ==================
def main_cafef():
    start_time = time.time()
    start_time_str = datetime.now().strftime("%H:%M:%S")
    
    print("\n" + "═" * 60)
    print("🚀 CAFEF KEYWORD CRAWLER DASHBOARD".center(60))
    print(f"⏰ Started: {start_time_str}".center(60))
    print("═" * 60)

    keyword_table_map = {
        "FPT": "FPT_News",
        "GAS": "GAS_News", 
        "IMP": "IMP_News",
        "VCB": "VCB_News",
    }
    
    results = []
    for kw, table_name in keyword_table_map.items():
        print(f"\n🚀 Processing keyword CAFEF: ---{kw}---  → Save to {table_name}")
        result = crawl_articles_sequentially(keyword=kw, table_name=table_name, max_pages=1)
        results.append(result)
        if kw != list(keyword_table_map.keys())[-1]:
            time.sleep(3)
    
    end_time = time.time()
    total_duration = end_time - start_time
    total_found = sum(r['total_found'] for r in results)
    total_crawled = sum(r['crawled_count'] for r in results)
    total_new = sum(r['new_articles'] for r in results)
    
    print("\n" + "═" * 60)
    print("🎉 CRAWLING CAFEF KEYWORD CRAWLER COMPLETED - RESULTS".center(60))
    print("═" * 60)
    print("┌─────────┬────────┬──────────────┬───────────────────┐")
    print("│ Keyword │ Time   │ Status       │ Saved Articles    │")
    print("├─────────┼────────┼──────────────┼───────────────────┤")
    for result in results:
        keyword = result['keyword']
        duration = result['duration']
        new_count = result['new_articles']
        status = "No new news" if new_count == 0 else "New news"
        results_text = f"{new_count} saved"
        print(f"│ {keyword:<7} │ {duration:>6.1f}s │ {status:<12} │ {results_text:<17} │")
    print("└─────────┴────────┴──────────────┴───────────────────┘")
    print("\n" + "═" * 60)
    print("📊 SUMMARY CAFEF KEYWORD CRAWLER".center(60))
    print("─" * 60)
    print(f"⏱️  Total Time      : {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
    print(f"📊 Total Found     : {total_found} articles")
    print(f"✅ Total New       : {total_new} articles")
    print(f"⚡ Avg per Keyword : {total_duration/len(results):.1f}s")
    print("═" * 60)
    print("🎯 CAFEF KEYWORD CRAWLING COMPLETED!")
    print("═" * 60)

if __name__ == "__main__":
    main_cafef()
