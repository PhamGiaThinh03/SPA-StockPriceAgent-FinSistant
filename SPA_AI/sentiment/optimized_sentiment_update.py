#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OPTIMIZED SENTIMENT UPDATE LOGIC
Only update trading days affected by new news

Author: SPA VIP Team
Date: August 4, 2025
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Set, List, Dict, Any

def get_affected_trading_days(db_manager, stock_table: str, news_dates: Set[str]) -> Dict[str, List[str]]:
    """
    Find trading days affected by new news dates
    IMPROVED: Returns a mapping from trading day → news dates to avoid aggregating all into one day
    
    Args:
        db_manager: Database manager instance
        stock_table: Stock table name (e.g., 'FPT_Stock')
        news_dates: Set of dates with new news (format: 'YYYY-MM-DD')
    
    Returns:
        Dict mapping trading_day → list of news_dates affecting it
    """
    if not news_dates:
        return {}
    
    print(f"Finding affected trading days for news dates: {len(news_dates)} dates")
    
    try:
        # Retrieve all trading days from stock table
        response = db_manager.client.table(stock_table).select("date").order("date", desc=False).execute()
        if not response.data:
            print(f"No trading days found in {stock_table}")
            return {}
        
        trading_days_df = pd.DataFrame(response.data)
        trading_days_df['date'] = pd.to_datetime(trading_days_df['date'])
        trading_days = set(trading_days_df['date'].dt.strftime('%Y-%m-%d'))
        trading_days_list = sorted(trading_days_df['date'].dt.strftime('%Y-%m-%d').tolist())
        
        print(f"Found {len(trading_days)} trading days in {stock_table}")
        
    except Exception as e:
        print(f"Error getting trading days from {stock_table}: {e}")
        return {}
    
    # Mapping: trading_day → [news_dates]
    trading_day_mapping = {}
    
    # Check stock activity level (many or few recent trading days)
    recent_days = [day for day in trading_days_list if pd.to_datetime(day) >= pd.to_datetime('2024-01-01')]
    is_low_activity_stock = len(recent_days) < 50  # Less than 50 recent trading days
    
    if is_low_activity_stock:
        print(f"{stock_table}: Low activity stock detected - using daily-based mapping")
        
        # For low-activity stocks: Map each news date to itself (create virtual trading day)
        for news_date_str in news_dates:
            if news_date_str in trading_days:
                # If it's an actual trading day
                if news_date_str not in trading_day_mapping:
                    trading_day_mapping[news_date_str] = []
                trading_day_mapping[news_date_str].append(news_date_str)
                print(f"Direct trading day: {news_date_str}")
            else:
                # If not a trading day, still create a separate entry
                if news_date_str not in trading_day_mapping:
                    trading_day_mapping[news_date_str] = []
                trading_day_mapping[news_date_str].append(news_date_str)
                print(f"Virtual trading day: {news_date_str}")
    else:
        print(f"{stock_table}: Active stock detected - using traditional mapping")
        
        # For active stocks: old logic (aggregate into the next trading day)
        for news_date_str in news_dates:
            news_date = pd.to_datetime(news_date_str)
            
            # If news date is a trading day
            if news_date_str in trading_days:
                if news_date_str not in trading_day_mapping:
                    trading_day_mapping[news_date_str] = []
                trading_day_mapping[news_date_str].append(news_date_str)
                print(f"Direct trading day: {news_date_str}")
            else:
                # Find next trading day to aggregate sentiment
                next_trading_day = None
                for trading_day_str in trading_days_list:
                    trading_day_date = pd.to_datetime(trading_day_str)
                    if trading_day_date > news_date:
                        next_trading_day = trading_day_str
                        break
                
                if next_trading_day:
                    if next_trading_day not in trading_day_mapping:
                        trading_day_mapping[next_trading_day] = []
                    trading_day_mapping[next_trading_day].append(news_date_str)
                    print(f"Non-trading day {news_date_str} → affects {next_trading_day}")
                else:
                    # If no future trading day, use latest trading day
                    latest_trading_day = trading_days_list[-1]
                    latest_date = pd.to_datetime(latest_trading_day)
                    
                    # Only aggregate if news date >= latest trading day
                    if news_date >= latest_date:
                        if latest_trading_day not in trading_day_mapping:
                            trading_day_mapping[latest_trading_day] = []
                        trading_day_mapping[latest_trading_day].append(news_date_str)
                        print(f"Latest news date {news_date_str} → affects latest trading day {latest_trading_day}")
                    else:
                        print(f"News date {news_date_str} is too old, no trading day affected")
    
    print(f"Total affected trading days: {len(trading_day_mapping)}")
    return trading_day_mapping

