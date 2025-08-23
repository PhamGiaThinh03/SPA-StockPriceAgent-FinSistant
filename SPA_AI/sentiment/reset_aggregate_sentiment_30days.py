#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script để xử lý sentiment aggregation cho 30 ngày gần nhất
Dồn sentiment từ weekend/holiday vào trading day tiếp theo
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
    Reset và aggregate sentiment cho 30 ngày gần nhất
    
    Logic:
    1. Lấy tất cả sentiment từ news table (30 ngày)
    2. Reset sentiment của stock table (30 ngày) về 0
    3. Aggregate sentiment vào trading days:
       - Trading day: Cộng sentiment của chính ngày đó
       - Non-trading day: Dồn vào trading day tiếp theo
    
    Args:
        stock_code: Mã cổ phiếu (FPT, GAS, IMP, VCB)
    """
    print(f"\n{'='*60}")
    print(f"🔄 RESET & AGGREGATE SENTIMENT 30 NGÀY CHO {stock_code}")
    print(f"{'='*60}")
    
    try:
        # Initialize database
        db_manager = SupabaseManager()
        news_table = f"{stock_code}_News"
        stock_table = f"{stock_code}_Stock"
        
        # Calculate 30-day window
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        
        print(f"📅 Xử lý từ: {start_date} đến {end_date}")
        
        # 1. Get all sentiment from news table (30 days)
        print(f"\n📰 Bước 1: Lấy sentiment từ {news_table}...")
        news_response = db_manager.client.table(news_table).select(
            "date, sentiment"
        ).gte("date", start_date.strftime('%Y-%m-%d')).lte("date", end_date.strftime('%Y-%m-%d')).neq("sentiment", "").neq("sentiment", None).execute()
        
        if not news_response.data:
            print(f"⚠️ Không có sentiment data trong 30 ngày cho {stock_code}")
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
        
        print(f"✅ Tìm thấy sentiment cho {len(sentiment_stats)} ngày")
        
        # 2. Get trading days (stock table with close_price)
        print(f"\n📈 Bước 2: Lấy trading days từ {stock_table}...")
        trading_response = db_manager.client.table(stock_table).select(
            "date, close_price"
        ).gte("date", start_date.strftime('%Y-%m-%d')).lte("date", end_date.strftime('%Y-%m-%d')).neq("close_price", "").not_.is_("close_price", "null").order("date").execute()
        
        if not trading_response.data:
            print(f"⚠️ Không có trading days trong 30 ngày cho {stock_code}")
            return False
        
        trading_days = [row['date'] for row in trading_response.data]
        trading_days_set = set(trading_days)
        
        print(f"✅ Tìm thấy {len(trading_days)} trading days")
        
        # 3. Reset sentiment for all stock records in 30-day window
        print(f"\n🔄 Bước 3: Reset sentiment trong {stock_table}...")
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
                    print(f"⚠️ Lỗi reset {date_str}: {e}")
        
        print(f"✅ Reset sentiment cho {reset_count} ngày")
        
        # 4. Aggregate sentiment logic
        print(f"\n📊 Bước 4: Aggregate sentiment...")
        
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
                
                print(f"📈 Trading day {date_str}: P={pending_sentiment['Positive']}, N={pending_sentiment['Negative']}, Neu={pending_sentiment['Neutral']}")
                
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
                    print(f"📅 Non-trading day {date_str}: P={int(row.get('Positive', 0))}, N={int(row.get('Negative', 0))}, Neu={int(row.get('Neutral', 0))} (dồn vào {next_trading_day})")
                else:
                    print(f"📅 Non-trading day {date_str}: P={int(row.get('Positive', 0))}, N={int(row.get('Negative', 0))}, Neu={int(row.get('Neutral', 0))} (không có trading day tiếp theo)")
        
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
                print(f"📈 Dồn thêm vào trading day cuối {last_trading_day}: P={aggregated_data[existing_data]['Positive']}, N={aggregated_data[existing_data]['Negative']}, Neu={aggregated_data[existing_data]['Neutral']}")
            else:
                # Create new entry
                aggregated_data.append({
                    'date': last_trading_day,
                    'Positive': pending_sentiment['Positive'],
                    'Negative': pending_sentiment['Negative'],
                    'Neutral': pending_sentiment['Neutral']
                })
                print(f"📈 Tạo mới cho trading day cuối {last_trading_day}: P={pending_sentiment['Positive']}, N={pending_sentiment['Negative']}, Neu={pending_sentiment['Neutral']}")
        
        # 5. Update stock table with aggregated sentiment
        print(f"\n💾 Bước 5: Cập nhật {stock_table}...")
        
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
                        print(f"✅ Cập nhật {date_str}: P={data['Positive']}, N={data['Negative']}, Neu={data['Neutral']}")
                    else:
                        print(f"❌ Không thể cập nhật {date_str}")
                else:
                    print(f"⚠️ Không tìm thấy record cho {date_str}")
                    
            except Exception as e:
                print(f"❌ Lỗi cập nhật {date_str}: {e}")
        
        print(f"\n✅ Hoàn thành! Cập nhật {updated_count}/{len(aggregated_data)} records")
        return True
        
    except Exception as e:
        print(f"❌ Lỗi xử lý {stock_code}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    print("🚀 RESET & AGGREGATE SENTIMENT CHO 30 NGÀY GẦN NHẤT")
    print("="*80)
    print(f"⏰ Thời gian xử lý: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎯 Logic: Dồn sentiment từ weekend/holiday vào trading day tiếp theo")
    
    # Available stocks
    stocks = ["FPT", "GAS", "IMP", "VCB"]
    
    success_count = 0
    
    for stock in stocks:
        result = reset_and_aggregate_sentiment_30days(stock)
        if result:
            success_count += 1
    
    print(f"\n{'='*80}")
    print(f"🎉 HOÀN THÀNH: {success_count}/{len(stocks)} cổ phiếu được xử lý thành công")
    print("="*80)

if __name__ == "__main__":
    main()
