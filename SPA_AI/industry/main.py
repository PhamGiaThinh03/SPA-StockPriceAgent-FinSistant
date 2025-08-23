#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Industry Classification Module for SPA VIP
Integrated industry classification pipeline using PhoBERT

Author: SPA VIP Team
Date: August 5, 2025
"""

import torch
import logging
import argparse
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from transformers import logging as transformers_logging
from utils.database import PostgresConnector
from config import Config
import time
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
transformers_logging.set_verbosity_error()  # Reduce logging level from transformers

from pipeline.classification_pipeline import IndustryClassificationPipeline


def main_industry():
    """Main function for industry classification with CLI options"""
    parser = argparse.ArgumentParser(
        description='🏭 SPA VIP - Industry Classification System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --batch                   # Process one batch
  python main.py --process-all             # Process ALL pending articles in batches  
  python main.py --continuous              # Run continuously
  python main.py --table FPT_News          # Process specific table
  python main.py --status                  # Show system status
        """
    )
    
    # Processing modes
    parser.add_argument('--batch', action='store_true',
                       help='Process one batch and exit')
    parser.add_argument('--process-all', action='store_true',
                       help='Process ALL pending articles in batches until complete')
    parser.add_argument('--continuous', action='store_true',
                       help='Run continuous processing')
    parser.add_argument('--status', action='store_true',
                       help='Show system status only')
    
    # Processing options
    parser.add_argument('--table', choices=['General_News', 'FPT_News', 'GAS_News', 'IMP_News', 'VCB_News'],
                       help='Process specific table only')
    parser.add_argument('--batch-size', type=int, default=50,
                       help='Number of articles to process in one batch (default: 50)')
    parser.add_argument('--interval', type=int, default=60,
                       help='Interval between processing cycles in seconds (default: 60)')
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    try:
        pipeline = IndustryClassificationPipeline()
        
        if args.status:
            # Show status only
            status = pipeline.get_system_status()
            
            logger.info("\n" + "="*80)
            logger.info("🏭 INDUSTRY CLASSIFICATION SYSTEM STATUS")
            logger.info("="*80)
            
            logger.info(f"🔗 Database Status: {'✅ Connected' if status['database_connected'] else '❌ Disconnected'}")
            logger.info(f"📰 Articles with Summary: {status['total_articles_with_summary']:,}")
            logger.info(f"🏭 Industry Classified: {status['total_classified']:,}")
            logger.info(f"⏳ Pending Classification: {status['total_pending']:,}")
            logger.info(f"📈 Overall Completion: {status['overall_completion_rate']:.1f}%")
            logger.info("")
            
            logger.info("📋 TABLE BREAKDOWN:")
            logger.info("-" * 60)
            logger.info(f"{'Table':<15} {'Summary':<8} {'Classified':<10} {'Pending':<8} {'Rate':<8}")
            logger.info("-" * 60)
            
            for table_name, table_stats in status['table_breakdown'].items():
                completion_rate = table_stats['completion_rate']
                logger.info(f"{table_name:<15} {table_stats['total_with_summary']:<8} "
                           f"{table_stats['classified']:<10} {table_stats['pending']:<8} "
                           f"{completion_rate:.1f}%")
            
            logger.info("="*80)
            
        elif args.batch:
            # Process one batch
            if args.table:
                processed = pipeline.process_specific_table(args.table, args.batch_size)
            else:
                processed = pipeline.process_batch(args.batch_size)
            
            logger.info(f"✅ Batch processing completed. Processed {processed} articles.")
            
        elif args.process_all:
            # Process ALL pending articles in batches
            logger.info("🔄 Processing ALL pending industry classifications...")
            results = pipeline.process_all_pending(batch_size=args.batch_size)
            
            total_processed = sum(results.values())
            logger.info(f"✅ ALL processing completed. Total articles classified: {total_processed}")
            
        elif args.continuous:
            # Run continuous processing
            pipeline.run_continuous(
                batch_size=args.batch_size,
                interval=args.interval,
                table_name=args.table
            )
            
        else:
            # Default: process all tables once
            logger.info("🏭 Processing all tables for industry classification...")
            results = pipeline.process_all_tables(batch_size=args.batch_size)
            
            total_processed = sum(results.values())
            logger.info(f"✅ Processing completed. Total articles classified: {total_processed}")
            
            for table_name, count in results.items():
                logger.info(f"   📋 {table_name}: {count} articles")
        
        # Close connections
        pipeline.close_connections()
        
    except KeyboardInterrupt:
        logger.info("⚠️ Received keyboard interrupt. Shutting down...")
    except Exception as e:
        logging.critical(f"💥 Application failed: {str(e)}")
        raise


if __name__ == "__main__":
    main_industry()