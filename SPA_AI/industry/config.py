
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
BASE_DIR = Path(__file__).parent

# Add parent directory to path for centralized database import
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Import centralized database system
from database import DatabaseConfig

class Config:
    # Use centralized database configuration
    DATABASE_CONFIG = DatabaseConfig()

    # Model paths - Updated to use model_AI centralized structure
    MODEL_INDUSTRY_PATH = os.path.join(parent_dir, 'model_AI', 'industry_model', 'PhoBERT_summary_industry_v4.bin')

    # Table configuration - Industry classification only works on General_News
    NEWS_TABLES = ['General_News']  # Only process general news for industry classification

    # Column names standardized according to SPA VIP schema
    TITLE_COLUMN = 'title'
    CONTENT_COLUMN = 'content'
    DATETIME_COLUMN = 'date'
    SUMMARY_COLUMN = 'ai_summary'
    INDUSTRY_COLUMN = 'industry'

    # Industry classification labels (matching trained model - 5 classes)
    INDUSTRY_LABELS = [
        'Finance',      # Finance - Banking
        'Technology',   # Technology
        'Healthcare',   # Healthcare - Pharmaceuticals
        'Energy',       # Energy - Oil & Gas
        'Other'         # Other
    ]

    # Processing configuration
    BATCH_SIZE = 50
    PROCESSING_INTERVAL = 60  # seconds