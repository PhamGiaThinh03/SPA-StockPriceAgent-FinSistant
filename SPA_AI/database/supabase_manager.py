"""
Supabase Manager
Centralized database operations for SPA VIP system
"""

import sys
from supabase import create_client, Client
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

from .config import DatabaseConfig
from .schemas import NewsSchema, StockSchema, validate_article_data, validate_stock_data

logger = logging.getLogger(__name__)

class SupabaseManager:
    """Centralized Supabase database manager"""
    
    def __init__(self):
        """Initialize Supabase client"""
        self.config = DatabaseConfig()
        self.config.validate_config()
        
        self.client = create_client(
            self.config.SUPABASE_URL, 
            self.config.SUPABASE_KEY
        )
        
        logger.info("Supabase client initialized successfully")
    
    def get_client(self) -> Client:
        """Get Supabase client instance"""
        return self.client
    
    def get_supabase_client(self) -> Client:
        """Get Supabase client instance (alias for backward compatibility)"""
        return self.client
    
    # ============ NEWS OPERATIONS ============
    
    def insert_article(self, table_name: str, article_data: Dict[str, Any]) -> bool:
        """
        Insert article with validation and duplicate check
        
        Args:
            table_name: Target table name
            article_data: Article data dictionary
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Validate data
            if not validate_article_data(article_data):
                # DEBUG: See specific validation issues
                issues = []
                required_fields = ["title", "content", "link", "date"]
                for field in required_fields:
                    if not article_data.get(field):
                        issues.append(f"Missing {field}")
                if len(article_data.get("content", "").strip()) < 50:
                    issues.append(f"Content too short ({len(article_data.get('content', '').strip())} chars)")
                logger.warning(f"Invalid article data - {', '.join(issues)}: {article_data.get('title', '')[:50]}...")
                return False
            
            # Check for duplicates
            link = article_data.get("link", "")
            if link and self.article_exists(table_name, link):
                logger.info(f"Article already exists: {article_data.get('title', '')[:50]}...")
                return False
            
            # Create schema object
            article = NewsSchema.from_crawler_data(article_data)
            if not article.validate():
                logger.warning(f"Article validation failed: {article.title[:50]}...")
                return False
            
            # Insert to database
            is_general_news = table_name.lower() == "general_news"
            result = self.client.table(table_name).upsert(
                article.to_dict(include_industry=is_general_news),
                on_conflict="link"
            ).execute()
            
            if result.data:
                logger.info(f"Inserted article: {article.title[:50]}...")
                return True
            else:
                logger.error(f"Failed to insert article: {article.title[:50]}...")
                return False
                
        except Exception as e:
            logger.error(f"Database error inserting article: {e}")
            return False
    
    def article_exists(self, table_name: str, link: str) -> bool:
        """Check if article already exists"""
        try:
            result = self.client.table(table_name)\
                .select("link")\
                .eq("link", link)\
                .execute()
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"Error checking article existence: {e}")
            return False
    
    def fetch_unsummarized_articles(self, table_name: str = None, limit: int = 100) -> List[Dict]:
        """
        Fetch articles without AI summary
        
        Args:
            table_name: Specific table or None for all tables
            limit: Maximum number of articles
            
        Returns:
            List of articles
        """
        try:
            all_articles = []
            tables_to_query = [table_name] if table_name else self.config.get_all_news_tables()
            
            for table in tables_to_query:
                logger.info(f"Querying table: {table}")
                
                query = self.client.table(table)\
                    .select("id, title, content")\
                    .or_("ai_summary.is.null,ai_summary.eq.")\
                    .neq("content", "")\
                    .order("id", desc=True)\
                    .limit(limit)
                
                result = query.execute()
                
                for article in result.data:
                    if article.get("content") and len(article.get("content", "").strip()) > 50:
                        article["table_name"] = table
                        all_articles.append(article)
                
                logger.info(f"Found {len(result.data)} unsummarized articles in {table}")
            
            logger.info(f"Total unsummarized articles found: {len(all_articles)}")
            return all_articles[:limit]
            
        except Exception as e:
            logger.error(f"Error fetching unsummarized articles: {e}")
            return []
    
    def update_article_summary(self, article_id: str, summary: str, table_name: str) -> bool:
        """Update article with AI summary"""
        try:
            response = self.client.table(table_name)\
                .update({"ai_summary": summary})\
                .eq("id", article_id)\
                .execute()
            
            if response.data:
                logger.info(f"Updated summary for article {article_id} in {table_name}")
                return True
            else:
                logger.warning(f"No rows updated for article {article_id} in {table_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating summary for article {article_id}: {e}")
            return False
    
    def update_article_industry(self, article_id: str, industry: str, table_name: str) -> bool:
        """Update article with industry classification"""
        try:
            response = self.client.table(table_name)\
                .update({"industry": industry})\
                .eq("id", article_id)\
                .execute()
            
            if response.data:
                logger.info(f"Updated industry for article {article_id} in {table_name}: {industry}")
                return True
            else:
                logger.warning(f"No rows updated for article {article_id} in {table_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating industry for article {article_id}: {e}")
            return False
    
    def fetch_unclassified_articles(self, table_name: str = None, limit: int = 100) -> List[Dict]:
        """
        Fetch articles with summaries but without industry classification (General_News only)
        
        Args:
            table_name: Should be General_News or None (defaults to General_News)
            limit: Maximum number of articles
            
        Returns:
            List of articles needing industry classification
        """
        try:
            all_articles = []
            # Industry classification only works on General_News
            tables_to_query = ['General_News'] if not table_name else [table_name] if table_name == 'General_News' else []
            
            if not tables_to_query:
                logger.warning("Industry classification only works on General_News table")
                return []
            
            for table in tables_to_query:
                logger.info(f"Querying table for industry classification: {table}")
                
                query = self.client.table(table)\
                    .select("id, title, content, ai_summary")\
                    .filter("ai_summary", "not.is", "null")\
                    .neq("ai_summary", "")\
                    .or_("industry.is.null,industry.eq.")\
                    .order("id", desc=True)\
                    .limit(limit)
                
                result = query.execute()
                
                for article in result.data:
                    if article.get("ai_summary") and len(article.get("ai_summary", "").strip()) > 10:
                        article["table_name"] = table
                        all_articles.append(article)
                
                logger.info(f"Found {len(result.data)} unclassified articles in {table}")
            
            logger.info(f"Total unclassified articles found: {len(all_articles)}")
            return all_articles[:limit]
            
        except Exception as e:
            logger.error(f"Error fetching unclassified articles: {e}")
            return []
    
    # ============ STOCK OPERATIONS ============
    
    def insert_stock_data(self, table_name: str, stock_data: Dict[str, Any]) -> bool:
        """Insert stock price data"""
        try:
            # Validate data
            if not validate_stock_data(stock_data):
                logger.warning(f"Invalid stock data for {table_name}")
                return False
            
            # Create schema object
            stock = StockSchema.from_crawler_data(stock_data)
            if not stock.validate():
                logger.warning(f"Stock validation failed for {table_name}")
                return False
            
            # Insert to database
            result = self.client.table(table_name).upsert(
                stock.to_dict(),
                on_conflict="date"
            ).execute()
            
            if result.data:
                logger.info(f"Inserted stock data for {table_name} - {stock.date}")
                return True
            else:
                logger.error(f"Failed to insert stock data for {table_name}")
                return False
                
        except Exception as e:
            logger.error(f"Database error inserting stock data: {e}")
            return False
    
    # ============ STATISTICS ============
    
    def get_table_stats(self) -> Dict[str, Dict]:
        """Get comprehensive statistics for all news tables"""
        stats = {}
        
        for table in self.config.get_all_news_tables():
            try:
                # Count total articles with valid content
                total_result = self.client.table(table)\
                    .select("*", count="exact")\
                    .neq("content", "")\
                    .execute()
                
                # Count articles with summaries
                summarized_result = self.client.table(table)\
                    .select("*", count="exact")\
                    .filter("ai_summary", "not.is", "null")\
                    .neq("ai_summary", "")\
                    .neq("content", "")\
                    .execute()
                
                # Count articles with industry classification (only for General_News)
                if table == 'General_News':
                    classified_result = self.client.table(table)\
                        .select("*", count="exact")\
                        .filter("industry", "not.is", "null")\
                        .neq("industry", "")\
                        .filter("ai_summary", "not.is", "null")\
                        .neq("ai_summary", "")\
                        .execute()
                    classified_count = classified_result.count or 0
                else:
                    classified_count = 0  # Other tables don't have industry classification
                
                total_count = total_result.count or 0
                summarized_count = summarized_result.count or 0
                
                stats[table] = {
                    "total": total_count,
                    "summarized": summarized_count,
                    "unsummarized": max(0, total_count - summarized_count),
                    "completion_rate": (summarized_count / total_count * 100) if total_count > 0 else 100,
                    "classified": classified_count,
                    "unclassified": max(0, summarized_count - classified_count) if table == 'General_News' else 0,
                    "classification_rate": (classified_count / summarized_count * 100) if summarized_count > 0 and table == 'General_News' else 0
                }
                
            except Exception as e:
                logger.error(f"Error getting stats for {table}: {e}")
                stats[table] = {
                    "total": 0, 
                    "summarized": 0, 
                    "unsummarized": 0, 
                    "completion_rate": 0,
                    "classified": 0,
                    "unclassified": 0,
                    "classification_rate": 0
                }
        
        return stats
    
    def get_table_count(self, table_name: str) -> int:
        """Get total count for a table"""
        try:
            result = self.client.table(table_name)\
                .select("*", count="exact")\
                .execute()
            return result.count or 0
        except Exception as e:
            logger.error(f"Error counting table {table_name}: {e}")
            return 0
    
    # ============ UTILITY METHODS ============
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            # Try to query a small sample from each news table
            for table in self.config.get_all_news_tables():
                result = self.client.table(table)\
                    .select("id")\
                    .limit(1)\
                    .execute()
                logger.info(f"Connection test passed for {table}")
            
            logger.info("All database connections working properly")
            return True
            
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def close_connection(self):
        """Close database connections (placeholder for compatibility)"""
        logger.info("Supabase connections are managed automatically")
    
    def close_connections(self):
        """Close database connections (alias for backward compatibility)"""
        self.close_connection()

# ============ FACTORY FUNCTIONS ============

def get_database_manager() -> SupabaseManager:
    """Factory function to create database manager"""
    return SupabaseManager()

def get_supabase_client() -> Client:
    """Factory function to get Supabase client"""
    manager = SupabaseManager()
    return manager.get_client()
