#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TIMESERIES PREDICTION PIPELINE
Integrated timeseries prediction system for SPA VIP

Author: SPA VIP Team
Date: August 5, 2025
"""

import sys
import os
import logging
from typing import Dict, List, Set, Any
from datetime import datetime

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Import centralized database
from database import SupabaseManager, DatabaseConfig
from load_model_timeseries_db import StockPredictor

logger = logging.getLogger(__name__)

class TimeseriesPipeline:
    """
    Integrated timeseries prediction pipeline for SPA VIP system
    """
    
    def __init__(self):
        """Initialize the timeseries pipeline"""
        self.db_manager = SupabaseManager()
        self.config = DatabaseConfig()
        self.predictors = {}  # Cache for model predictors
        self.results = {}
        
        # Available stock codes
        self.available_stocks = ["FPT", "GAS", "IMP", "VCB"]
        
        logger.info("🚀 Timeseries Pipeline initialized")
    
    def _get_predictor(self, stock_code: str, model_path: str = None) -> StockPredictor:
        """
        Get or create a predictor for specific stock using centralized database
        
        Args:
            stock_code: Stock code (e.g., 'FPT', 'GAS')
            model_path: Path to the model file
        
        Returns:
            StockPredictor instance
        """
        if stock_code not in self.predictors:
            # Default model path if not provided
            if model_path is None:
                # Use relative path from timeseries directory
                model_path = os.path.join(current_dir, "..", "model_AI", "timeseries_model", "model_lstm", "LSTM_missing10_window15.keras")
            
            # Create stock table name
            stock_table = f"{stock_code}_Stock"
            
            # Create predictor with centralized database
            config = StockPredictor.create_default_supabase_config(stock_table)
            predictor = StockPredictor(model_path, config, use_centralized_db=True)
            
            self.predictors[stock_code] = predictor
            
        return self.predictors[stock_code]
    
    def predict_single_stock(self, stock_code: str, model_path: str = None) -> Dict[str, Any]:
        """
        Predict stock price for a single stock
        
        Args:
            stock_code: Stock code to predict
            model_path: Path to model file (optional)
        
        Returns:
            Dictionary with prediction results
        """
        logger.info(f"🎯 Starting prediction for {stock_code}")
        
        try:
            # Get predictor
            predictor = self._get_predictor(stock_code, model_path)
            
            # Load model
            if not predictor.load_model():
                return {
                    'stock_code': stock_code,
                    'status': 'error',
                    'error': 'Failed to load model',
                    'predictions': None
                }
            
            # Load window data (15 days for current model)
            df_window = predictor.load_last_window_data()
            if df_window is None or len(df_window) < predictor.window_size:
                return {
                    'stock_code': stock_code,
                    'status': 'error',
                    'error': f'Insufficient data (need at least {predictor.window_size} days)',
                    'predictions': None
                }
            
            # Make predictions
            future_dates, pred_prices = predictor.predict_next_10_days(df_window)
            
            if future_dates is None:
                return {
                    'stock_code': stock_code,
                    'status': 'error', 
                    'error': 'Prediction failed',
                    'predictions': None
                }
            
            # Update database with predictions
            update_success = predictor.update_existing_predictions(future_dates, pred_prices)
            
            # Format predictions
            predictions = []
            for date, price in zip(future_dates, pred_prices):
                predictions.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'predicted_price': float(price),
                    'formatted_price': f"{price:,.0f} VND"
                })
            
            result = {
                'stock_code': stock_code,
                'status': 'success',
                'error': None,
                'predictions': predictions,
                'database_updated': update_success,
                'total_predictions': len(predictions)
            }
            
            logger.info(f"✅ Successfully predicted {stock_code}: {len(predictions)} predictions")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error predicting {stock_code}: {e}")
            return {
                'stock_code': stock_code,
                'status': 'error',
                'error': str(e),
                'predictions': None
            }
    
    def predict_specific_stocks(self, stock_codes: List[str], model_path: str = None) -> Dict[str, Any]:
        """
        Predict stock prices for specific stocks
        
        Args:
            stock_codes: List of stock codes to predict
            model_path: Path to model file (optional)
        
        Returns:
            Dictionary with aggregated results
        """
        logger.info(f"🎯 Starting predictions for {len(stock_codes)} stocks: {stock_codes}")
        
        results = []
        successful_predictions = 0
        failed_predictions = 0
        
        for stock_code in stock_codes:
            if stock_code not in self.available_stocks:
                logger.warning(f"⚠️ Stock code {stock_code} not in available stocks: {self.available_stocks}")
                continue
            
            result = self.predict_single_stock(stock_code, model_path)
            results.append(result)
            
            if result['status'] == 'success':
                successful_predictions += 1
            else:
                failed_predictions += 1
        
        # Calculate summary
        total_stocks = len(results)
        success_rate = (successful_predictions / total_stocks * 100) if total_stocks > 0 else 0
        
        summary = {
            'total_stocks': total_stocks,
            'successful_predictions': successful_predictions,
            'failed_predictions': failed_predictions,
            'success_rate': success_rate,
            'results': results
        }
        
        logger.info(f"📊 Prediction Summary: {successful_predictions}/{total_stocks} successful ({success_rate:.1f}%)")
        
        self.results = summary
        return summary
    
    def predict_all_stocks(self, model_path: str = None) -> Dict[str, Any]:
        """
        Predict stock prices for all available stocks
        
        Args:
            model_path: Path to model file (optional)
        
        Returns:
            Dictionary with aggregated results
        """
        logger.info(f"🎯 Starting predictions for all available stocks: {self.available_stocks}")
        return self.predict_specific_stocks(self.available_stocks, model_path)
    
    def get_stock_prediction_status(self, stock_code: str) -> Dict[str, Any]:
        """
        Get prediction status for a specific stock
        
        Args:
            stock_code: Stock code to check
        
        Returns:
            Dictionary with status information
        """
        try:
            stock_table = f"{stock_code}_Stock"
            
            # Check for recent predictions
            response = (
                self.db_manager.client.table(stock_table)
                .select("date, predict_price")
                .not_.is_("predict_price", "null")
                .neq("predict_price", "")
                .order("date", desc=True)
                .limit(10)
                .execute()
            )
            
            predictions = response.data if response.data else []
            
            return {
                'stock_code': stock_code,
                'recent_predictions': len(predictions),
                'latest_prediction_date': predictions[0]['date'] if predictions else None,
                'has_recent_predictions': len(predictions) > 0
            }
            
        except Exception as e:
            logger.error(f"❌ Error checking status for {stock_code}: {e}")
            return {
                'stock_code': stock_code,
                'error': str(e)
            }
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get overall system status for timeseries predictions
        
        Returns:
            Dictionary with system status
        """
        logger.info("📊 Checking timeseries system status...")
        
        stock_status = []
        total_predictions = 0
        stocks_with_predictions = 0
        
        for stock_code in self.available_stocks:
            status = self.get_stock_prediction_status(stock_code)
            stock_status.append(status)
            
            if status.get('recent_predictions', 0) > 0:
                stocks_with_predictions += 1
                total_predictions += status['recent_predictions']
        
        system_status = {
            'total_stocks': len(self.available_stocks),
            'stocks_with_predictions': stocks_with_predictions,
            'stocks_without_predictions': len(self.available_stocks) - stocks_with_predictions,
            'total_recent_predictions': total_predictions,
            'coverage_rate': (stocks_with_predictions / len(self.available_stocks) * 100) if self.available_stocks else 0,
            'stock_details': stock_status,
            'last_checked': datetime.now().isoformat()
        }
        
        logger.info(f"📈 System Status: {stocks_with_predictions}/{len(self.available_stocks)} stocks have predictions")
        return system_status
    
    def close_connections(self):
        """Close database connections"""
        if hasattr(self, 'db_manager') and self.db_manager:
            try:
                self.db_manager.close_connections()
                logger.info("🔒 Database connections closed")
            except Exception as e:
                logger.warning(f"⚠️ Error closing connections: {e}")


