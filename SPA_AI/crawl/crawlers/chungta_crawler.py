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

# Completely disable unnecessary warnings and logs
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
    """Get 50 most recent article links from the database for crawling"""
    try:
        supabase_client = db_manager.get_supabase_client()
        # Try using id instead of created_at if created_at is not available
        try:
            result = supabase_client.table(table_name).select("link").order("created_at", desc=True).limit(limit).execute()
        except Exception:
            # Fallback: use id or no ordering
            try:
                result = supabase_client.table(table_name).select("link").order("id", desc=True).limit(limit).execute()
            except Exception:
                # Final fallback: just get links without ordering
                result = supabase_client.table(table_name).select("link").limit(limit).execute()
        
        if result.data:
            return set(item['link'] for item in result.data if item.get('link'))
        return set()
    except Exception as e:
        print(f"Error fetching links from DB: {e}")
        return set()

def check_stop_condition(links_to_check, existing_links):
    """
    Check stopping condition: 3 consecutive articles already exist in the database
    Args:
        links_to_check: List of links to check (ordered top-down)
        existing_links: Set of links already in the database
    Returns:
        int: Index to stop at (if 3 consecutive found), -1 if not
    """
    consecutive_found = 0
    
    for i, link in enumerate(links_to_check):
        if link in existing_links:
            consecutive_found += 1
            if consecutive_found >= 3:
                # Stop at the 3rd consecutive article
                return i - 2  # Return index of the first of the 3 consecutive articles
        else:
            consecutive_found = 0  # Reset if not consecutive
    
    return -1  # No 3 consecutive articles found

def insert_article_to_database(db_manager, table_name, article_data, date_parser_func=None):
    """Insert article using the new database system"""
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
    """Normalize date text into database-compatible format"""
    if not raw_text or raw_text.strip() == "" or raw_text.strip().upper() == "EMPTY":
        return None

    raw_text = raw_text.strip()

    # Case like 23-07-2025 - 06:57 AM
    try:
        dt = datetime.strptime(raw_text, "%d-%m-%Y - %I:%M %p")
        return format_datetime_for_db(dt)
    except:
        pass

    # Case like Friday, 25/7/2025 | 18:08GMT or 30/7/2025
    try:
        match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", raw_text)
        if match:
            day, month, year = match.groups()
            dt = datetime(int(year), int(month), int(day))
            return format_datetime_for_db(dt)
    except:
        pass
    return None

# Crawl data from Chungta.vn with optimized logic
def crawl_chungta(url, table_name, db_manager):
    """Crawl Chungta.vn with optimized logic"""
    start_time = time.time()
    
    existing_links = get_recent_links_from_db(db_manager, table_name, 100)  # 100 most recent news

    options = Options()
    options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Disable logs
    options.add_argument("--disable-logging")
    options.add_argument("--log-level=3")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(options=options)

    driver.get(url)
    wait = WebDriverWait(driver, 10)

    MAX_PAGE = 1
    print(f"LOAD PAGE {MAX_PAGE}...")

    for i in range(MAX_PAGE):
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            button = wait.until(EC.element_to_be_clickable((By.ID, "load_more_redesign")))
            button.click()
            time.sleep(4)
        except:
            print(f"  Cannot load more pages (stopped at page {i})")
            break

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    articles = soup.select("h3.title-news a")
    print(f"Total {len(articles)} news from {MAX_PAGE} pages")
    # Create list of links to check
    all_links = []
    for a in articles:
        link = "https://chungta.vn" + a.get("href")
        all_links.append(link)
    
    # Check stop condition (3 consecutive articles already in DB)
    stop_index = check_stop_condition(all_links, existing_links)
    
    if stop_index >= 0:
        links_to_crawl = all_links[:stop_index]
        if len(links_to_crawl) > 0:
            print(f"Crawl {len(links_to_crawl)} new articles")
        else:
            print(f"No new news")
    else:
        # Filter only links not in DB
        links_to_crawl = [link for link in all_links if link not in existing_links]
        if len(links_to_crawl) > 0:
            print(f"Crawl {len(links_to_crawl)} new articles")
        else:
            print(f"No new news")

    # Crawl selected articles
    new_articles = 0
    crawled_count = 0
    duplicate_count = 0
    headers = {"User-Agent": "Mozilla/5.0"}

    for i, link in enumerate(links_to_crawl):
        try:
            print(f"[{i+1}/{len(links_to_crawl)}] {link}")
            
            res = requests.get(link, headers=headers, timeout=10)
            article_soup = BeautifulSoup(res.text, "html.parser")

            # Get title from original link
            title_element = None
            for a in articles:
                if "https://chungta.vn" + a.get("href") == link:
                    title_element = a
                    break
            
            title_preview = title_element.get_text(strip=True) if title_element else ""
            
            title = article_soup.select_one("h1.title-detail")
            title = title.get_text(strip=True) if title else title_preview

            date = article_soup.select_one("span.time")
            date = date.get_text(strip=True) if date else "Unknown date"

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
                print(f"Saved article: {title[:50]}...")
            else:
                duplicate_count += 1
                # Show only first 3 duplicates to avoid spam
                if duplicate_count <= 3:
                    print(f"Duplicate title - skipped: {title[:50]}...")
                elif duplicate_count == 4:
                    print(f"... and {len(links_to_crawl) - i - 1} more duplicates (not displayed)")
            
            crawled_count += 1
            time.sleep(1)  # Delay between requests

        except Exception as e:
            print(f"Error fetching article {link}: {e}")
            continue

    # Compute results
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
    """Main function with dashboard timing and statistics"""
    start_time = time.time()
    start_time_str = datetime.now().strftime("%H:%M:%S")
    
    print("\n" + "═" * 60)
    print("CHUNGTA CRAWLER DASHBOARD".center(60))
    print(f"Started: {start_time_str}".center(60))
    print("═" * 60)

    urls = [
        "https://chungta.vn/kinh-doanh",
        "https://chungta.vn/cong-nghe"
    ]
    table_name = "FPT_News"  # Save Chungta news to FPT_News because many articles are about FPT
    db_manager = get_database_manager()

    results = []
    
    for i, url in enumerate(urls, 1):
        print(f"\nProcessing URL [{i}/{len(urls)}]: {url}")
        print(f"Save to: {table_name}")
        
        result = crawl_chungta(url, table_name, db_manager)
        results.append(result)
        
        # Delay between URLs
        if i < len(urls):
            time.sleep(3)

    db_manager.close_connections()
    
    # Display dashboard results
    end_time = time.time()
    total_duration = end_time - start_time
    total_found = sum(r['total_found'] for r in results)
    total_crawled = sum(r['crawled_count'] for r in results)
    total_new = sum(r['new_articles'] for r in results)
    
    print("\n" + "═" * 60)
    print("CRAWLING COMPLETED - RESULTS".center(60))
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
        
        status = "No new news" if new_count == 0 else "New news"
        results_text = f"{new_count} saved"
        
        print(f"│ {url_short} │ {duration:>6.1f}s │ {status:<12} │ {results_text:<17} │")
    
    # Table footer
    print("└──────────────────────────┴────────┴──────────────┴───────────────────┘")
    
    # Summary
    print("\n" + "═" * 60)
    print("SUMMARY".center(60))
    print("─" * 60)
    print(f"Total Time      : {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
    print(f"Total Found     : {total_found} articles")
    print(f"Total New       : {total_new} articles")
    print(f"Avg per URL     : {total_duration/len(results):.1f}s")
    print("═" * 60)
    print("CHUNGTA CRAWLING COMPLETED!")
    print("═" * 60)

if __name__ == "__main__":
    main_chungta()
