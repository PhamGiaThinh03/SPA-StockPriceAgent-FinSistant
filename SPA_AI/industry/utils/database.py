import logging
import os
import sys

# Add parent directory to path for centralized database import
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, parent_dir)

# Import centralized database system
from database import SupabaseManager, DatabaseConfig

class PostgresConnector:
    """
    Database connector adapted for SPA VIP centralized database system
    Now uses SupabaseManager instead of direct PostgreSQL connection
    """
    
    def __init__(self):
        try:
            self.db_manager = SupabaseManager()
            self.config = DatabaseConfig()
            
            # Test connection
            if self.db_manager.test_connection():
                logging.info("✅ Supabase connection established successfully for Industry module")
            else:
                raise Exception("Database connection test failed")
                
        except Exception as e:
            logging.error(f"❌ Failed to initialize database connection: {str(e)}")
            raise

    def fetch_unprocessed_rows(self, limit=100, table_name=None):
        """
        Get rows where industry classification is missing (only General_News)
        
        Args:
            limit: Maximum number of rows to fetch
            table_name: Specific table to process (should be General_News only)
            
        Returns:
            List of articles needing industry classification
        """
        try:
            all_articles = []
            # Force only General_News table for industry classification
            tables_to_query = ['General_News'] if not table_name else [table_name] if table_name == 'General_News' else []
            
            if not tables_to_query:
                logging.warning("⚠️ Industry classification only works on General_News table")
                return []
            
            for table in tables_to_query:
                logging.debug(f"🔍 Querying table: {table}")
                
                # Get articles with ai_summary but without industry classification
                result = self.db_manager.client.table(table)\
                    .select("id, title, content, ai_summary")\
                    .filter("ai_summary", "not.is", "null")\
                    .neq("ai_summary", "")\
                    .or_("industry.is.null,industry.eq.")\
                    .order("id", desc=True)\
                    .limit(limit)\
                    .execute()
                
                for article in result.data:
                    # Ensure ai_summary exists and is meaningful
                    if article.get("ai_summary") and len(article.get("ai_summary", "").strip()) > 10:
                        article["table_name"] = table
                        all_articles.append(article)
                
                logging.debug(f"Found {len(result.data)} unprocessed articles in {table}")
            
            logging.info(f"📊 Total unprocessed articles found: {len(all_articles)}")
            return all_articles[:limit]
            
        except Exception as e:
            logging.error(f"❌ Error fetching unprocessed rows: {str(e)}")
            return []

    def update_row(self, article_id, updates, table_name):
        """
        Update article with industry classification
        
        Args:
            article_id: Article ID to update
            updates: Dictionary of updates (should contain 'industry')
            table_name: Table containing the article
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not updates or not article_id or not table_name:
                raise ValueError("Invalid update data, article ID, or table name")
            
            # Update the article
            response = self.db_manager.client.table(table_name)\
                .update(updates)\
                .eq("id", article_id)\
                .execute()
            
            if response.data:
                logging.debug(f"✅ Updated article {article_id} in {table_name} with {updates}")
                return True
            else:
                logging.warning(f"⚠️ No rows updated for article {article_id} in {table_name}")
                return False
                
        except Exception as e:
            logging.error(f"❌ Error updating article {article_id}: {str(e)}")
            return False

    def health_check(self):
        """Check database connection health"""
        try:
            return self.db_manager.test_connection()
        except Exception as e:
            logging.error(f"❌ Health check failed: {str(e)}")
            return False
    
    def get_industry_stats(self):
        """Get industry classification statistics (only General_News)"""
        try:
            stats = {}
            
            # Only process General_News table
            table = 'General_News'
            try:
                # Count total articles with summaries
                total_result = self.db_manager.client.table(table)\
                    .select("*", count="exact")\
                    .filter("ai_summary", "not.is", "null")\
                    .neq("ai_summary", "")\
                    .execute()
                
                # Count articles with industry classification
                classified_result = self.db_manager.client.table(table)\
                    .select("*", count="exact")\
                    .filter("industry", "not.is", "null")\
                    .neq("industry", "")\
                    .filter("ai_summary", "not.is", "null")\
                    .neq("ai_summary", "")\
                    .execute()
                
                total_count = total_result.count or 0
                classified_count = classified_result.count or 0
                
                stats[table] = {
                    "total_with_summary": total_count,
                    "classified": classified_count,
                    "pending": max(0, total_count - classified_count),
                    "completion_rate": (classified_count / total_count * 100) if total_count > 0 else 100
                }
                
            except Exception as e:
                logging.error(f"❌ Error getting stats for {table}: {str(e)}")
                stats[table] = {"total_with_summary": 0, "classified": 0, "pending": 0, "completion_rate": 0}
            
            return stats
            
        except Exception as e:
            logging.error(f"❌ Error getting industry stats: {str(e)}")
            return {}
    
    def close_connections(self):
        """Close database connections"""
        try:
            self.db_manager.close_connections()
            logging.info("🔒 Database connections closed")
        except Exception as e:
            logging.error(f"❌ Error closing connections: {str(e)}")

# Legacy alias for backward compatibility
class DatabaseConnector(PostgresConnector):
    pass