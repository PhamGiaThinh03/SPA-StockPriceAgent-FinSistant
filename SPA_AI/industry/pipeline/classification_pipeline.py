import logging
import time
from typing import Dict, Any, List, Optional

from industry.models.phobert_classifier import PhoBERTClassifier
from industry.utils.database import PostgresConnector
from industry.config import Config

class IndustryClassificationPipeline:
    """
    Industry Classification Pipeline for SPA VIP system
    Classifies news articles into industry categories using PhoBERT
    """
    
    def __init__(self):
        """Initialize the industry classification pipeline"""
        try:
            logging.info("🏭 Initializing Industry Classification Pipeline...")
            
            # Initialize industry classifier
            self.industry_classifier = PhoBERTClassifier(
                Config.MODEL_INDUSTRY_PATH,
                Config.INDUSTRY_LABELS
            )
            
            # Initialize database connector
            self.db = PostgresConnector()
            
            # Test database connection
            if not self.db.health_check():
                raise Exception("Database health check failed")
            
            logging.info("✅ Industry Classification Pipeline initialized successfully")
            
        except Exception as e:
            logging.critical(f"❌ Failed to initialize Industry Classification Pipeline: {str(e)}")
            raise

    def process_batch(self, batch_size: int = 50, table_name: str = None) -> int:
        """
        Process a batch of articles for industry classification
        
        Args:
            batch_size: Number of articles to process in one batch
            table_name: Specific table to process (optional)
            
        Returns:
            int: Number of articles successfully processed
        """
        try:
            # Fetch unprocessed articles
            articles = self.db.fetch_unprocessed_rows(limit=batch_size, table_name=table_name)
            
            if not articles:
                logging.info("📭 No unprocessed articles found for industry classification")
                return 0
            
            processed_count = 0
            
            for article in articles:
                try:
                    # Get article content for classification
                    summary = article.get(Config.SUMMARY_COLUMN, '')
                    
                    # Only use ai_summary for industry classification
                    text_to_classify = summary
                    
                    if not text_to_classify or len(text_to_classify.strip()) < 10:
                        logging.warning(f"⚠️ No ai_summary available for classification in article {article.get('id')}")
                        continue
                    
                    # Classify industry
                    industry, confidence_scores = self.industry_classifier.predict(text_to_classify)
                    
                    # Handle confidence scores safely
                    try:
                        if confidence_scores is not None and len(confidence_scores) > 0:
                            max_confidence = float(max(confidence_scores))
                        else:
                            max_confidence = 0.0
                    except (ValueError, TypeError):
                        max_confidence = 0.0
                    
                    # Update article with industry classification
                    updates = {
                        Config.INDUSTRY_COLUMN: industry
                    }
                    
                    success = self.db.update_row(
                        article['id'], 
                        updates, 
                        article['table_name']
                    )
                    
                    if success:
                        processed_count += 1
                        logging.info(f"✅ Classified article {article['id']}: {industry} (confidence: {max_confidence:.3f})")
                    else:
                        logging.error(f"❌ Failed to update article {article['id']}")
                        
                except Exception as e:
                    logging.error(f"❌ Error processing article {article.get('id', 'unknown')}: {str(e)}")
                    continue
            
            logging.info(f"📊 Successfully processed {processed_count}/{len(articles)} articles")
            return processed_count
            
        except Exception as e:
            logging.error(f"❌ Batch processing failed: {str(e)}")
            return 0

    def process_specific_table(self, table_name: str, batch_size: int = 50) -> int:
        """
        Process articles from a specific table
        
        Args:
            table_name: Name of the table to process
            batch_size: Number of articles to process in one batch
            
        Returns:
            int: Number of articles successfully processed
        """
        logging.info(f"🎯 Processing specific table: {table_name}")
        return self.process_batch(batch_size=batch_size, table_name=table_name)

    def process_all_tables(self, batch_size: int = 50) -> Dict[str, int]:
        """
        Process articles from General_News table only
        
        Args:
            batch_size: Number of articles to process per batch
            
        Returns:
            Dict[str, int]: Processing results for General_News
        """
        logging.info("🌐 Processing General_News table for industry classification")
        
        results = {}
        
        # Only process General_News table
        table_name = "General_News"
        logging.info(f"📋 Processing table: {table_name}")
        processed = self.process_specific_table(table_name, batch_size)
        results[table_name] = processed
        
        total_processed = sum(results.values())
        logging.info(f"🎉 Total articles processed: {total_processed}")
        
        return results

    def process_all_pending(self, batch_size: int = 10) -> Dict[str, int]:
        """
        Process ALL pending articles in batches until no more articles need classification
        
        Args:
            batch_size: Number of articles to process per batch
            
        Returns:
            Dict[str, int]: Total processing results
        """
        logging.info("🔄 Processing ALL pending industry classifications in batches...")
        
        # Get initial count of pending articles
        stats = self.db.get_industry_stats()
        general_news_stats = stats.get('General_News', {})
        total_pending = general_news_stats.get('pending', 0)
        
        if total_pending == 0:
            logging.info("✅ No pending articles found for industry classification")
            return {'General_News': 0}
        
        total_batches = (total_pending + batch_size - 1) // batch_size  # Ceiling division
        logging.info(f"📊 Found {total_pending} pending articles")
        logging.info(f"🎯 Will process in {total_batches} batches of {batch_size} articles each")
        
        results = {'General_News': 0}
        batch_number = 1
        
        while True:
            logging.info(f"\n🔄 Processing Batch {batch_number}/{total_batches}")
            logging.info("-" * 50)
            
            # Process one batch
            processed = self.process_specific_table('General_News', batch_size)
            
            if processed == 0:
                logging.info("✅ No more articles to process. All pending classifications completed!")
                break
            
            results['General_News'] += processed
            batch_number += 1
            
            # Brief pause between batches to avoid overwhelming the system
            if processed == batch_size:  # Full batch processed
                logging.info(f"⏸️ Brief pause before next batch...")
                time.sleep(2)
            
            # Safety check to prevent infinite loops
            if batch_number > total_batches + 5:  # Allow some buffer
                logging.warning("⚠️ Maximum batch limit reached. Stopping to prevent infinite loop.")
                break
        
        total_processed = results['General_News']
        logging.info(f"\n🎉 BATCH PROCESSING COMPLETED!")
        logging.info(f"📊 Total articles processed: {total_processed}")
        logging.info(f"🎯 Batches completed: {batch_number - 1}")
        
        return results

    def run_continuous(self, batch_size: int = 50, interval: int = 60, table_name: str = None):
        """
        Run continuous industry classification
        
        Args:
            batch_size: Number of articles to process in each batch
            interval: Seconds to wait between processing cycles
            table_name: Specific table to monitor (optional)
        """
        logging.info(f"🔄 Starting continuous industry classification")
        logging.info(f"📊 Configuration: batch_size={batch_size}, interval={interval}s")
        
        if table_name:
            logging.info(f"🎯 Monitoring specific table: {table_name}")
        else:
            logging.info("🌐 Monitoring all news tables")
        
        while True:
            try:
                processed = self.process_batch(batch_size=batch_size, table_name=table_name)
                
                if processed == 0:
                    logging.info(f"😴 No articles to process. Waiting {interval} seconds...")
                    time.sleep(interval)
                else:
                    logging.info(f"⏸️ Processed {processed} articles. Brief pause before next batch...")
                    time.sleep(5)  # Brief pause between successful batches
                    
            except KeyboardInterrupt:
                logging.info("⚠️ Received keyboard interrupt. Shutting down...")
                break
            except Exception as e:
                logging.error(f"❌ Unexpected error in continuous processing: {str(e)}")
                logging.info(f"🔄 Retrying in {interval} seconds...")
                time.sleep(interval)

    def get_system_status(self) -> Dict[str, Any]:
        """
        Get current system status and statistics
        
        Returns:
            Dict containing system status information
        """
        try:
            # Get database health
            db_healthy = self.db.health_check()
            
            # Get industry classification statistics
            stats = self.db.get_industry_stats()
            
            # Calculate totals
            total_with_summary = sum(table_stats['total_with_summary'] for table_stats in stats.values())
            total_classified = sum(table_stats['classified'] for table_stats in stats.values())
            total_pending = sum(table_stats['pending'] for table_stats in stats.values())
            
            overall_completion = (total_classified / total_with_summary * 100) if total_with_summary > 0 else 100
            
            return {
                'status': 'healthy' if db_healthy else 'unhealthy',
                'database_connected': db_healthy,
                'total_articles_with_summary': total_with_summary,
                'total_classified': total_classified,
                'total_pending': total_pending,
                'overall_completion_rate': round(overall_completion, 1),
                'table_breakdown': stats,
                'industry_labels': Config.INDUSTRY_LABELS
            }
            
        except Exception as e:
            logging.error(f"❌ Error getting system status: {str(e)}")
            return {'status': 'error', 'error': str(e)}

    def close_connections(self):
        """Close database connections"""
        try:
            self.db.close_connections()
            logging.info("🔒 Industry Classification Pipeline connections closed")
        except Exception as e:
            logging.error(f"❌ Error closing connections: {str(e)}")

# Legacy alias for backward compatibility
ClassificationPipeline = IndustryClassificationPipeline
