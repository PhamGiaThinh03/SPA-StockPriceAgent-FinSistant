import os
import sys
import torch
from dotenv import load_dotenv
from typing import Dict, Any
from pathlib import Path

# Thêm đường dẫn để import config từ thư mục crawl
crawl_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'crawl')
if crawl_path not in sys.path:
    sys.path.insert(0, crawl_path)

# Constants - moved from shared_config.py
DEFAULT_SUPABASE_URL = "https://baenxyqklayjtlbmubxe.supabase.co"
DEFAULT_SUPABASE_KEY = "sb_secret_4Mj3OwBW9VlbhVU6bVrfLA_1olLCYpp"
TABLE_NAMES = ['FPT_News', 'GAS_News', 'IMP_News', 'VCB_News', 'General_News']
STOCK_CODES = ['FPT', 'GAS', 'IMP', 'VCB']

load_dotenv()

class Config:
    """Enhanced configuration with Map-Reduce parameters"""
    
    # Hardware
    DEVICE = os.getenv("DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", 5 if DEVICE == "cuda" else 2))
    
    # Supabase - sử dụng config từ crawl folder
    SUPABASE_URL = os.getenv("SUPABASE_URL", DEFAULT_SUPABASE_URL)
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", DEFAULT_SUPABASE_KEY)
    
    # Model paths - absolute path to model_AI directory
    _current_dir = os.path.dirname(os.path.abspath(__file__))
    _project_root = os.path.dirname(_current_dir)  # Go up to SPA_vip
    MODEL_PATH = os.path.join(_project_root, "model_AI", "summarization_model", "model_vit5")
    
    # Text processing
    MAX_INPUT_LENGTH = int(os.getenv("MAX_INPUT_LENGTH", 1024))
    MAX_TARGET_LENGTH = int(os.getenv("MAX_TARGET_LENGTH", 256))
    
    # Map-Reduce Configuration
    ENABLE_MAP_REDUCE = os.getenv("ENABLE_MAP_REDUCE", "true").lower() == "true"
    MAP_REDUCE_CHUNK_OVERLAP = int(os.getenv("MAP_REDUCE_CHUNK_OVERLAP", 128))
    MAP_REDUCE_MIN_CHUNK_SIZE = int(os.getenv("MAP_REDUCE_MIN_CHUNK_SIZE", 256))
    MAP_REDUCE_MAX_ROUNDS = int(os.getenv("MAP_REDUCE_MAX_ROUNDS", 3))
    
    # Performance
    MAX_ARTICLES_PER_RUN = int(os.getenv("MAX_ARTICLES_PER_RUN", 0))  # 0 = unlimited

    MAX_RETRIES = 3  # Try again when you encounter an error
    RETRY_DELAY = 5  # Waiting time between testing (seconds)
    
    # Tables to process (sử dụng từ crawl config)
    # News tables
    NEWS_TABLES = TABLE_NAMES  # TABLE_NAMES đã là list
        
    @staticmethod
    def get_generation_config() -> Dict[str, Any]:
        config = {
            "max_length": Config.MAX_TARGET_LENGTH,
            "min_length": 30,
            "repetition_penalty": 1.2,
            "length_penalty": 1.0,
            "early_stopping": True,
            "no_repeat_ngram_size": 3 if Config.DEVICE == "cuda" else 2,
            "num_beams": 4 if Config.DEVICE == "cuda" else 2
        }
        return config