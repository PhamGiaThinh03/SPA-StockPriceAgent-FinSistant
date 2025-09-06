#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main Crawler Controller
Run all crawlers in an organized flow
Author: Auto-generated
Date: August 3, 2025
"""

import sys
import os
import time
import logging
from datetime import datetime
from typing import List, Dict, Callable

# Import crawler modules
from crawlers.fireant_crawler import crawl_fireant
from crawlers.cafef_keyword_crawler import main_cafef
from crawlers.cafef_general_crawler import crawl_cafef_chung
from crawlers.chungta_crawler import main_chungta
from crawlers.markettime import crawl_markettimes, crawl_markettimes_general, main_markettimes
from crawlers.diendandoanhnghiep import crawl_dddn_stock, crawl_dddn_general, main_dddn
from crawlers.crawl_imp import crawl_imp, main_imp
from crawlers.petrotimes import crawl_petrotimes_gas, main_petrotimes

# Import centralized database system
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import SupabaseManager

# Helper function for compatibility
def get_database_manager():
    """Get database manager instance"""
    return SupabaseManager()

# Import stock crawler
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'crawl_stock'))
from crawl_stock.crawl_stock_price_history import main_stock_simplize

# Configure logging with UTF-8 encoding for Windows
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/crawl_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class CrawlerController:
    """Controller to manage and run all crawlers"""
    
    def __init__(self):
        self.start_time = None
        self.crawlers_status = {}
        
    def log_start(self, crawler_name: str):
        """Log crawler start"""
        logger.info(f"[START] Starting {crawler_name}")
        self.crawlers_status[crawler_name] = {
            'start_time': datetime.now(),
            'status': 'running'
        }
        
    def log_success(self, crawler_name: str):
        """Log crawler success"""
        end_time = datetime.now()
        start_time = self.crawlers_status[crawler_name]['start_time']
        duration = end_time - start_time
        
        self.crawlers_status[crawler_name].update({
            'end_time': end_time,
            'status': 'success',
            'duration': duration
        })
        
        logger.info(f"[SUCCESS] {crawler_name} completed in {duration}")
        
    def log_error(self, crawler_name: str, error: Exception):
        """Log crawler error"""
        end_time = datetime.now()
        start_time = self.crawlers_status[crawler_name]['start_time']
        duration = end_time - start_time
        
        self.crawlers_status[crawler_name].update({
            'end_time': end_time,
            'status': 'error',
            'duration': duration,
            'error': str(error)
        })
        
        logger.error(f"[ERROR] {crawler_name} failed after {duration}: {error}")
        
    def run_crawler(self, crawler_func: Callable, crawler_name: str, *args, **kwargs):
        """Run a crawler with error handling"""
        try:
            self.log_start(crawler_name)
            result = crawler_func(*args, **kwargs)
            self.log_success(crawler_name)
            return result
        except Exception as e:
            self.log_error(crawler_name, e)
            return None
            
    def run_fireant_crawlers(self):
        """Run FireAnt crawlers"""
        logger.info("=== FIREANT CRAWLERS ===")
        
        # Crawler for all stock codes
        stock_codes = ["FPT", "GAS", "IMP", "VCB"]
        for stock_code in stock_codes:
            self.run_crawler(
                crawl_fireant, 
                f"FireAnt {stock_code} Stock", 
                stock_code=stock_code, 
                table_name=f"{stock_code}_News"
            )
        
        print("FireAnt General News crawling has been disabled - only processing stock-specific news")
        
    def run_cafef_crawlers(self):
        """Run CafeF crawlers"""
        logger.info("=== CAFEF CRAWLERS ===")
        
        # CafeF crawler with keyword
        self.run_crawler(
            main_cafef,
            "CafeF Keyword Search"
        )
        
        # CafeF general crawler
        self.run_crawler(
            crawl_cafef_chung,
            "CafeF General News",
            max_clicks=5
        )
        
    def run_chungta_crawler(self):
        """Run ChungTa crawler"""
        logger.info("=== CHUNGTA CRAWLER ===")
        
        self.run_crawler(
            main_chungta,
            "ChungTa News"
        )
        
    def run_markettimes_crawlers(self):
        """Run MarketTimes crawlers"""
        logger.info("=== MARKETTIMES CRAWLERS ===")
        
        # Crawler for all stock codes
        stock_codes = ["FPT", "GAS", "IMP", "VCB"]
        for stock_code in stock_codes:
            self.run_crawler(
                crawl_markettimes, 
                f"MarketTimes {stock_code} Stock", 
                stock_code=stock_code, 
                table_name=f"{stock_code}_News"
            )
        
        # Crawler for general MarketTimes news
        self.run_crawler(
            crawl_markettimes_general,
            "MarketTimes General News",
            table_name="General_News"
        )
        
    def run_dddn_crawlers(self):
        """Run DiendanDoanhNghiep crawlers"""
        logger.info("=== DIENDANDOANHNGHIEP CRAWLERS ===")
        
        # Crawler for all stock codes
        stock_codes = ["FPT", "GAS", "IMP", "VCB"]
        for stock_code in stock_codes:
            self.run_crawler(
                crawl_dddn_stock, 
                f"DiendanDoanhNghiep {stock_code} Stock", 
                stock_code=stock_code, 
                table_name=f"{stock_code}_News"
            )
        
        # Crawler for general DiendanDoanhNghiep news
        self.run_crawler(
            crawl_dddn_general,
            "DiendanDoanhNghiep General News",
            table_name="General_News"
        )
        
    def run_imp_crawler(self):
        """Run IMP News crawler"""
        logger.info("=== IMP NEWS CRAWLER ===")
        
        self.run_crawler(
            crawl_imp,
            "IMP News Crawler",
            table_name="IMP_News"
        )
        
    def run_petrotimes_crawler(self):
        """Run Petrotimes GAS crawler"""
        logger.info("=== PETROTIMES GAS CRAWLER ===")
        
        self.run_crawler(
            crawl_petrotimes_gas,
            "Petrotimes GAS News Crawler",
            table_name="GAS_News"
        )
        
    def run_stock_crawler(self):
        """Run Stock Price crawler"""
        logger.info("=== STOCK PRICE CRAWLER ===")
        
        self.run_crawler(
            main_stock_simplize,
            "Stock Price Crawler"
        )
        
    def print_summary(self):
        """Print summary report"""
        logger.info("\n" + "="*60)
        logger.info("CRAWLING SESSION SUMMARY")
        logger.info("="*60)
        
        total_duration = datetime.now() - self.start_time
        successful = sum(1 for status in self.crawlers_status.values() if status['status'] == 'success')
        failed = sum(1 for status in self.crawlers_status.values() if status['status'] == 'error')
        
        logger.info(f"Total time: {total_duration}")
        logger.info(f"Successful: {successful}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Total crawlers: {len(self.crawlers_status)}")
        
        logger.info("\nDetails for each crawler:")
        for name, status in self.crawlers_status.items():
            status_icon = "[OK]" if status['status'] == 'success' else "[FAIL]"
            duration = status.get('duration', 'N/A')
            logger.info(f"{status_icon} {name}: {duration}")
            
            if status['status'] == 'error':
                logger.info(f"   Error: {status.get('error', 'Unknown error')}")
                
    def run_all_crawlers(self):
        """Run all crawlers in sequence"""
        self.start_time = datetime.now()
        
        logger.info("=" * 50)
        logger.info("STARTING CRAWLING SESSION")
        logger.info("=" * 50)
        logger.info(f"Start time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # 1. Run Stock Price crawler first
            self.run_stock_crawler()
            time.sleep(2)  # Pause between sessions
            
            # 2. Run FireAnt crawlers
            self.run_fireant_crawlers()
            time.sleep(2)
            
            # 3. Run CafeF crawlers  
            self.run_cafef_crawlers()
            time.sleep(2)
            
            # 4. Run ChungTa crawler
            self.run_chungta_crawler()
            time.sleep(2)
            
            # 5. Run MarketTimes crawlers
            self.run_markettimes_crawlers()
            time.sleep(2)
            
            # 6. Run DiendanDoanhNghiep crawlers
            self.run_dddn_crawlers()
            time.sleep(2)
            
            # 7. Run IMP crawler
            self.run_imp_crawler()
            time.sleep(2)
            
            # 8. Run Petrotimes GAS crawler
            self.run_petrotimes_crawler()
            
        except KeyboardInterrupt:
            logger.warning("User stopped crawling session")
        except Exception as e:
            logger.error(f"Critical error in crawling session: {e}")
        finally:
            self.print_summary()

def run_single_crawler(crawler_name: str):
    """Run a single crawler"""
    controller = CrawlerController()
    
    crawler_map = {
        'fireant_fpt': lambda: crawl_fireant(stock_code="FPT", table_name="FPT_News"),
        'fireant_gas': lambda: crawl_fireant(stock_code="GAS", table_name="GAS_News"),
        'fireant_imp': lambda: crawl_fireant(stock_code="IMP", table_name="IMP_News"),
        'fireant_vcb': lambda: crawl_fireant(stock_code="VCB", table_name="VCB_News"),
        'cafef_keyword': main_cafef,
        'cafef_general': lambda: crawl_cafef_chung(max_clicks=5),
        'chungta': main_chungta,
        'markettimes_fpt': lambda: crawl_markettimes(stock_code="FPT", table_name="FPT_News"),
        'markettimes_gas': lambda: crawl_markettimes(stock_code="GAS", table_name="GAS_News"),
        'markettimes_imp': lambda: crawl_markettimes(stock_code="IMP", table_name="IMP_News"),
        'markettimes_vcb': lambda: crawl_markettimes(stock_code="VCB", table_name="VCB_News"),
        'markettimes_general': lambda: crawl_markettimes_general(table_name="General_News"),
        'markettimes_all': main_markettimes,
        'dddn_fpt': lambda: crawl_dddn_stock(stock_code="FPT", table_name="FPT_News"),
        'dddn_gas': lambda: crawl_dddn_stock(stock_code="GAS", table_name="GAS_News"),
        'dddn_imp': lambda: crawl_dddn_stock(stock_code="IMP", table_name="IMP_News"),
        'dddn_vcb': lambda: crawl_dddn_stock(stock_code="VCB", table_name="VCB_News"),
        'dddn_general': lambda: crawl_dddn_general(table_name="General_News"),
        'dddn_all': main_dddn,
        'imp_news': lambda: crawl_imp(table_name="IMP_News"),
        'imp_all': main_imp,
        'petrotimes_gas': lambda: crawl_petrotimes_gas(table_name="GAS_News"),
        'petrotimes_all': main_petrotimes,
        'stock_price': main_stock_simplize
    }
    
    if crawler_name not in crawler_map:
        logger.error(f"Crawler not found: {crawler_name}")
        logger.info(f"Available crawlers: {list(crawler_map.keys())}")
        return
        
    controller.start_time = datetime.now()
    controller.run_crawler(crawler_map[crawler_name], crawler_name.title())
    controller.print_summary()

def main_crawl():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='News Crawler Controller')
    parser.add_argument('--single', '-s', help='Run a single crawler', 
                       choices=['fireant_fpt', 'fireant_gas', 'fireant_imp', 'fireant_vcb', 
                               'cafef_keyword', 'cafef_general', 'chungta', 
                               'markettimes_fpt', 'markettimes_gas', 'markettimes_imp', 'markettimes_vcb', 
                               'markettimes_general', 'markettimes_all',
                               'dddn_fpt', 'dddn_gas', 'dddn_imp', 'dddn_vcb', 'dddn_general', 'dddn_all',
                               'imp_news', 'imp_all',
                               'petrotimes_gas', 'petrotimes_all',
                               'stock_price'])
    parser.add_argument('--list', '-l', action='store_true', help='List available crawlers')
    
    args = parser.parse_args()
    
    if args.list:
        print("Available crawlers:")
        print("  - fireant_fpt: FireAnt FPT stock news")
        print("  - fireant_gas: FireAnt GAS stock news")
        print("  - fireant_imp: FireAnt IMP stock news")
        print("  - fireant_vcb: FireAnt VCB stock news")
        print("  - cafef_keyword: CafeF keyword search")
        print("  - cafef_general: CafeF general news")
        print("  - chungta: ChungTa news")
        print("  - markettimes_fpt: MarketTimes FPT stock news")
        print("  - markettimes_gas: MarketTimes GAS stock news")
        print("  - markettimes_imp: MarketTimes IMP stock news")
        print("  - markettimes_vcb: MarketTimes VCB stock news")
        print("  - markettimes_general: MarketTimes general news")
        print("  - markettimes_all: MarketTimes all crawlers")
        print("  - dddn_fpt: DiendanDoanhNghiep FPT stock news")
        print("  - dddn_gas: DiendanDoanhNghiep GAS stock news")
        print("  - dddn_imp: DiendanDoanhNghiep IMP stock news")
        print("  - dddn_vcb: DiendanDoanhiep VCB stock news")
        print("  - dddn_general: DiendanDoanhiep general news")
        print("  - dddn_all: DiendanDoanhiep all crawlers")
        print("  - imp_news: IMP News crawler")
        print("  - imp_all: IMP News all functions")
        print("  - petrotimes_gas: Petrotimes GAS stock news")
        print("  - petrotimes_all: Petrotimes all crawlers")
        print("  - stock_price: Stock price history from Simplize")
        return
        
    if args.single:
        run_single_crawler(args.single)
    else:
        # Run all crawlers
        controller = CrawlerController()
        controller.run_all_crawlers()

if __name__ == "__main__":
    main_crawl()
