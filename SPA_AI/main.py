#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SPA VIP - INTEGRATED NEWS PROCESSING SYSTEM
Main pipeline controller for crawling and AI summarization

Author: Auto-generated
Date: August 3, 2025
"""

import sys
import os
import time
import logging
import argparse
from datetime import datetime
from typing import Dict, Any

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
crawl_path = os.path.join(current_dir, 'crawl')
summarization_path = os.path.join(current_dir, 'summarization')
sentiment_path = os.path.join(current_dir, 'sentiment')
timeseries_path = os.path.join(current_dir, 'timeseries')
industry_path = os.path.join(current_dir, 'industry')

sys.path.insert(0, crawl_path)
sys.path.insert(0, summarization_path)
sys.path.insert(0, sentiment_path)
sys.path.insert(0, timeseries_path)
sys.path.insert(0, industry_path)

# Import database manager
from database import SupabaseManager, DatabaseConfig

# Create logs directory if it does not exist
os.makedirs('logs', exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/spa_vip_pipeline_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log', 
                           encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class SPAVIPPipeline:
    """
    Integrated pipeline for SPA VIP system
    Combines crawling and AI summarization in a unified workflow
    """
    
    def __init__(self):
        """Initialize the integrated pipeline"""
        self.start_time = None
        self.db_manager = None
        self.crawl_results = {}
        self.summarization_results = {}
        self.sentiment_results = {}
        self.timeseries_results = {}
        self.industry_results = {}
        
        # Create logs directory if it does not exist
        os.makedirs('logs', exist_ok=True)
        
        logger.info("SPA VIP Pipeline initialized")
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database connection"""
        try:
            self.db_manager = SupabaseManager()
            
            # Test connection
            if self.db_manager.test_connection():
                logger.info("Database connection established")
            else:
                raise Exception("Database connection test failed")
                
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def show_system_status(self):
        """Display current system status"""
        logger.info("\n" + "="*80)
        logger.info("SPA VIP SYSTEM STATUS")
        logger.info("="*80)
        
        # Database statistics
        stats = self.db_manager.get_table_stats()
        
        total_articles = sum(table_stats['total'] for table_stats in stats.values())
        total_summarized = sum(table_stats['summarized'] for table_stats in stats.values())
        total_pending = sum(table_stats['unsummarized'] for table_stats in stats.values())
        total_classified = sum(table_stats.get('classified', 0) for table_stats in stats.values())
        total_unclassified = sum(table_stats.get('unclassified', 0) for table_stats in stats.values())
        
        overall_completion = (total_summarized / total_articles * 100) if total_articles > 0 else 0
        overall_classification = (total_classified / total_summarized * 100) if total_summarized > 0 else 0
        
        logger.info(f"Total Articles: {total_articles:,}")
        logger.info(f"AI Summarized: {total_summarized:,}")
        logger.info(f"Industry Classified: {total_classified:,}")
        logger.info(f"Pending Summary: {total_pending:,}")
        logger.info(f"Pending Classification: {total_unclassified:,}")
        logger.info(f"Summary Rate: {overall_completion:.1f}%")
        logger.info(f"Classification Rate: {overall_classification:.1f}%")
        logger.info("")
        
        logger.info("TABLE BREAKDOWN:")
        logger.info("-" * 80)
        logger.info(f"{'Table':<15} {'Total':<8} {'Summary':<8} {'Industry':<10} {'S-Rate':<8} {'I-Rate':<8}")
        logger.info("-" * 80)
        
        for table_name, table_stats in stats.items():
            summary_rate = table_stats['completion_rate']
            classification_rate = table_stats.get('classification_rate', 0)
            logger.info(f"{table_name:<15} {table_stats['total']:<8} "
                       f"{table_stats['summarized']:<8} {table_stats.get('classified', 0):<10} "
                       f"{summary_rate:.1f}%{'':<3} {classification_rate:.1f}%")
        
        logger.info("="*80)
    
    def run_crawling_phase(self, crawler_options: Dict[str, Any] = None):
        """
        Execute crawling phase
        
        Args:
            crawler_options: Options for crawler execution
        """
        logger.info("\nPHASE 1: NEWS CRAWLING")
        logger.info("="*50)
        
        phase_start = time.time()
        
        try:
            # Import main crawl function
            from crawl.main_crawl import CrawlerController, run_single_crawler
            
            # Check if single crawler option is provided
            if crawler_options and crawler_options.get('single'):
                single_crawler = crawler_options['single']
                logger.info(f"Running single crawler: {single_crawler}")
                run_single_crawler(single_crawler)
            else:
                logger.info("Running all crawlers...")
                # Run all crawlers
                controller = CrawlerController()
                controller.run_all_crawlers()
            
            phase_time = time.time() - phase_start
            self.crawl_results = {
                'status': 'success',
                'duration': phase_time,
                'crawlers_status': {'all_crawlers': {'status': 'success'}}
            }
            
            logger.info(f"Crawling phase completed in {phase_time/60:.1f} minutes")
            
        except Exception as e:
            phase_time = time.time() - phase_start
            self.crawl_results = {
                'status': 'error',
                'duration': phase_time,
                'error': str(e)
            }
            logger.error(f"Crawling phase failed: {e}")
            raise
    
    def run_summarization_phase(self, summarization_options: Dict[str, Any] = None):
        """
        Execute AI summarization phase with Map-Reduce support
        
        Args:
            summarization_options: Options for summarization
                - table: Specific table to process
                - priority: Process by priority
                - use_map_reduce: Enable/disable Map-Reduce (default: True)
                - analyze_texts: Analyze text lengths only
        """
        logger.info("\nPHASE 2: AI SUMMARIZATION")
        logger.info("="*50)
        
        phase_start = time.time()
        
        try:
            # Import summarization pipeline
            from summarization.main_summarization import SummarizationPipeline
            
            # Get Map-Reduce setting
            use_map_reduce = summarization_options.get('use_map_reduce', True) if summarization_options else True
            
            # Initialize pipeline with Map-Reduce option
            pipeline = SummarizationPipeline(use_map_reduce=use_map_reduce)
            
            logger.info(f"Map-Reduce: {'ENABLED' if use_map_reduce else 'DISABLED'}")
            
            if summarization_options and summarization_options.get('analyze_texts'):
                # Analyze text lengths only
                logger.info("Analyzing text lengths in database...")
                pipeline._analyze_database_texts()
                processed = 0
                
            elif summarization_options and summarization_options.get('table'):
                # Process specific table
                table_name = summarization_options['table']
                logger.info(f"Processing specific table: {table_name}")
                processed = pipeline.process_specific_table(table_name)
                
            elif summarization_options and summarization_options.get('priority'):
                # Process by priority
                logger.info("Processing all tables by priority")
                processed = pipeline.process_all_tables_by_priority()
                
            else:
                # Default: process by priority
                logger.info("Processing all tables by priority (default)")
                processed = pipeline.process_all_tables_by_priority()
            
            phase_time = time.time() - phase_start
            self.summarization_results = {
                'status': 'success',
                'duration': phase_time,
                'articles_processed': processed if isinstance(processed, int) else 0
            }
            
            logger.info(f"Summarization phase completed in {phase_time/60:.1f} minutes")
            
        except Exception as e:
            phase_time = time.time() - phase_start
            self.summarization_results = {
                'status': 'error', 
                'duration': phase_time,
                'error': str(e)
            }
            logger.error(f"Summarization phase failed: {e}")
            raise
    
    def run_sentiment_phase(self, sentiment_options: Dict[str, Any] = None):
        """
        Execute sentiment analysis phase
        
        Args:
            sentiment_options: Options for sentiment analysis
                - tables: List of specific tables to process
                - update_stock: Whether to update stock tables (default: True)
                - recalculate_all_stock: Whether to recalculate all stock sentiment stats (default: False)
                - optimized_update: Whether to use optimized update (only affected trading days) (default: False)
                - 30day_aggregate: Whether to use 30-day aggregation (weekend/holiday aggregation) (default: True)
        """
        logger.info("\nPHASE 3: SENTIMENT ANALYSIS")
        logger.info("="*50)
        
        phase_start = time.time()
        
        try:
            # Get options
            tables = sentiment_options.get('tables') if sentiment_options else None
            update_stock = sentiment_options.get('update_stock', True) if sentiment_options else True
            recalculate_all_stock = sentiment_options.get('recalculate_all_stock', False) if sentiment_options else False
            optimized_update = sentiment_options.get('optimized_update', False) if sentiment_options else False
            use_30day_aggregate = sentiment_options.get('30day_aggregate', True) if sentiment_options else True
            
            if use_30day_aggregate and not recalculate_all_stock:
                # Use 30-day sentiment aggregation logic (default)
                logger.info("Using 30-DAY SENTIMENT AGGREGATION mode (default)")
                from sentiment.reset_aggregate_sentiment_30days import reset_and_aggregate_sentiment_30days
                from sentiment.predict_sentiment_db import get_database_manager, predict_and_update_sentiment
                from database import DatabaseConfig
                
                if tables is None:
                    # Default: process all stock news tables
                    config = DatabaseConfig()
                    tables = [config.get_table_name(stock_code=code) for code in ["FPT", "GAS", "IMP", "VCB"]]
                    tables.append(config.get_table_name(is_general=True))
                
                db_manager = get_database_manager()
                total_updated_dates = set()
                
                # Phase 1: Predict sentiment for new records
                stock_updates = {}
                for table_name in tables:
                    logger.info(f"Processing table: {table_name}")
                    try:
                        updated_dates = predict_and_update_sentiment(db_manager, table_name)
                        total_updated_dates.update(updated_dates)
                        
                        # Store updated dates for 30-day aggregation
                        if table_name.endswith("_News") and table_name != "General_News":
                            stock_code = table_name.replace("_News", "")
                            stock_updates[stock_code] = updated_dates
                        
                        logger.info(f"Completed processing {table_name}")
                    except Exception as e:
                        logger.error(f"Error processing {table_name}: {e}")
                
                # Phase 2: 30-day sentiment aggregation for stock tables
                if update_stock:
                    logger.info("Phase 2: 30-DAY SENTIMENT AGGREGATION")
                    
                    for stock_code in ["FPT", "GAS", "IMP", "VCB"]:
                        if stock_code in stock_updates and stock_updates[stock_code]:
                            logger.info(f"Processing 30-day aggregation for {stock_code}")
                            try:
                                reset_and_aggregate_sentiment_30days(stock_code)
                                logger.info(f"Completed 30-day aggregation for {stock_code}")
                            except Exception as e:
                                logger.error(f"Error 30-day aggregation {stock_code}: {e}")
                        else:
                            logger.info(f"Skipping {stock_code} - no new predictions")
                
                db_manager.close_connections()
                processed_dates = total_updated_dates
                
            elif optimized_update:
                # Use optimized sentiment update logic
                logger.info("Using OPTIMIZED sentiment update mode")
                from sentiment.optimized_sentiment_update import optimized_process_sentiment_to_stock
                from sentiment.predict_sentiment_db import get_database_manager, predict_and_update_sentiment
                from database import DatabaseConfig
                
                if tables is None:
                    # Default: process all stock news tables
                    config = DatabaseConfig()
                    tables = [config.get_table_name(stock_code=code) for code in ["FPT", "GAS", "IMP", "VCB"]]
                    tables.append(config.get_table_name(is_general=True))
                
                db_manager = get_database_manager()
                total_updated_dates = set()
                
                # Phase 1: Predict sentiment for new records
                stock_updates = {}
                for table_name in tables:
                    logger.info(f"Processing table: {table_name}")
                    try:
                        updated_dates = predict_and_update_sentiment(db_manager, table_name)
                        total_updated_dates.update(updated_dates)
                        
                        if table_name.endswith("_News") and table_name != "General_News":
                            stock_code = table_name.replace("_News", "")
                            stock_updates[stock_code] = updated_dates
                        
                        logger.info(f"Completed processing {table_name}")
                    except Exception as e:
                        logger.error(f"Error processing {table_name}: {e}")
                
                # Phase 2: Optimized stock table updates
                if update_stock:
                    logger.info("Phase 2: OPTIMIZED Stock Table Updates")
                    
                    from sentiment.predict_sentiment_db import ensure_all_stock_sentiment_not_null
                    logger.info("Ensuring stock sentiment columns are not NULL...")
                    ensure_all_stock_sentiment_not_null(db_manager)
                    
                    for stock_code, updated_dates in stock_updates.items():
                        if updated_dates:
                            try:
                                optimized_process_sentiment_to_stock(db_manager, stock_code, updated_dates)
                            except Exception as e:
                                logger.error(f"Error optimized processing {stock_code}: {e}")
                        else:
                            logger.info(f"Skipping {stock_code} - no new predictions")
                
                db_manager.close_connections()
                processed_dates = total_updated_dates
            else:
                # Use standard sentiment analysis pipeline
                from sentiment.predict_sentiment_db import run_sentiment_analysis_pipeline
                
                if tables:
                    logger.info(f"Processing specific tables: {tables}")
                    processed_dates = run_sentiment_analysis_pipeline(tables, update_stock, recalculate_all_stock)
                else:
                    logger.info("Processing all news tables")
                    processed_dates = run_sentiment_analysis_pipeline(None, update_stock, recalculate_all_stock)
            
            phase_time = time.time() - phase_start
            self.sentiment_results = {
                'status': 'success',
                'duration': phase_time,
                'dates_processed': len(processed_dates) if processed_dates else 0
            }
            
            logger.info(f"Sentiment analysis phase completed in {phase_time/60:.1f} minutes")
            
        except Exception as e:
            phase_time = time.time() - phase_start
            self.sentiment_results = {
                'status': 'error',
                'duration': phase_time,
                'error': str(e)
            }
            logger.error(f"Sentiment analysis phase failed: {e}")
            raise
    
    def run_timeseries_phase(self, timeseries_options: Dict[str, Any] = None):
        """
        Execute timeseries prediction phase
        
        Args:
            timeseries_options: Options for timeseries prediction
                - stock_codes: List of specific stock codes to predict
                - predict_all: Whether to predict all available stocks (default: True)
        """
        logger.info("\nPHASE 4: TIMESERIES PREDICTION")
        logger.info("="*50)
        
        phase_start = time.time()
        
        try:
            # Import timeseries pipeline
            from timeseries.main_timeseries import TimeseriesPipeline
            
            # Initialize pipeline
            pipeline = TimeseriesPipeline()
            
            if timeseries_options and timeseries_options.get('stock_codes'):
                # Predict specific stocks
                stock_codes = timeseries_options['stock_codes']
                logger.info(f"Predicting specific stocks: {stock_codes}")
                results = pipeline.predict_specific_stocks(stock_codes)
                
            else:
                # Default: predict all stocks
                logger.info("Predicting all available stocks")
                results = pipeline.predict_all_stocks()
            
            # Close connections
            pipeline.close_connections()
            
            phase_time = time.time() - phase_start
            self.timeseries_results = {
                'status': 'success',
                'duration': phase_time,
                'predictions_made': results.get('successful_predictions', 0),
                'total_stocks': results.get('total_stocks', 0),
                'success_rate': results.get('summary', {}).get('success_rate', 0)
            }
            
            logger.info(f"Timeseries prediction phase completed in {phase_time/60:.1f} minutes")
            
        except Exception as e:
            phase_time = time.time() - phase_start
            self.timeseries_results = {
                'status': 'error',
                'duration': phase_time,
                'error': str(e)
            }
            logger.error(f"Timeseries prediction phase failed: {e}")
            raise
    
    def run_industry_phase(self, industry_options: Dict[str, Any] = None):
        """
        Execute industry classification phase
        
        Args:
            industry_options: Options for industry classification
                - tables: List of specific tables to process
                - batch_size: Number of articles to process in one batch (default: 50)
                - process_all: Process ALL pending articles in batches (default: False)
        """
        logger.info("\nPHASE 5: INDUSTRY CLASSIFICATION")
        logger.info("="*50)
        
        phase_start = time.time()
        
        try:
            # Import industry pipeline
            from industry.pipeline.classification_pipeline import IndustryClassificationPipeline
            
            # Initialize pipeline
            pipeline = IndustryClassificationPipeline()
            
            # Get options
            tables = industry_options.get('tables') if industry_options else None
            batch_size = industry_options.get('batch_size', 50) if industry_options else 50
            process_all = industry_options.get('process_all', False) if industry_options else False
            
            if process_all:
                # Process all pending articles in batches
                logger.info(f"Processing all pending articles in batches of {batch_size}")
                results = pipeline.process_all_pending(batch_size)
                total_processed = sum(results.values())
                
            elif tables:
                # Process specific tables
                logger.info(f"Processing specific tables: {tables}")
                total_processed = 0
                for table_name in tables:
                    processed = pipeline.process_specific_table(table_name, batch_size)
                    total_processed += processed
                    
            else:
                # Process all tables in a single batch
                logger.info("Processing all tables for industry classification")
                results = pipeline.process_all_tables(batch_size)
                total_processed = sum(results.values())
            
            # Close connections
            pipeline.close_connections()
            
            phase_time = time.time() - phase_start
            self.industry_results = {
                'status': 'success',
                'duration': phase_time,
                'articles_processed': total_processed
            }
            
            logger.info(f"Industry classification phase completed in {phase_time/60:.1f} minutes")
            
        except Exception as e:
            phase_time = time.time() - phase_start
            self.industry_results = {
                'status': 'error',
                'duration': phase_time,
                'error': str(e)
            }
            logger.error(f"Industry classification phase failed: {e}")
            raise
    
    def run_full_pipeline(self, options: Dict[str, Any] = None):
        """
        Execute complete pipeline: Crawling -> Summarization -> Sentiment Analysis -> Timeseries Prediction -> Industry Classification
        
        Args:
            options: Pipeline execution options
        """
        self.start_time = time.time()
        
        logger.info("\n" + "="*20)
        logger.info("STARTING SPA VIP FULL PIPELINE")
        logger.info("="*20)
        logger.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Phase 1: Crawling
            crawl_options = options.get('crawl', {}) if options else {}
            self.run_crawling_phase(crawl_options)
            
            # Wait between phases
            logger.info("Waiting 10 seconds between phases...")
            time.sleep(10)
            
            # Phase 2: Summarization
            summarization_options = options.get('summarization', {}) if options else {}
            self.run_summarization_phase(summarization_options)
            
            # Wait between phases
            logger.info("Waiting 10 seconds between phases...")
            time.sleep(10)
            
            # Phase 3: Sentiment Analysis
            sentiment_options = options.get('sentiment', {}) if options else {}
            self.run_sentiment_phase(sentiment_options)
            
            # Wait between phases
            logger.info("Waiting 10 seconds between phases...")
            time.sleep(10)
            
            # Phase 4: Timeseries Prediction
            timeseries_options = options.get('timeseries', {}) if options else {}
            self.run_timeseries_phase(timeseries_options)
            
            # Wait between phases
            logger.info("Waiting 10 seconds between phases...")
            time.sleep(10)
            
            # Phase 5: Industry Classification
            industry_options = options.get('industry', {}) if options else {}
            self.run_industry_phase(industry_options)
            
            # Final summary
            self._print_pipeline_summary()
            
        except KeyboardInterrupt:
            logger.warning("Pipeline interrupted by user")
            self._print_pipeline_summary()
        except Exception as e:
            logger.error(f"Pipeline failed with error: {e}")
            self._print_pipeline_summary()
            raise
    
    def _print_pipeline_summary(self):
        """Print comprehensive pipeline summary"""
        total_time = time.time() - self.start_time if self.start_time else 0
        
        logger.info("\n" + "="*80)
        logger.info("PIPELINE EXECUTION SUMMARY")
        logger.info("="*80)
        logger.info(f"Total execution time: {total_time/60:.1f} minutes")
        logger.info("")
        
        # Crawling results
        if self.crawl_results:
            crawl_status = "SUCCESS" if self.crawl_results['status'] == 'success' else "FAILED"
            crawl_time = self.crawl_results['duration'] / 60
            logger.info(f"CRAWLING PHASE: {crawl_status} ({crawl_time:.1f} min)")
            
            if self.crawl_results['status'] == 'success' and 'crawlers_status' in self.crawl_results:
                successful_crawlers = sum(1 for status in self.crawl_results['crawlers_status'].values() 
                                        if status['status'] == 'success')
                total_crawlers = len(self.crawl_results['crawlers_status'])
                logger.info(f"   Successful crawlers: {successful_crawlers}/{total_crawlers}")
        
        # Summarization results
        if self.summarization_results:
            summ_status = "SUCCESS" if self.summarization_results['status'] == 'success' else "FAILED"
            summ_time = self.summarization_results['duration'] / 60
            logger.info(f"SUMMARIZATION PHASE: {summ_status} ({summ_time:.1f} min)")
            
            if self.summarization_results['status'] == 'success':
                articles_processed = self.summarization_results.get('articles_processed', 0)
                logger.info(f"   Articles processed: {articles_processed}")
        
        # Sentiment results
        if self.sentiment_results:
            sent_status = "SUCCESS" if self.sentiment_results['status'] == 'success' else "FAILED"
            sent_time = self.sentiment_results['duration'] / 60
            logger.info(f"SENTIMENT PHASE: {sent_status} ({sent_time:.1f} min)")
            
            if self.sentiment_results['status'] == 'success':
                dates_processed = self.sentiment_results.get('dates_processed', 0)
                logger.info(f"   Dates processed: {dates_processed}")
        
        # Timeseries results
        if self.timeseries_results:
            ts_status = "SUCCESS" if self.timeseries_results['status'] == 'success' else "FAILED"
            ts_time = self.timeseries_results['duration'] / 60
            logger.info(f"TIMESERIES PHASE: {ts_status} ({ts_time:.1f} min)")
            
            if self.timeseries_results['status'] == 'success':
                predictions_made = self.timeseries_results.get('predictions_made', 0)
                total_stocks = self.timeseries_results.get('total_stocks', 0)
                success_rate = self.timeseries_results.get('success_rate', 0)
                logger.info(f"   Predictions: {predictions_made}/{total_stocks} ({success_rate:.1f}%)")
        
        # Industry results
        if self.industry_results:
            ind_status = "SUCCESS" if self.industry_results['status'] == 'success' else "FAILED"
            ind_time = self.industry_results['duration'] / 60
            logger.info(f"INDUSTRY PHASE: {ind_status} ({ind_time:.1f} min)")
            
            if self.industry_results['status'] == 'success':
                articles_processed = self.industry_results.get('articles_processed', 0)
                logger.info(f"   Articles classified: {articles_processed}")
        
        logger.info("")
        logger.info("FINAL STATUS:")
        self.show_system_status()
        
        logger.info("\nPIPELINE EXECUTION COMPLETED!")
        logger.info("="*80)