def reset_sentiment_for_specific_dates(db_manager, stock_table: str, trading_day_mapping: Dict[str, List[str]]) -> int:
    """
    Reset sentiment stats to 0 only for specific dates
    IMPROVED: Supports virtual trading days for low-activity stocks
    
    Args:
        db_manager: Database manager instance
        stock_table: Stock table name
        trading_day_mapping: Dict mapping trading_day → news_dates
    
    Returns:
        Number of dates successfully reset
    """
    if not trading_day_mapping:
        print(f"No trading dates to reset in {stock_table}")
        return 0
    
    print(f"Resetting sentiment for {len(trading_day_mapping)} specific dates in {stock_table}")
    
    reset_count = 0
    for trading_day in trading_day_mapping.keys():
        try:
            # Check if there is any row for this date
            check_response = db_manager.client.table(stock_table).select("date").eq("date", trading_day).execute()
            
            if check_response.data:
                # Update existing row
                result = db_manager.client.table(stock_table).update({
                    "Positive": 0,
                    "Negative": 0,
                    "Neutral": 0
                }).eq("date", trading_day).execute()
                
                if result.data:
                    reset_count += 1
                    print(f"Reset {trading_day}: P=0, N=0, Neu=0")
            else:
                # For low-activity stocks, may need to create virtual row
                # Skip for now - will be handled during update phase
                print(f"Virtual trading day {trading_day} - will be created during update")
                reset_count += 1
                
        except Exception as e:
            print(f"Error resetting {trading_day}: {e}")
    
    print(f"Successfully reset sentiment for {reset_count}/{len(trading_day_mapping)} dates")
    return reset_count

def get_sentiment_stats_for_affected_dates(db_manager, news_table: str, trading_day_mapping: Dict[str, List[str]], is_low_activity: bool = False) -> pd.DataFrame:
    """
    Get sentiment stats according to different strategies for each stock type
    
    Args:
        db_manager: Database manager instance
        news_table: News table name
        trading_day_mapping: Dict mapping trading_day → news_dates
        is_low_activity: True if low-activity stock (stats by day)
    
    Returns:
        DataFrame containing sentiment stats
    """
    if not trading_day_mapping:
        return pd.DataFrame()
    
    stock_code = news_table.replace("_News", "")
    
    if is_low_activity:
        print(f"LOW-ACTIVITY STOCK ({stock_code}): Getting daily sentiment stats")
        return get_daily_sentiment_stats(db_manager, news_table, trading_day_mapping)
    else:
        print(f"ACTIVE STOCK ({stock_code}): Getting aggregated sentiment stats")
        return get_aggregated_sentiment_stats(db_manager, news_table, trading_day_mapping)

def get_daily_sentiment_stats(db_manager, news_table: str, trading_day_mapping: Dict[str, List[str]]) -> pd.DataFrame:
    """
    Get sentiment stats for each specific day (for low-activity stocks)
    """
    all_sentiment_data = []
    
    for trading_day, news_dates in trading_day_mapping.items():
        print(f"Processing daily stats for {trading_day} with {len(news_dates)} news dates")
        
        try:
            # Retrieve sentiment for specific news dates (split to avoid query errors)
            news_date_chunks = [news_dates[i:i+10] for i in range(0, len(news_dates), 10)]
            chunk_data = []
            
            for chunk in news_date_chunks:
                if len(chunk) == 1:
                    # Single condition - no need for OR
                    response = db_manager.client.table(news_table).select("date, sentiment").neq("sentiment", None).neq("sentiment", "").eq("date", chunk[0]).execute()
                else:
                    # Multiple conditions - use IN filter instead of OR
                    response = db_manager.client.table(news_table).select("date, sentiment").neq("sentiment", None).neq("sentiment", "").in_("date", chunk).execute()
                
                if response.data:
                    chunk_data.extend(response.data)
            
            if chunk_data:
                # Assign all sentiment to this trading day
                for record in chunk_data:
                    record['trading_day'] = trading_day
                all_sentiment_data.extend(chunk_data)
                print(f"Found {len(chunk_data)} sentiment records for {trading_day}")
            else:
                print(f"No sentiment data for {trading_day}")
                
        except Exception as e:
            print(f"Error getting sentiment for {trading_day}: {e}")
    
    if not all_sentiment_data:
        return pd.DataFrame()
    
    # Create DataFrame and group by trading_day
    sentiment_df = pd.DataFrame(all_sentiment_data)
    
    # Add trading_day mapping column
    sentiment_df['trading_day'] = sentiment_df['date'].apply(
        lambda date: next((td for td, nd_list in trading_day_mapping.items() if date in nd_list), date)
    )
    
    # Group by trading_day and count sentiment
    sentiment_stats = sentiment_df.groupby('trading_day')['sentiment'].value_counts().unstack(fill_value=0)
    sentiment_stats = sentiment_stats.reindex(columns=['Positive', 'Negative', 'Neutral'], fill_value=0)
    sentiment_stats = sentiment_stats.reset_index()
    sentiment_stats.rename(columns={'trading_day': 'date'}, inplace=True)

    print(f"Daily sentiment stats completed: {len(sentiment_stats)} trading days")
    return sentiment_stats

