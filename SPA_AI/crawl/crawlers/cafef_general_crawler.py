from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
from datetime import datetime
import warnings
import logging
from urllib.parse import urlparse   # ✅ NEW
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

def get_recent_links_from_db(db_manager, table_name="General_News", limit=100):
    """Lấy 100 link bài viết gần nhất từ database"""
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
    Kiểm tra điều kiện dừng: 5 bài liên tiếp có trong DB
    """
    consecutive_found = 0
    for i, link in enumerate(links_to_check):
        if link in existing_links:
            consecutive_found += 1
            if consecutive_found >= 5:
                return i - 4  # index của bài đầu tiên trong 5 bài liên tiếp
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

def convert_date(date_str):
    formats = ["%d-%m-%Y - %H:%M %p", "%d-%m-%Y", "%d/%m/%Y"]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return format_datetime_for_db(dt)
        except:
            pass
    return None

def insert_to_supabase(db_manager, table_name, data):
    """Wrapper function để tương thích với code cũ - sử dụng hàm chung"""
    return insert_article_to_database(db_manager, table_name, data, convert_date)

def setup_driver():
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
    return webdriver.Chrome(options=options)

# ========= NEW: Helpers cho source_link (CafeF) =========
def _clean_url(u: str) -> Union[str, None]:
    if not u:
        return None
    u = u.strip().strip('"').strip("'")
    u = u.replace("\u00a0", " ").strip()  # bỏ NBSP
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
    Trả về URL gốc (nguồn) trong trang bài viết CafeF, hoặc None nếu không có.
    Ưu tiên:
      1) span.link-source-full (text chứa URL)
      2) .btn-copy-link-source[data-clipboard-text]
      3) <a> hợp lệ trong .link-source-wrapper (không phải javascript:)
    """
    wrapper = soup.select_one("div.link-source-wrapper")
    if not wrapper:
        return None

    # 1) URL ở dạng text
    full = wrapper.select_one("span.link-source-full")
    if full:
        u = _clean_url(full.get_text(strip=True))
        if u and _is_external(u):
            return u

    # 2) Nút copy có data-clipboard-text
    btn = wrapper.select_one(".btn-copy-link-source")
    if btn and btn.has_attr("data-clipboard-text"):
        u = _clean_url(btn["data-clipboard-text"])
        if u and _is_external(u):
            return u

    # 3) Fallback: href trong <a>
    for a in wrapper.select("a[href]"):
        href = (a.get("href") or "").strip()
        if href.lower().startswith("javascript"):
            continue
        u = _clean_url(href)
        if u and _is_external(u):
            return u

    return None
# =======================================================

def extract_article_data(driver):
    soup = BeautifulSoup(driver.page_source, "html.parser")
    title = soup.select_one("h1.title")
    date_tag = soup.select_one("span.pdate[data-role='publishdate']")
    content_tag = soup.select_one("div.detail-content.afcbc-body")

    if not (title and date_tag and content_tag):
        return None

    content = " ".join(p.get_text(strip=True) for p in content_tag.select("p"))

    # 🔗 NEW: lấy link bài gốc từ CafeF
    source_link = extract_source_link_cafef(soup)

    return {
        "title": title.get_text(strip=True),
        "date": date_tag.get_text(strip=True),
        "content": content,
        "link": driver.current_url,   # link bài trên CafeF
        "ai_summary": None,
        "source_link": source_link    # ✅ THÊM VÀO DB
    }

def click_view_more(driver, max_clicks=5):
    for i in range(max_clicks):
        try:
            driver.execute_script("window.scrollBy(0, 1200);")
            time.sleep(1)
            btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div.btn-viewmore"))
            )
            driver.execute_script("arguments[0].scrollIntoView();", btn)
            time.sleep(0.5)
            btn.click()
            print(f"🔽 Click Xem thêm ({i+1}/{max_clicks})")
            time.sleep(2)
        except:
            break

