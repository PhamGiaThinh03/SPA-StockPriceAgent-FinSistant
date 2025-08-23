from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any

@dataclass
class NewsArticle:
    """Data model for news articles"""
    date: str
    industry: str
    news_title: str
    news_content: str
    source: str
    influence: List[str]
    stock_ticker: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'date': self.date,
            'industry': self.industry,
            'news_title': self.news_title,
            'news_content': self.news_content,
            'source': self.source,
            'influence': self.influence,
            'stock_ticker': self.stock_ticker
        }


@dataclass 
class StockData:
    """Data model for stock price data"""
    date: str
    close_price: float
    ticker: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'date': self.date,
            'close_price': self.close_price,
            'ticker': self.ticker
        }


@dataclass
class Bookmark:
    """Data model for user bookmarks"""
    id: Optional[int]
    user_id: str
    article_data: Dict[str, Any]
    created_at: Optional[datetime]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'article_data': self.article_data,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


@dataclass
class User:
    """Data model for user information"""
    id: str
    email: str
    created_at: Optional[datetime]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# Response models
@dataclass
class ApiResponse:
    """Standard API response format"""
    success: bool
    data: Any = None
    message: str = ""
    error: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'data': self.data,
            'message': self.message,
            'error': self.error
        }