def get_aggregated_sentiment_stats(db_manager, news_table: str, trading_day_mapping: Dict[str, List[str]]) -> pd.DataFrame:
    """
    Get sentiment stats using traditional aggregation logic (for active stocks)
    """
    try:
        # Retrieve all trading days to determine date range
        stock_table = news_table.replace("_News", "_Stock")
        response = db_manager.client.table(stock_table).select("date").order("date", desc=False).execute()
        if not response.data:
            return pd.DataFrame()
        
        trading_days_df = pd.DataFrame(response.data)
        trading_days_df['date'] = pd.to_datetime(trading_days_df['date'])
        trading_days_list = sorted(trading_days_df['date'].dt.strftime('%Y-%m-%d').tolist())
        
        # Determine date range for sentiment retrieval
        relevant_dates = set()
        
        for affected_trading_day in trading_day_mapping.keys():
            affected_date = pd.to_datetime(affected_trading_day)
            
            # Find previous trading day to define range
            prev_trading_day = None
            for i, trading_day_str in enumerate(trading_days_list):
                if trading_day_str == affected_trading_day and i > 0:
                    prev_trading_day = trading_days_list[i-1]
                    break
            
            # Get all dates from previous trading day +1 to affected trading day
            start_date = pd.to_datetime(prev_trading_day) + timedelta(days=1) if prev_trading_day else affected_date - timedelta(days=7)
            end_date = affected_date
            
            # Add all dates in range
            current_date = start_date
            while current_date <= end_date:
                relevant_dates.add(current_date.strftime('%Y-%m-%d'))
                current_date += timedelta(days=1)
        
        print(f"Checking aggregated sentiment for {len(relevant_dates)} dates in range")
        
        # Query sentiment data for relevant dates (split into chunks to avoid long OR)
        all_sentiment_data = []
        date_chunks = [list(relevant_dates)[i:i+20] for i in range(0, len(relevant_dates), 20)]
        
        for chunk in date_chunks:
            try:
                if len(chunk) == 1:
                    response = db_manager.client.table(news_table).select("date, sentiment").neq("sentiment", None).neq("sentiment", "").eq("date", chunk[0]).execute()
                else:
                    response = db_manager.client.table(news_table).select("date, sentiment").neq("sentiment", None).neq("sentiment", "").in_("date", chunk).execute()
                
                if response.data:
                    all_sentiment_data.extend(response.data)
                    print(f"Found {len(response.data)} sentiment records in chunk")
            except Exception as e:
                print(f"Error querying chunk: {e}")
        
        if not all_sentiment_data:
            print(f"No sentiment data found for relevant dates")
            return pd.DataFrame()
        
        # Compute sentiment stats by date from all data
        sentiment_df = pd.DataFrame(all_sentiment_data)
        sentiment_stats = sentiment_df.groupby('date')['sentiment'].value_counts().unstack(fill_value=0)
        sentiment_stats = sentiment_stats.reindex(columns=['Positive', 'Negative', 'Neutral'], fill_value=0)
        sentiment_stats = sentiment_stats.reset_index()
        
        print(f"Aggregated sentiment stats completed: {len(sentiment_stats)} dates")
        return sentiment_stats
        
    except Exception as e:
        print(f"Error getting aggregated sentiment stats: {e}")
        return pd.DataFrame()

