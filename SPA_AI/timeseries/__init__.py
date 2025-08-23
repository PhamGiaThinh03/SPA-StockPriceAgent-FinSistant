"""
TIMESERIES MODULE
Stock price prediction using LSTM/GRU models

This module provides:
- StockPredictor: Core prediction class
- TimeseriesPipeline: Integrated pipeline for SPA VIP system
- Support for multiple stock codes (FPT, GAS, IMP, VCB)
- Integration with centralized database system
"""

from .load_model_timeseries_db import StockPredictor, run_prediction_for_table

# Import TimeseriesPipeline only when running within the main system
try:
    from .main_timeseries import TimeseriesPipeline
    _PIPELINE_AVAILABLE = True
except ImportError:
    _PIPELINE_AVAILABLE = False

__all__ = ['StockPredictor', 'run_prediction_for_table']

if _PIPELINE_AVAILABLE:
    __all__.append('TimeseriesPipeline')