def crawl_cafef_chung(max_clicks=5):
    """Crawl tin tức CafeF với tối ưu thời gian"""
    start_time = time.time()
    start_time_str = datetime.now().strftime("%H:%M:%S")
    
    print("\n" + "═" * 60)
    print("🚀 CAFEF GENERAL NEWS CRAWLER".center(60))
    print(f"⏰ Started: {start_time_str}".center(60))
    print("═" * 60)
    
    driver = setup_driver()
    db_manager = get_database_manager()
    
    try:
        driver.get("https://cafef.vn/thi-truong-chung-khoan.chn")
        time.sleep(3)

        # Lấy danh sách links đã có trong DB (100 bài gần nhất)
        print("🔍 Checking database for crawling optimization...")
        existing_links = get_recent_links_from_db(db_manager, "General_News", 100)  #100 news 

        # Click "Xem thêm" để load thêm bài viết
        print(f"🔄 Click 'load more' {max_clicks} lần...")
        click_view_more(driver, max_clicks=max_clicks)

        # Lấy tất cả links bài viết
        link_elements = driver.find_elements(By.CSS_SELECTOR, "div.tlitem.box-category-item h3 a")
        all_links = []
        
        for link_el in link_elements:
            url = link_el.get_attribute("href")
            if url:
                all_links.append(url)
                
        # Kiểm tra điều kiện dừng (5 bài liên tiếp có trong DB)
        stop_index = check_stop_condition(all_links, existing_links)
        
        if stop_index >= 0:
            links_to_crawl = all_links[:stop_index]
            print(f"🎯 Crawl {len(links_to_crawl)} new news")
        else:
            links_to_crawl = all_links
            print(f"🎯 Crawl all {len(links_to_crawl)} new news")

        # Crawl các bài viết được chọn
        crawled_count = 0
        new_articles = 0
        
        for i, url in enumerate(links_to_crawl):
            try:
                print(f"🔗 [{i+1}/{len(links_to_crawl)}] {url}")
                
                # Skip nếu link đã có trong DB
                if url in existing_links:
                    print(f"⏭️  Bỏ qua - đã có trong DB")
                    continue
                
                driver.execute_script("window.open(arguments[0]);", url)
                driver.switch_to.window(driver.window_handles[-1])
                time.sleep(1)
                
                data = extract_article_data(driver)
                if data:
                    # DEBUG nếu cần: print("DEBUG source_link =", data.get("source_link"))
                    success = insert_to_supabase(db_manager, "General_News", data)
                    if success:
                        new_articles += 1
                        print(f"✅ Đã lưu bài viết: {data['title'][:50]}...")
                    else:
                        print(f"⏭️  Bỏ qua - có thể đã tồn tại: {data['title'][:50]}...")
                else:
                    print(f"⚠️  Không lấy được dữ liệu bài viết")
                
                crawled_count += 1
                
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                time.sleep(1)
                
            except Exception as e:
                print(f"❌ Lỗi khi crawl bài viết {i+1}: {e}")
                continue

    except Exception as e:
        print(f"❌ Lỗi chung: {e}")
    finally:
        driver.quit()
        db_manager.close_connections()
        
        # Hiển thị kết quả
        end_time = time.time()
        duration = end_time - start_time
        
        print("\n" + "═" * 60)
        print("🎉 CRAWLING CAFEF GENERAL COMPLETED - RESULTS".center(60))
        print("═" * 60)
        
        print(f"⏱️  Total Time     : {duration:.1f}s ({duration/60:.1f} minutes)")
        print(f"📊 Articles Found : {len(all_links)} total")
        print(f"🎯 Articles Crawled: {crawled_count}")
        print(f"✅ New Articles   : {new_articles}")
        print(f"⏭️  Skipped (Exists): {len(links_to_crawl) - crawled_count}")
        print(f"⚡ Avg per Article: {duration/max(crawled_count, 1):.1f}s")
        
        if stop_index >= 0:
            print("🛑 Stopped early due to no new posts.")

        print("═" * 60)
        print("🎉 CAFEF GENERAL CRAWLING COMPLETED SUCCESSFULLY!")
        print("═" * 60)

if __name__ == "__main__":
    crawl_cafef_chung(max_clicks=2)