def optimized_process_sentiment_to_stock(db_manager, stock_code: str, updated_dates: Set[str]):
    """
    Optimized sentiment processing with two strategies:
    - Low-activity stocks: daily-based statistics
    - Active stocks (FPT, GAS, VCB): traditional aggregation
    
    Args:
        db_manager: Database manager instance
        stock_code: Stock code (e.g., 'FPT', 'GAS', 'IMP', 'VCB')
        updated_dates: Set of dates with newly added news
    """
    if not updated_dates:
        print(f"No updated dates for {stock_code}")
        return 0
    
    news_table = f"{stock_code}_News"
    stock_table = f"{stock_code}_Stock"
    
    print(f"\nOPTIMIZED SENTIMENT PROCESSING FOR {stock_code}")
    print(f"News table: {news_table}")
    print(f"Stock table: {stock_table}")
    print(f"News dates to process: {len(updated_dates)} dates")
    
    # Step 1: Find affected trading days with mapping
    trading_day_mapping = get_affected_trading_days(db_manager, stock_table, updated_dates)
    
    if not trading_day_mapping:
        print(f"No affected trading days for {stock_code}")
        return 0
    
    # Determine stock type based on number of news, not trading days
    try:
        news_count_response = db_manager.client.table(news_table).select("id", count="exact").execute()
        total_news = news_count_response.count if news_count_response.count else 0
        
        # Low activity: less than 50 total news
        is_low_activity = total_news < 50
        
        strategy = "DAILY-BASED" if is_low_activity else "AGGREGATION-BASED"
        print(f"Strategy: {strategy} (total news: {total_news})")
    except Exception as e:
        print(f"Error checking news count, defaulting to aggregation: {e}")
        is_low_activity = False
        strategy = "AGGREGATION-BASED"
    
    # Step 2: Reset only affected trading days
    reset_count = reset_sentiment_for_specific_dates(db_manager, stock_table, trading_day_mapping)
    
    # Step 3: Get sentiment stats according to strategy
    sentiment_stats = get_sentiment_stats_for_affected_dates(
        db_manager, news_table, trading_day_mapping, is_low_activity
    )
    
    if sentiment_stats.empty:
        print(f"No sentiment statistics to process for {stock_code}")
        return 0
    
    # Step 4: Update sentiment statistics
    if is_low_activity:
        # For low-activity stocks: update/insert directly by date
        updated_count = update_daily_sentiment_stats(db_manager, stock_table, sentiment_stats)
    else:
        # For active stocks: use traditional aggregation
        from sentiment.predict_sentiment_db import aggregate_sentiment_for_trading_days, update_stock_sentiment_stats
        
        aggregated_sentiment_stats = aggregate_sentiment_for_trading_days(db_manager, stock_table, sentiment_stats)
        if aggregated_sentiment_stats.empty:
            print(f"No aggregated sentiment statistics to update for {stock_code}")
            return 0
        
        updated_count = update_stock_sentiment_stats(db_manager, stock_table, aggregated_sentiment_stats, reset_mode=False)
    
    print(f"OPTIMIZED PROCESSING COMPLETED for {stock_code}")
    print(f"   Strategy: {strategy}")
    print(f"   Affected trading days: {len(trading_day_mapping)}")
    print(f"   Reset dates: {reset_count}")
    print(f"   Updated dates: {updated_count}")
    
    return updated_count

def update_daily_sentiment_stats(db_manager, stock_table: str, sentiment_stats: pd.DataFrame) -> int:
    """
    Update sentiment statistics for low-activity stocks (daily-based)
    
    Args:
        db_manager: Database manager instance  
        stock_table: Stock table name
        sentiment_stats: DataFrame containing sentiment stats with columns [date, Positive, Negative, Neutral]
    
    Returns:
        Number of records successfully updated
    """
    if sentiment_stats.empty:
        return 0
    
    print(f"Updating daily sentiment stats for {len(sentiment_stats)} dates")
    updated_count = 0
    
    for _, row in sentiment_stats.iterrows():
        date_str = row['date']
        positive = int(row.get('Positive', 0))
        negative = int(row.get('Negative', 0))
        neutral = int(row.get('Neutral', 0))
        
        try:
            # Check if a record already exists for this date
            check_response = db_manager.client.table(stock_table).select("date").eq("date", date_str).execute()
            
            if check_response.data:
                # Update existing record
                result = db_manager.client.table(stock_table).update({
                    "Positive": positive,
                    "Negative": negative, 
                    "Neutral": neutral
                }).eq("date", date_str).execute()
                
                if result.data:
                    updated_count += 1
                    print(f"Updated {date_str}: P={positive}, N={negative}, Neu={neutral}")
            else:
                # For low-activity stocks, creating virtual record is skipped to avoid inconsistency with stock price data
                print(f"No existing record for {date_str} - skipping (virtual day)")
                
        except Exception as e:
            print(f"Error updating {date_str}: {e}")
    
    print(f"Daily sentiment update completed: {updated_count}/{len(sentiment_stats)} dates")
    return updated_count

if __name__ == "__main__":
    print("Optimized Sentiment Update Logic")
    print("This module provides optimized functions for selective sentiment updates")
