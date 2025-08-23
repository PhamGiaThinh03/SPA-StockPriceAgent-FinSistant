"""
Crawlers Package
Chứa tất cả các crawler cho các trang tin tức khác nhau
"""

from .fireant_crawler import crawl_fireant
from .cafef_keyword_crawler import main_cafef
from .cafef_general_crawler import crawl_cafef_chung
from .chungta_crawler import main_chungta
from .markettime import crawl_markettimes, crawl_markettimes_general, main_markettimes
from .diendandoanhnghiep import crawl_dddn_stock, crawl_dddn_general, main_dddn
from .crawl_imp import crawl_imp, main_imp
from .petrotimes import crawl_petrotimes_gas, main_petrotimes

__all__ = [
    'crawl_fireant',
    'main_cafef',
    'crawl_cafef_chung',
    'main_chungta',
    'crawl_markettimes',
    'crawl_markettimes_general',
    'main_markettimes',
    'crawl_dddn_stock',
    'crawl_dddn_general',
    'main_dddn',
    'crawl_imp',
    'main_imp',
    'crawl_petrotimes_gas',
    'main_petrotimes'
]
