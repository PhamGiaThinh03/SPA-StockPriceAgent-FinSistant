#!/usr/bin/env python3
"""
Database Connection Test
Test the centralized database system
"""

import sys
import os
import logging

# Add parent path to import database package
parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_path)

from database import SupabaseManager, DatabaseConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_database_connection():
    """Test all database functionality"""
    
    logger.info("TESTING DATABASE CONNECTION")
    logger.info("="*50)
    
    try:
        # Initialize database manager
        logger.info("1. Initializing database manager...")
        db_manager = SupabaseManager()
        logger.info("Database manager initialized")
        
        # Test configuration
        logger.info("2. Testing configuration...")
        config = DatabaseConfig()
        config.validate_config()
        logger.info("Configuration validated")
        
        # Test connection
        logger.info("3. Testing database connection...")
        if db_manager.test_connection():
            logger.info("Database connection successful")
        else:
            logger.error("Database connection failed")
            return False
        
        # Test table statistics
        logger.info("4. Testing table statistics...")
        stats = db_manager.get_table_stats()
        
        total_articles = sum(table_stats['total'] for table_stats in stats.values())
        total_summarized = sum(table_stats['summarized'] for table_stats in stats.values())
        total_pending = sum(table_stats['unsummarized'] for table_stats in stats.values())
        
        logger.info(f"Total articles: {total_articles}")
        logger.info(f"Summarized: {total_summarized}")
        logger.info(f"Pending: {total_pending}")
        
        logger.info("\nTable breakdown:")
        for table_name, table_stats in stats.items():
            logger.info(f"  {table_name}: {table_stats['summarized']}/{table_stats['total']} "
                       f"({table_stats['completion_rate']:.1f}%)")
        
        logger.info("\nALL TESTS PASSED!")
        logger.info("Database system is working correctly")
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_database_connection()
    sys.exit(0 if success else 1)
