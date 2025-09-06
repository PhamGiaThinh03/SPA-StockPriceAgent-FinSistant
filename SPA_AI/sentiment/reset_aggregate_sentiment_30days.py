#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to process sentiment aggregation for the last 30 days
Aggregate sentiment from weekend/holiday into the next trading day
"""

import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Import database manager
from database import SupabaseManager

def reset_and_aggregate_sentiment_30days(stock_code: str):
    """
    Reset and aggregate sentiment for the last 30 days

    Logic:
    1. Get all sentiment from news table (30 days)
    2. Reset sentiment in stock table (30 days) to 0
    3. Aggregate sentiment into trading days:
       - Trading day: Add sentiment of that day
       - Non-trading day: Aggregate into the next trading day

    Args:
        stock_code: Stock code (FPT, GAS, IMP, VCB)
    """
    print(f"\n{'='*60}")
    print(f"RESET & AGGREGATE SENTIMENT FOR LAST 30 DAYS FOR {stock_code}")
    print(f"{'='*60}")
    
    try:
        # Initialize database
        db_manager = SupabaseManager()
        news_table = f"{stock_code}_News"
        stock_table = f"{stock_code}_Stock"

        # Calculate 30-day window
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)

        print(f"Processing from: {start_date} to {end_date}")

        # 1. Get all sentiment from news table (30 days)
        print(f"\nStep 1: Get sentiment from {news_table}...")
        news_response = db_manager.client.table(news_table).select(
            "date, sentiment"
        ).gte("date", start_date.strftime('%Y-%m-%d')).lte("date", end_date.strftime('%Y-%m-%d')).neq("sentiment", "").neq("sentiment", None).execute()

        if not news_response.data:
            print(f"No sentiment data in last 30 days for {stock_code}")
            return False

        # Group sentiment by date
        sentiment_df = pd.DataFrame(news_response.data)
        sentiment_counts = sentiment_df.groupby(['date', 'sentiment']).size().reset_index(name='count')
        sentiment_stats = sentiment_counts.pivot_table(
            index='date',
            columns='sentiment',
            values='count',
            fill_value=0
        ).reset_index()

        # Ensure all sentiment columns exist
        for col in ['Positive', 'Negative', 'Neutral']:
            if col not in sentiment_stats.columns:
                sentiment_stats[col] = 0

        print(f"Found sentiment for {len(sentiment_stats)} days")

        # 2. Get trading days (stock table with close_price)
        print(f"\nStep 2: Get trading days from {stock_table}...")
        trading_response = db_manager.client.table(stock_table).select(
            "date, close_price"
        ).gte("date", start_date.strftime('%Y-%m-%d')).lte("date", end_date.strftime('%Y-%m-%d')).neq("close_price", "").not_.is_("close_price", "null").order("date").execute()

        if not trading_response.data:
            print(f"No trading days in last 30 days for {stock_code}")
            return False

        trading_days = [row['date'] for row in trading_response.data]
        trading_days_set = set(trading_days)

        print(f"Found {len(trading_days)} trading days")

        # 3. Reset sentiment for all stock records in 30-day window
        print(f"\nStep 3: Reset sentiment in {stock_table}...")
        all_stock_response = db_manager.client.table(stock_table).select("date").gte("date", start_date.strftime('%Y-%m-%d')).lte("date", end_date.strftime('%Y-%m-%d')).execute()

        reset_count = 0
        if all_stock_response.data:
            for row in all_stock_response.data:
                date_str = row['date']
                try:
                    db_manager.client.table(stock_table).update({
                        "Positive": 0,
                        "Negative": 0,
                        "Neutral": 0
                    }).eq("date", date_str).execute()
                    reset_count += 1
                except Exception as e:
                    print(f"Error resetting {date_str}: {e}")

        print(f"Reset sentiment for {reset_count} days")

        # 4. Aggregate sentiment logic
        print(f"\nStep 4: Aggregate sentiment...")

        aggregated_data = []
        pending_sentiment = {'Positive': 0, 'Negative': 0, 'Neutral': 0}

        # Sort sentiment dates
        sentiment_stats_sorted = sentiment_stats.sort_values('date')

        for _, row in sentiment_stats_sorted.iterrows():
            date_str = row['date']
            sentiment_date = pd.to_datetime(date_str)

            # Add current day sentiment to pending
            pending_sentiment['Positive'] += int(row.get('Positive', 0))
            pending_sentiment['Negative'] += int(row.get('Negative', 0))
            pending_sentiment['Neutral'] += int(row.get('Neutral', 0))

            if date_str in trading_days_set:
                # Trading day: Apply accumulated sentiment
                aggregated_data.append({
                    'date': date_str,
                    'Positive': pending_sentiment['Positive'],
                    'Negative': pending_sentiment['Negative'],
                    'Neutral': pending_sentiment['Neutral']
                })

                print(f"Trading day {date_str}: P={pending_sentiment['Positive']}, N={pending_sentiment['Negative']}, Neu={pending_sentiment['Neutral']}")

                # Reset pending sentiment
                pending_sentiment = {'Positive': 0, 'Negative': 0, 'Neutral': 0}
            else:
                # Non-trading day: Find next trading day
                next_trading_day = None
                for trading_day_str in trading_days:
                    trading_day_date = pd.to_datetime(trading_day_str)
                    if trading_day_date > sentiment_date:
                        next_trading_day = trading_day_str
                        break

                if next_trading_day:
                    print(f"Non-trading day {date_str}: P={int(row.get('Positive', 0))}, N={int(row.get('Negative', 0))}, Neu={int(row.get('Neutral', 0))} (aggregated into {next_trading_day})")
                else:
                    print(f"Non-trading day {date_str}: P={int(row.get('Positive', 0))}, N={int(row.get('Negative', 0))}, Neu={int(row.get('Neutral', 0))} (no next trading day)")

        # Handle remaining pending sentiment
        if any(pending_sentiment.values()) and trading_days:
            last_trading_day = trading_days[-1]

            # Check if we already have data for last trading day
            existing_data = None
            for i, data in enumerate(aggregated_data):
                if data['date'] == last_trading_day:
                    existing_data = i
                    break

            if existing_data is not None:
                # Add to existing
                aggregated_data[existing_data]['Positive'] += pending_sentiment['Positive']
                aggregated_data[existing_data]['Negative'] += pending_sentiment['Negative']
                aggregated_data[existing_data]['Neutral'] += pending_sentiment['Neutral']
                print(f"Added to last trading day {last_trading_day}: P={aggregated_data[existing_data]['Positive']}, N={aggregated_data[existing_data]['Negative']}, Neu={aggregated_data[existing_data]['Neutral']}")
            else:
                # Create new entry
                aggregated_data.append({
                    'date': last_trading_day,
                    'Positive': pending_sentiment['Positive'],
                    'Negative': pending_sentiment['Negative'],
                    'Neutral': pending_sentiment['Neutral']
                })
                print(f"Created new entry for last trading day {last_trading_day}: P={pending_sentiment['Positive']}, N={pending_sentiment['Negative']}, Neu={pending_sentiment['Neutral']}")

        # 5. Update stock table with aggregated sentiment
        print(f"\nStep 5: Update {stock_table}...")

        updated_count = 0
        for data in aggregated_data:
            date_str = data['date']
            try:
                # Check if record exists
                check_response = db_manager.client.table(stock_table).select("date").eq("date", date_str).execute()

                if check_response.data:
                    # Update existing record
                    result = db_manager.client.table(stock_table).update({
                        "Positive": data['Positive'],
                        "Negative": data['Negative'],
                        "Neutral": data['Neutral']
                    }).eq("date", date_str).execute()

                    if result.data:
                        updated_count += 1
                        print(f"Updated {date_str}: P={data['Positive']}, N={data['Negative']}, Neu={data['Neutral']}")
                    else:
                        print(f"Failed to update {date_str}")
                else:
                    print(f"No record found for {date_str}")

            except Exception as e:
                print(f"Error updating {date_str}: {e}")

        print(f"\nCompleted! Updated {updated_count}/{len(aggregated_data)} records")
        return True

    except Exception as e:
        print(f"Error processing {stock_code}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    print("RESET & AGGREGATE SENTIMENT FOR LAST 30 DAYS")
    print("="*80)
    print(f"Processing time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Logic: Aggregate sentiment from weekend/holiday into the next trading day")

    # Available stocks
    stocks = ["FPT", "GAS", "IMP", "VCB"]

    success_count = 0

    for stock in stocks:
        result = reset_and_aggregate_sentiment_30days(stock)
        if result:
            success_count += 1

    print(f"\n{'='*80}")
    print(f"COMPLETED: {success_count}/{len(stocks)} stocks processed successfully")
    print("="*80)

if __name__ == "__main__":
    main()