def main():
    """Main function for testing timeseries pipeline"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    pipeline = TimeseriesPipeline()
    
    try:
        # Show system status
        logger.info("="*60)
        logger.info("📊 TIMESERIES SYSTEM STATUS")
        logger.info("="*60)
        
        status = pipeline.get_system_status()
        logger.info(f"📈 Coverage: {status['stocks_with_predictions']}/{status['total_stocks']} stocks")
        logger.info(f"📊 Recent predictions: {status['total_recent_predictions']}")
        
        # Run predictions for all stocks
        logger.info("\n" + "="*60)
        logger.info("🚀 RUNNING PREDICTIONS FOR ALL STOCKS")
        logger.info("="*60)
        
        results = pipeline.predict_all_stocks()
        
        # Print results summary
        logger.info("\n" + "="*60)
        logger.info("📋 PREDICTION RESULTS SUMMARY")
        logger.info("="*60)
        
        logger.info(f"📊 Total stocks processed: {results['total_stocks']}")
        logger.info(f"✅ Successful predictions: {results['successful_predictions']}")
        logger.info(f"❌ Failed predictions: {results['failed_predictions']}")
        logger.info(f"📈 Success rate: {results['success_rate']:.1f}%")
        
        # Print details for each stock
        for result in results['results']:
            stock_code = result['stock_code']
            status = result['status']
            
            if status == 'success':
                pred_count = result['total_predictions']
                logger.info(f"✅ {stock_code}: {pred_count} predictions made")
            else:
                error = result['error']
                logger.info(f"❌ {stock_code}: {error}")
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ Process interrupted by user")
    except Exception as e:
        logger.error(f"💥 Pipeline error: {e}")
        raise
    finally:
        pipeline.close_connections()


if __name__ == "__main__":
    main()
