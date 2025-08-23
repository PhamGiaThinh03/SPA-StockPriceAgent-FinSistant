"""
Database Schemas
Define table structures and data validation
"""

from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class NewsSchema:
    """Schema for news articles"""
    
    # Required fields
    title: str
    content: str
    link: str
    date: str
    
    # Optional fields
    ai_summary: Optional[str] = None
    sentiment: Optional[str] = None
    industry: Optional[str] = None
    source_link: Optional[str] = None
    
    def to_dict(self, include_industry: bool = False) -> Dict[str, Any]:
        """Convert to dictionary for database insertion"""
        data = {
            "title": self.title,
            "content": self.content,
            "link": self.link,
            "date": self.date,
            "ai_summary": self.ai_summary,
            "sentiment": self.sentiment,
            "source_link": self.source_link
        }
        
        # Only include industry field for General_News table
        if include_industry:
            data["industry"] = self.industry
            
        return data
    
    @classmethod
    def from_crawler_data(cls, data: Dict[str, Any]) -> 'NewsSchema':
        """Create from crawler data"""
        return cls(
            title=data.get("title", ""),
            content=data.get("content", ""),
            link=data.get("link", ""),
            date=data.get("date", ""),
            ai_summary=data.get("ai_summary"),
            sentiment=data.get("sentiment"),
            industry=data.get("industry"),
            source_link=data.get("source_link")
        )
    
    def validate(self) -> bool:
        """Validate required fields"""
        if not self.title or not self.content or not self.link:
            return False
        return True

@dataclass 
class StockSchema:
    """Schema for stock price data"""
    
    # Required fields
    date: str
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    
    # Optional fields
    change_percent: Optional[float] = None
    change_value: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion"""
        return {
            "date": self.date,
            "open": self.open_price,
            "high": self.high_price,
            "low": self.low_price,
            "close": self.close_price,
            "volume": self.volume,
            "change_percent": self.change_percent,
            "change_value": self.change_value
        }
    
    @classmethod
    def from_crawler_data(cls, data: Dict[str, Any]) -> 'StockSchema':
        """Create from crawler data"""
        return cls(
            date=data.get("date", ""),
            open_price=float(data.get("open", 0)),
            high_price=float(data.get("high", 0)),
            low_price=float(data.get("low", 0)),
            close_price=float(data.get("close", 0)),
            volume=int(data.get("volume", 0)),
            change_percent=data.get("change_percent"),
            change_value=data.get("change_value")
        )
    
    def validate(self) -> bool:
        """Validate required fields"""
        if not self.date or self.close_price <= 0:
            return False
        return True

def format_datetime_for_db(dt: datetime) -> str:
    """Format datetime for database storage"""
    if dt:
        return dt.strftime("%Y-%m-%d")
    return datetime.now().strftime("%Y-%m-%d")

def validate_article_data(data: Dict[str, Any]) -> bool:
    """Validate article data before insertion"""
    required_fields = ["title", "content", "link", "date"]
    
    for field in required_fields:
        if not data.get(field):
            return False
            
    # Content should be meaningful
    if len(data.get("content", "").strip()) < 50:
        return False
        
    return True

def validate_stock_data(data: Dict[str, Any]) -> bool:
    """Validate stock data before insertion"""
    required_fields = ["date", "close"]
    
    for field in required_fields:
        if not data.get(field):
            return False
            
    # Close price should be positive
    try:
        close_price = float(data.get("close", 0))
        if close_price <= 0:
            return False
    except (ValueError, TypeError):
        return False
        
    return True
