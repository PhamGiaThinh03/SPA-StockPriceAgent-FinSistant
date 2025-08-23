"""
Database Configuration
Centralized configuration for all database operations
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class DatabaseConfig:
    """Centralized database configuration"""
    
    # Supabase Configuration
    SUPABASE_URL = os.getenv("SUPABASE_URL", "https://baenxyqklayjtlbmubxe.supabase.co")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_secret_4Mj3OwBW9VlbhVU6bVrfLA_1olLCYpp")
    
    # Table Names - News Tables
    NEWS_TABLES = {
        "general_news": "General_News",
        "fpt_news": "FPT_News", 
        "gas_news": "GAS_News",
        "imp_news": "IMP_News",
        "vcb_news": "VCB_News"
    }
    
    # Table Names - Stock Tables
    STOCK_TABLES = {
        "fpt_stock": "FPT_Stock",
        "gas_stock": "GAS_Stock", 
        "imp_stock": "IMP_Stock",
        "vcb_stock": "VCB_Stock"
    }
    
    # Stock Codes
    STOCK_CODES = ["FPT", "GAS", "IMP", "VCB"]
    
    # API URLs
    FIREANT_BASE_URL = "https://fireant.vn"
    FIREANT_STOCK_URL = "https://fireant.vn/ma-chung-khoan"
    FIREANT_ARTICLE_URL = "https://fireant.vn/bai-viet"
    
    @classmethod
    def get_all_news_tables(cls) -> list:
        """Get list of all news table names"""
        return list(cls.NEWS_TABLES.values())
    
    @classmethod
    def get_all_stock_tables(cls) -> list:
        """Get list of all stock table names"""
        return list(cls.STOCK_TABLES.values())
    
    @classmethod
    def get_table_name(cls, stock_code: str = None, is_general: bool = False, is_stock: bool = False) -> str:
        """
        Get appropriate table name based on parameters
        
        Args:
            stock_code: Stock code (FPT, GAS, IMP, VCB)
            is_general: True for general news
            is_stock: True for stock price data
            
        Returns:
            str: Table name
        """
        if is_general:
            return cls.NEWS_TABLES["general_news"]
        elif is_stock and stock_code:
            return cls.STOCK_TABLES.get(f"{stock_code.lower()}_stock", f"{stock_code}_Stock")
        elif stock_code:
            return cls.NEWS_TABLES.get(f"{stock_code.lower()}_news", f"{stock_code}_News")
        else:
            return cls.NEWS_TABLES["general_news"]
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate database configuration"""
        errors = []
        
        if not cls.SUPABASE_URL:
            errors.append("SUPABASE_URL is required")
        
        if not cls.SUPABASE_KEY:
            errors.append("SUPABASE_KEY is required")
            
        if errors:
            raise ValueError(f"Database configuration errors: {', '.join(errors)}")
        
        return True