def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(
        description='SPA VIP - Integrated News Processing System (Runs --full by default)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                        # Run complete pipeline (DEFAULT)
  python main.py --full                 # Run complete pipeline (explicit)
  python main.py --crawl-only           # Only crawling phase
  python main.py --summarize-only       # Only summarization phase
  python main.py --status               # Show system status only
  python main.py --full --crawl-single fpt # Full pipeline with single crawler
  
  # Map-Reduce Summarization Examples:
  python main.py --analyze-texts        # Analyze database text lengths
  python main.py --summarize-only --no-map-reduce  # Disable Map-Reduce
  python main.py --full --no-map-reduce # Full pipeline without Map-Reduce
        """
    )
    
    # Pipeline modes
    parser.add_argument('--full', action='store_true', 
                       help='Run complete pipeline (crawl + summarization)')
    parser.add_argument('--crawl-only', action='store_true',
                       help='Run only crawling phase')
    parser.add_argument('--summarize-only', action='store_true',
                       help='Run only summarization phase')
    parser.add_argument('--sentiment-only', action='store_true',
                       help='Run only sentiment analysis phase')
    parser.add_argument('--timeseries-only', action='store_true',
                       help='Run only timeseries prediction phase')
    parser.add_argument('--industry-only', action='store_true',
                       help='Run only industry classification phase')
    parser.add_argument('--status', action='store_true',
                       help='Show current system status')
    
    # Crawling options
    parser.add_argument('--crawl-single', choices=['fireant_fpt', 'fireant_gas', 'fireant_imp', 'fireant_vcb', 
                       'cafef_keyword', 'cafef_general', 'chungta', 'stock_price',
                       'markettimes_fpt', 'markettimes_gas', 'markettimes_imp', 'markettimes_vcb', 
                       'markettimes_general', 'markettimes_all',
                       'dddn_fpt', 'dddn_gas', 'dddn_imp', 'dddn_vcb', 'dddn_general', 'dddn_all',
                       'imp_news', 'imp_all', 'petrotimes_gas', 'petrotimes_all'],
                       help='Run single crawler only')
    
    # Summarization options
    parser.add_argument('--summ-table', choices=['General_News', 'FPT_News', 'GAS_News', 
                       'IMP_News', 'VCB_News'],
                       help='Process specific table only')
    parser.add_argument('--summ-priority', action='store_true',
                       help='Process tables by priority (default)')
    
    # Map-Reduce Summarization options
    parser.add_argument('--no-map-reduce', action='store_true',
                       help='Disable Map-Reduce for long texts (use truncation)')
    parser.add_argument('--analyze-texts', action='store_true',
                       help='Analyze text lengths in database to show Map-Reduce benefits')
    
    # Sentiment options
    parser.add_argument('--sent-tables', nargs='+', 
                       choices=['General_News', 'FPT_News', 'GAS_News', 'IMP_News', 'VCB_News'],
                       help='Process specific tables for sentiment analysis')
    parser.add_argument('--no-stock-update', action='store_true',
                       help='Skip updating stock tables with sentiment statistics')
    parser.add_argument('--recalculate-all-stock', action='store_true',
                       help='Recalculate sentiment statistics for all dates in stock tables')
    parser.add_argument('--optimized-update', action='store_true',
                       help='Use optimized sentiment update (only affected trading days)')
    parser.add_argument('--30day-aggregate', action='store_true',
                       help='Use 30-day sentiment aggregation (weekend/holiday aggregation)')
    
    # Timeseries options
    parser.add_argument('--ts-stocks', nargs='+',
                       choices=['FPT', 'GAS', 'IMP', 'VCB'],
                       help='Predict specific stock codes only')
    
    # Industry options
    parser.add_argument('--ind-tables', nargs='+',
                       choices=['General_News'],
                       help='Process General_News table for industry classification (default: General_News)')
    parser.add_argument('--ind-batch-size', type=int, default=50,
                       help='Batch size for industry classification (default: 50)')
    parser.add_argument('--ind-process-all', action='store_true',
                       help='Process ALL pending industry classifications in batches')
    
    args = parser.parse_args()
    
    # Initialize pipeline
    pipeline = SPAVIPPipeline()
    
    try:
        if args.status:
            # Show system status only
            pipeline.show_system_status()
            
        elif args.crawl_only:
            # Run only crawling phase
            crawl_options = {}
            if args.crawl_single:
                crawl_options['single'] = args.crawl_single
            pipeline.run_crawling_phase(crawl_options)
            
        elif args.summarize_only:
            # Run only summarization phase
            summarization_options = {}
            if args.summ_table:
                summarization_options['table'] = args.summ_table
            elif args.summ_priority:
                summarization_options['priority'] = True
            
            # Map-Reduce options
            if args.no_map_reduce:
                summarization_options['use_map_reduce'] = False
            if args.analyze_texts:
                summarization_options['analyze_texts'] = True
            
            pipeline.run_summarization_phase(summarization_options)
            
        elif args.sentiment_only:
            # Run only sentiment analysis phase
            sentiment_options = {}
            if args.sent_tables:
                sentiment_options['tables'] = args.sent_tables
            if args.no_stock_update:
                sentiment_options['update_stock'] = False
            if args.recalculate_all_stock:
                sentiment_options['recalculate_all_stock'] = True
            if args.optimized_update:
                sentiment_options['optimized_update'] = True
            if args.__dict__.get('30day_aggregate'):  # Access hyphenated argument
                sentiment_options['30day_aggregate'] = True
            pipeline.run_sentiment_phase(sentiment_options)
            
        elif args.timeseries_only:
            # Run only timeseries prediction phase
            timeseries_options = {}
            if args.ts_stocks:
                timeseries_options['stock_codes'] = args.ts_stocks
            pipeline.run_timeseries_phase(timeseries_options)
            
        elif args.industry_only:
            # Run only industry classification phase
            industry_options = {}
            if args.ind_tables:
                industry_options['tables'] = args.ind_tables
            if args.ind_batch_size:
                industry_options['batch_size'] = args.ind_batch_size
            if args.ind_process_all:
                industry_options['process_all'] = True
            pipeline.run_industry_phase(industry_options)
            
        elif args.full:
            # Run full pipeline
            options = {}
            
            # Crawl options
            if args.crawl_single:
                options['crawl'] = {'single': args.crawl_single}
            
            # Summarization options with Map-Reduce support
            summ_opts = {}
            if args.summ_table:
                summ_opts['table'] = args.summ_table
            elif args.summ_priority:
                summ_opts['priority'] = True
            
            # Map-Reduce options
            if args.no_map_reduce:
                summ_opts['use_map_reduce'] = False
            if args.analyze_texts:
                summ_opts['analyze_texts'] = True
                
            if summ_opts:
                options['summarization'] = summ_opts
            
            # Sentiment options
            sent_opts = {}
            if args.sent_tables:
                sent_opts['tables'] = args.sent_tables
            if args.no_stock_update:
                sent_opts['update_stock'] = False
            if args.recalculate_all_stock:
                sent_opts['recalculate_all_stock'] = True
            if args.optimized_update:
                sent_opts['optimized_update'] = True
            if sent_opts:
                options['sentiment'] = sent_opts
            
            # Industry options
            ind_opts = {}
            if args.ind_tables:
                ind_opts['tables'] = args.ind_tables
            if args.ind_batch_size:
                ind_opts['batch_size'] = args.ind_batch_size
            if ind_opts:
                options['industry'] = ind_opts
                
            pipeline.run_full_pipeline(options)
            
        else:
            # Default behavior: run full pipeline automatically
            print("\n" + "="*80)
            print("SPA VIP - RUNNING FULL PIPELINE (DEFAULT)")
            print("="*80)
            print("No arguments provided - Running complete pipeline automatically")
            print("To see all available commands, use: python main.py --help")
            print("="*80)
            
            # Run full pipeline with default options
            pipeline.run_full_pipeline({})
            
            # Simple completion message
            print("\nPIPELINE EXECUTION COMPLETED!")
            print("="*80)
            
    except KeyboardInterrupt:
        logger.info("\nOperation interrupted by user")
    except Exception as e:
        logger.error(f"System error: {e}")
        raise

if __name__ == "__main__":
    main()
