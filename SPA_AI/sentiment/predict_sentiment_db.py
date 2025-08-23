import torch
import torch.nn as nn
import pandas as pd
from transformers import AutoModel, AutoTokenizer
from tqdm import tqdm
import time
import sys
import os

# Add paths for centralized database import
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Import centralized database system
from database import SupabaseManager, DatabaseConfig


# ====================== 1. Định nghĩa model ======================
class SentimentClassifier(nn.Module):
    def __init__(self, n_classes=3):
        super(SentimentClassifier, self).__init__()
        self.bert = AutoModel.from_pretrained("vinai/phobert-base")
        self.drop = nn.Dropout(p=0.3)
        self.fc = nn.Linear(self.bert.config.hidden_size, n_classes)
        nn.init.normal_(self.fc.weight, std=0.02)
        nn.init.normal_(self.fc.bias, 0)

    def forward(self, input_ids, attention_mask):
        _, pooled_output = self.bert(
            input_ids=input_ids,
            attention_mask=attention_mask,
            return_dict=False
        )
        output = self.drop(pooled_output)
        return self.fc(output)

# ====================== 2. Load model & tokenizer ======================
def load_sentiment_model():
    """Load sentiment analysis model and tokenizer"""
    model = SentimentClassifier(n_classes=3)
    model_path = os.path.join(os.path.dirname(__file__), "..", "model_AI", "sentiment_model", "Phobert_hyper_parameters", "PhoBERT_summary_sentiment_v5.bin")
    model.load_state_dict(torch.load(model_path, map_location="cpu"))
    model.eval()
    
    tokenizer = AutoTokenizer.from_pretrained("vinai/phobert-base")
    id2label = {0: "Positive", 1: "Negative", 2: "Neutral"}
    
    return model, tokenizer, id2label

# Initialize model globally (will be loaded when needed)
model, tokenizer, id2label = None, None, None

# ====================== 3. Database Manager ======================
def get_database_manager():
    """Get centralized database manager"""
    return SupabaseManager()

# ====================== 4. Hàm update DB ======================
def update_sentiment_in_db(db_manager, table_name, link, sentiment):
    """Update sentiment using centralized database manager"""
    try:
        # Use centralized database update method
        result = db_manager.client.table(table_name).update({
            "sentiment": sentiment
        }).eq("link", link).execute()
        
        if result.data:
            print(f"✅ Updated sentiment={sentiment} for link={link[:50]}...")
            return True
        else:
            print(f"⚠️ No update for link={link[:50]}...")
            return False
    except Exception as e:
        print(f"❌ Error updating sentiment: {e}")
        return False

# ====================== 5. Đọc dữ liệu từ DB ======================
def get_data_from_db(db_manager, table_name):
    """Get data using centralized database manager - only rows without sentiment"""
    try:
        # Only get records where sentiment is NULL or empty AND ai_summary is not empty
        response = db_manager.client.table(table_name).select("link, ai_summary, date, sentiment").neq("ai_summary", "").or_("sentiment.is.null,sentiment.eq.").execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            # Filter out records that already have sentiment
            df = df[(df['sentiment'].isna()) | (df['sentiment'] == '') | (df['sentiment'].isnull())]
            print(f"📄 Loaded {len(df)} rows from {table_name} (only records without sentiment)")
            return df
        else:
            print(f"⚠️ No data found in {table_name} without sentiment")
            return pd.DataFrame()
    except Exception as e:
        print(f"❌ Error loading data from {table_name}: {e}")
        return pd.DataFrame()

# ====================== 6. Dự đoán và cập nhật DB ======================
def predict_and_update_sentiment(db_manager, table_name):
    """Predict sentiment and update database using centralized system"""
    global model, tokenizer, id2label
    
    # Load model if not already loaded
    if model is None:
        print("🔄 Loading sentiment analysis model...")
        model, tokenizer, id2label = load_sentiment_model()
        print("✅ Sentiment model loaded successfully")
    
    # Get data from database
    df = get_data_from_db(db_manager, table_name)
    if df.empty:
        print(f"⚠️ No articles to process in {table_name}")
        return set()

    updated_dates = set()
    count = 0
    start_time = None
    successful_updates = 0

    print(f"🚀 Starting sentiment analysis for {len(df)} articles in {table_name}...")

    for i, row in tqdm(df.iterrows(), total=len(df), desc=f"Processing {table_name}"):
        text = row["ai_summary"] if pd.notna(row["ai_summary"]) else ""
        if not text.strip():
            continue

        if count == 0:
            start_time = time.time()

        # Tokenize and predict
        inputs = tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=256
        )

        with torch.no_grad():
            outputs = model(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"]
            )
            predicted_class = torch.argmax(outputs, dim=1).item()

        sentiment = id2label[predicted_class]
        
        # Update database
        if update_sentiment_in_db(db_manager, table_name, row["link"], sentiment):
            successful_updates += 1
            
            # Track updated dates
            if "date" in row and pd.notna(row["date"]):
                updated_dates.add(str(row["date"]))

        count += 1
        if count == 10:
            elapsed = time.time() - start_time
            print(f"📊 Performance: {elapsed:.2f}s for 10 articles ({elapsed/10:.3f}s/article)")

    print(f"🎉 Sentiment analysis completed for {table_name}!")
    print(f"📈 Successfully updated: {successful_updates}/{len(df)} articles")
    return updated_dates

# ====================== 7. Sentiment Statistics Functions ======================
def get_sentiment_stats_by_date(db_manager, news_table, dates=None):
    """
    Calculate sentiment statistics by date from news table
    
    Args:
        db_manager: Database manager instance
        news_table: Name of the news table (e.g., 'FPT_News')
        dates: List of dates to process (if None, process all dates)
    
    Returns:
        DataFrame with columns: date, Positive, Negative, Neutral
    """
    try:
        # Build query - get ALL sentiment data from 2020 onwards only
        query = db_manager.client.table(news_table).select("date, sentiment").neq("sentiment", "").neq("sentiment", None).gte("date", "2020-01-01")
        
        print(f"📅 Processing sentiment data from 2020-01-01 onwards only")
        
        # If specific dates provided, only process those dates
        # If not, process all dates that have sentiment data (from 2020+)
        if dates:
            # Filter by specific dates but still maintain 2020+ filter
            date_list = list(dates) if isinstance(dates, set) else dates
            # Only include dates from 2020 onwards
            date_list = [d for d in date_list if d >= "2020-01-01"]
            if date_list:
                query = query.in_("date", date_list)
            else:
                print(f"⚠️ No dates from 2020+ to process")
                return pd.DataFrame()
        
        response = query.execute()
        
        if not response.data:
            print(f"⚠️ No sentiment data found in {news_table}")
            return pd.DataFrame()
        
        df = pd.DataFrame(response.data)
        
        # Group by date and count sentiments
        sentiment_stats = df.groupby(['date', 'sentiment']).size().unstack(fill_value=0)
        sentiment_stats = sentiment_stats.reset_index()
        
        # Ensure all sentiment columns exist
        for sentiment in ['Positive', 'Negative', 'Neutral']:
            if sentiment not in sentiment_stats.columns:
                sentiment_stats[sentiment] = 0
        
        print(f"📊 Calculated sentiment stats for {len(sentiment_stats)} dates in {news_table}")
        return sentiment_stats[['date', 'Positive', 'Negative', 'Neutral']]
        
    except Exception as e:
        print(f"❌ Error calculating sentiment stats for {news_table}: {e}")
        return pd.DataFrame()

def ensure_sentiment_columns_not_null(db_manager, stock_table):
    """
    Ensure all sentiment columns are 0 instead of NULL in stock table
    
    Args:
        db_manager: Database manager instance
        stock_table: Name of the stock table (e.g., 'FPT_Stock')
    """
    try:
        print(f"🔧 Ensuring sentiment columns are not NULL in {stock_table}")
        
        # Update any NULL values to 0
        result = db_manager.client.table(stock_table).update({
            "Positive": 0,
            "Negative": 0,
            "Neutral": 0
        }).or_("Positive.is.null,Negative.is.null,Neutral.is.null").execute()
        
        if result.data:
            print(f"✅ Updated {len(result.data)} records with NULL sentiment values to 0")
        else:
            print(f"✅ No NULL sentiment values found in {stock_table}")
            
    except Exception as e:
        print(f"❌ Error ensuring sentiment columns not NULL in {stock_table}: {e}")

def ensure_all_stock_sentiment_not_null(db_manager):
    """
    Ensure sentiment columns are not NULL for all stock tables
    
    Args:
        db_manager: Database manager instance
    """
    stock_codes = ["FPT", "GAS", "IMP", "VCB"]
    
    print(f"🔧 Ensuring all stock sentiment columns are not NULL")
    print("="*60)
    
    for stock_code in stock_codes:
        stock_table = f"{stock_code}_Stock"
        ensure_sentiment_columns_not_null(db_manager, stock_table)
    
    print(f"✅ All stock sentiment columns check completed")

def update_stock_sentiment_stats(db_manager, stock_table, sentiment_stats_df, reset_before_update=False):
    """
    Update stock table with sentiment statistics (CUMULATIVE - adds to existing values)
    
    Args:
        db_manager: Database manager instance
        stock_table: Name of the stock table (e.g., 'FPT_Stock')
        sentiment_stats_df: DataFrame with sentiment statistics
        reset_before_update: If True, reset sentiment columns to 0 before updating (for recalculate mode)
    """
    if sentiment_stats_df.empty:
        print(f"⚠️ No sentiment stats to update in {stock_table}")
        return 0
    
    updated_count = 0
    
    if reset_before_update:
        print(f"🔄 Resetting sentiment stats in {stock_table} before recalculation...")
        try:
            # Reset all sentiment columns to 0 for all rows
            reset_result = db_manager.client.table(stock_table).update({
                "Positive": 0,
                "Negative": 0,
                "Neutral": 0
            }).neq("id", 0).execute()  # Use id instead of date for non-empty filter
            print(f"✅ Reset sentiment stats for all dates in {stock_table}")
        except Exception as e:
            print(f"❌ Error resetting sentiment stats in {stock_table}: {e}")
    
    mode_text = "RESET & RECALCULATE" if reset_before_update else "CUMULATIVE"
    print(f"🔄 Updating sentiment stats in {stock_table} ({mode_text} mode)...")
    
    for _, row in tqdm(sentiment_stats_df.iterrows(), total=len(sentiment_stats_df), desc=f"Updating {stock_table}"):
        try:
            if reset_before_update:
                # In reset mode, directly set the values (no need to read current)
                result = db_manager.client.table(stock_table).update({
                    "Positive": int(row["Positive"]),
                    "Negative": int(row["Negative"]), 
                    "Neutral": int(row["Neutral"])
                }).eq("date", row["date"]).execute()
                
                if result.data:
                    updated_count += 1
                    print(f"✅ Set {row['date']}: P={int(row['Positive'])}, N={int(row['Negative'])}, Neu={int(row['Neutral'])}")
                else:
                    print(f"⚠️ No stock data found for date {row['date']} in {stock_table}")
            else:
                # Cumulative mode: add to existing values
                current_response = db_manager.client.table(stock_table).select("Positive, Negative, Neutral").eq("date", row["date"]).execute()
                
                if current_response.data and len(current_response.data) > 0:
                    # Get current values (handle None values and ensure they are integers)
                    current_data = current_response.data[0]
                    current_positive = int(current_data.get("Positive") or 0)
                    current_negative = int(current_data.get("Negative") or 0)  
                    current_neutral = int(current_data.get("Neutral") or 0)
                    
                    # Calculate new cumulative values
                    new_positive = current_positive + int(row["Positive"])
                    new_negative = current_negative + int(row["Negative"])
                    new_neutral = current_neutral + int(row["Neutral"])
                    
                    print(f"📊 {row['date']}: Current P={current_positive}, N={current_negative}, Neu={current_neutral}")
                    print(f"📈 {row['date']}: Adding P={int(row['Positive'])}, N={int(row['Negative'])}, Neu={int(row['Neutral'])}")
                    
                    # Update with cumulative values
                    result = db_manager.client.table(stock_table).update({
                        "Positive": new_positive,
                        "Negative": new_negative, 
                        "Neutral": new_neutral
                    }).eq("date", row["date"]).execute()
                    
                    if result.data:
                        updated_count += 1
                        print(f"✅ Updated {row['date']}: P={new_positive}, N={new_negative}, Neu={new_neutral}")
                    else:
                        print(f"❌ Failed to update {row['date']} in {stock_table}")
                else:
                    print(f"⚠️ No stock data found for date {row['date']} in {stock_table}")
                
        except Exception as e:
            print(f"❌ Error updating {row['date']} in {stock_table}: {e}")
    
    print(f"📈 Updated sentiment stats for {updated_count}/{len(sentiment_stats_df)} dates in {stock_table}")
    return updated_count

def aggregate_sentiment_for_trading_days(db_manager, stock_table, sentiment_stats_df):
    """
    Aggregate sentiment from non-trading days to the next trading day
    IMPORTANT: Always based on stock table dates for accurate trading day identification
    
    Args:
        db_manager: Database manager instance
        stock_table: Name of the stock table
        sentiment_stats_df: DataFrame with sentiment statistics by date
    
    Returns:
        DataFrame with aggregated sentiment stats for trading days only
    """
    if sentiment_stats_df.empty:
        return pd.DataFrame()
    
    print(f"🔄 Aggregating sentiment for non-trading days...")
    
    # Get all trading days from stock table (days that have stock data) - SORTED BY DATE DESC to get latest first
    try:
        # Query latest dates first, then reverse to get chronological order
        response = db_manager.client.table(stock_table).select("date").order("date", desc=True).execute()
        if not response.data:
            print(f"⚠️ No trading days found in {stock_table}")
            return pd.DataFrame()
        
        trading_days_df = pd.DataFrame(response.data)
        trading_days_df['date'] = pd.to_datetime(trading_days_df['date'])
        trading_days_df = trading_days_df.sort_values('date')  # Sort chronologically (oldest first)
        trading_days = set(trading_days_df['date'].dt.strftime('%Y-%m-%d'))
        trading_days_list = trading_days_df['date'].dt.strftime('%Y-%m-%d').tolist()
        
        print(f"📅 Found {len(trading_days)} trading days in {stock_table}")
        print(f"📅 Trading day range: {trading_days_list[0]} to {trading_days_list[-1]}")
        
    except Exception as e:
        print(f"❌ Error getting trading days from {stock_table}: {e}")
        return pd.DataFrame()
    
    # Convert sentiment dates to datetime for sorting
    sentiment_stats_df = sentiment_stats_df.copy()
    sentiment_stats_df['date'] = pd.to_datetime(sentiment_stats_df['date'])
    sentiment_stats_df = sentiment_stats_df.sort_values('date')
    
    aggregated_data = []
    pending_sentiment = {'Positive': 0, 'Negative': 0, 'Neutral': 0}
    
    # Process each sentiment date and find the next available trading day
    for _, row in sentiment_stats_df.iterrows():
        date_str = row['date'].strftime('%Y-%m-%d')
        sentiment_date = row['date']
        
        # Add current day sentiment to pending
        pending_sentiment['Positive'] += int(row['Positive'])
        pending_sentiment['Negative'] += int(row['Negative']) 
        pending_sentiment['Neutral'] += int(row['Neutral'])
        
        # If this is a trading day, aggregate all pending sentiment
        if date_str in trading_days:
            aggregated_data.append({
                'date': date_str,
                'Positive': pending_sentiment['Positive'],
                'Negative': pending_sentiment['Negative'],
                'Neutral': pending_sentiment['Neutral']
            })
            
            print(f"📈 Aggregated to trading day {date_str}: P={pending_sentiment['Positive']}, N={pending_sentiment['Negative']}, Neu={pending_sentiment['Neutral']}")
            
            # Reset pending sentiment
            pending_sentiment = {'Positive': 0, 'Negative': 0, 'Neutral': 0}
        else:
            # Find next trading day after this sentiment date
            next_trading_day = None
            for trading_day_str in trading_days_list:
                trading_day_date = pd.to_datetime(trading_day_str)
                if trading_day_date > sentiment_date:
                    next_trading_day = trading_day_str
                    break
            
            if next_trading_day:
                print(f"📅 Non-trading day {date_str}: P={int(row['Positive'])}, N={int(row['Negative'])}, Neu={int(row['Neutral'])} (pending for {next_trading_day})")
            else:
                print(f"📅 Non-trading day {date_str}: P={int(row['Positive'])}, N={int(row['Negative'])}, Neu={int(row['Neutral'])} (no future trading day)")
    
    # Handle any remaining pending sentiment for dates beyond the last trading day
    if any(pending_sentiment.values()):
        # Find the last trading day to assign remaining sentiment
        if trading_days_list:
            last_trading_day = trading_days_list[-1]
            
            # Check if we already have data for the last trading day, if so, add to it
            existing_data = None
            for i, data in enumerate(aggregated_data):
                if data['date'] == last_trading_day:
                    existing_data = i
                    break
            
            if existing_data is not None:
                # Add to existing last trading day
                aggregated_data[existing_data]['Positive'] += pending_sentiment['Positive']
                aggregated_data[existing_data]['Negative'] += pending_sentiment['Negative']
                aggregated_data[existing_data]['Neutral'] += pending_sentiment['Neutral']
                print(f"📈 Added remaining sentiment to last trading day {last_trading_day}: P={aggregated_data[existing_data]['Positive']}, N={aggregated_data[existing_data]['Negative']}, Neu={aggregated_data[existing_data]['Neutral']}")
            else:
                # Create new entry for last trading day
                aggregated_data.append({
                    'date': last_trading_day,
                    'Positive': pending_sentiment['Positive'],
                    'Negative': pending_sentiment['Negative'],
                    'Neutral': pending_sentiment['Neutral']
                })
                print(f"📈 Assigned remaining sentiment to last trading day {last_trading_day}: P={pending_sentiment['Positive']}, N={pending_sentiment['Negative']}, Neu={pending_sentiment['Neutral']}")
        else:
            print(f"⚠️ Remaining pending sentiment will be discarded (no trading days found)")
    
    if not aggregated_data:
        print(f"⚠️ No sentiment data aligned with trading days")
        return pd.DataFrame()
    
    result_df = pd.DataFrame(aggregated_data)
    print(f"✅ Aggregated sentiment for {len(result_df)} trading days")
    return result_df

def process_sentiment_to_stock_30days(db_manager, stock_code, updated_dates=None):
    """
    Process sentiment from news table and update stock table for LAST 30 DAYS
    This ensures proper aggregation of weekend/holiday sentiment to next trading day
    
    Args:
        db_manager: Database manager instance  
        stock_code: Stock code (e.g., 'FPT', 'GAS')
        updated_dates: Set of dates that were updated (trigger for 30-day recheck)
    """
    from datetime import datetime, timedelta
    
    news_table = f"{stock_code}_News"
    stock_table = f"{stock_code}_Stock"
    
    print(f"\n📊 Processing sentiment stats for {stock_code} (30-day window)")
    print(f"📋 News table: {news_table}")
    print(f"📈 Stock table: {stock_table}")
    
    # First, ensure all sentiment columns are 0 instead of NULL
    ensure_sentiment_columns_not_null(db_manager, stock_table)
    
    # Calculate 30-day window
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    
    print(f"🗓️ Processing 30-day window: {start_date} to {end_date}")
    
    # Get all sentiment statistics for last 30 days
    try:
        sentiment_response = db_manager.client.table(news_table).select(
            "date, sentiment"
        ).gte("date", start_date.strftime('%Y-%m-%d')).lte("date", end_date.strftime('%Y-%m-%d')).neq("sentiment", "").neq("sentiment", None).execute()
        
        if not sentiment_response.data:
            print(f"⚠️ No sentiment data found in last 30 days for {stock_code}")
            return 0
            
        # Convert to DataFrame and group by date and sentiment
        sentiment_df = pd.DataFrame(sentiment_response.data)
        
        # Group by date and sentiment, then count occurrences
        sentiment_counts = sentiment_df.groupby(['date', 'sentiment']).size().reset_index(name='count')
        
        # Pivot to get Positive, Negative, Neutral columns
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
                
        print(f"📊 Found sentiment data for {len(sentiment_stats)} days in last 30 days")
        
    except Exception as e:
        print(f"❌ Error getting sentiment stats for {stock_code}: {e}")
        return 0
    
    if sentiment_stats.empty:
        print(f"⚠️ No sentiment statistics to process for {stock_code}")
        return 0
    
    # Get trading days for last 30 days to reset sentiment first
    try:
        trading_response = db_manager.client.table(stock_table).select("date").gte("date", start_date.strftime('%Y-%m-%d')).lte("date", end_date.strftime('%Y-%m-%d')).execute()
        
        if trading_response.data:
            trading_dates = [row['date'] for row in trading_response.data]
            print(f"🔄 Resetting sentiment for {len(trading_dates)} trading days in 30-day window...")
            
            # Reset sentiment for these trading days
            for date_str in trading_dates:
                try:
                    db_manager.client.table(stock_table).update({
                        "Positive": 0,
                        "Negative": 0,
                        "Neutral": 0
                    }).eq("date", date_str).execute()
                except Exception as e:
                    print(f"⚠️ Error resetting {date_str}: {e}")
                    
            print(f"✅ Reset sentiment for {len(trading_dates)} trading days")
            
    except Exception as e:
        print(f"⚠️ Error getting trading days: {e}")
    
    # Aggregate sentiment for non-trading days to next trading day
    aggregated_sentiment_stats = aggregate_sentiment_for_trading_days(db_manager, stock_table, sentiment_stats)
    
    if aggregated_sentiment_stats.empty:
        print(f"⚠️ No aggregated sentiment statistics to update for {stock_code}")
        return 0
    
    # Update stock table with aggregated sentiment stats (NO reset since we already reset above)
    updated_count = update_stock_sentiment_stats(db_manager, stock_table, aggregated_sentiment_stats, reset_before_update=False)
    
    print(f"✅ Completed 30-day sentiment processing for {stock_code}")
    return updated_count

def process_sentiment_to_stock(db_manager, stock_code, updated_dates=None, recalculate_all=False):
    """
    Process sentiment from news table and update corresponding stock table
    
    Args:
        db_manager: Database manager instance  
        stock_code: Stock code (e.g., 'FPT', 'GAS')
        updated_dates: Set of dates that were updated (if None, process all)
        recalculate_all: If True, recalculate stats for all dates (not just updated ones)
    """
    # If we have updated dates, use the new 30-day processing logic
    if updated_dates and not recalculate_all:
        return process_sentiment_to_stock_30days(db_manager, stock_code, updated_dates)
    
    # Otherwise, use the original logic for full recalculation
    news_table = f"{stock_code}_News"
    stock_table = f"{stock_code}_Stock"
    
    print(f"\n📊 Processing sentiment stats for {stock_code}")
    print(f"📋 News table: {news_table}")
    print(f"📈 Stock table: {stock_table}")
    
    # First, ensure all sentiment columns are 0 instead of NULL
    ensure_sentiment_columns_not_null(db_manager, stock_table)
    
    # If recalculate_all or no updated_dates, process all dates
    dates_to_process = None if recalculate_all or not updated_dates else updated_dates
    
    if dates_to_process:
        print(f"🎯 Processing specific dates: {len(dates_to_process)} dates")
    else:
        print(f"🔄 Recalculating sentiment stats for all dates (2020+ only)")
    
    # Get sentiment statistics by date (2020+ only)
    sentiment_stats = get_sentiment_stats_by_date(db_manager, news_table, dates_to_process)
    
    if sentiment_stats.empty:
        print(f"⚠️ No sentiment statistics to process for {stock_code}")
        return 0
    
    # Aggregate sentiment for non-trading days to next trading day
    aggregated_sentiment_stats = aggregate_sentiment_for_trading_days(db_manager, stock_table, sentiment_stats)
    
    if aggregated_sentiment_stats.empty:
        print(f"⚠️ No aggregated sentiment statistics to update for {stock_code}")
        return 0
    
    # Update stock table with aggregated sentiment stats
    reset_mode = recalculate_all  # Reset before update when recalculating all
    updated_count = update_stock_sentiment_stats(db_manager, stock_table, aggregated_sentiment_stats, reset_mode)
    
    print(f"✅ Completed sentiment processing for {stock_code}")
    return updated_count

# ====================== 8. Main Functions ======================
def run_sentiment_analysis_pipeline(table_names=None, update_stock_tables=True, recalculate_all_stock=False):
    """
    Run sentiment analysis pipeline for specified tables
    
    Args:
        table_names: List of table names to process. If None, process all news tables.
        update_stock_tables: Whether to update stock tables with sentiment statistics
        recalculate_all_stock: If True, recalculate sentiment stats for all dates in stock tables
    """
    if table_names is None:
        # Default: process all stock news tables
        config = DatabaseConfig()
        table_names = [config.get_table_name(stock_code=code) for code in ["FPT", "GAS", "IMP", "VCB"]]
        table_names.append(config.get_table_name(is_general=True))  # Add General_News
    
    print("🚀 Starting SPA VIP Sentiment Analysis Pipeline")
    print(f"📋 Tables to process: {table_names}")
    
    db_manager = get_database_manager()
    total_updated_dates = set()
    stock_updates = {}
    
    # Phase 1: Predict sentiment and update news tables (only for records without sentiment)
    for table_name in table_names:
        print(f"\n📊 Processing table: {table_name}")
        try:
            updated_dates = predict_and_update_sentiment(db_manager, table_name)
            total_updated_dates.update(updated_dates)
            
            # Store updated dates for stock processing
            if table_name.endswith("_News") and table_name != "General_News":
                stock_code = table_name.replace("_News", "")
                stock_updates[stock_code] = updated_dates
            
            print(f"✅ Completed processing {table_name}")
        except Exception as e:
            print(f"❌ Error processing {table_name}: {e}")
    
    # Phase 2: Update stock tables with sentiment statistics
    if update_stock_tables:
        print(f"\n🏢 Phase 2: Updating Stock Tables with Sentiment Statistics")
        print("=" * 60)
        
        # Get all stock codes from news tables processed
        all_stock_codes = set()
        for table_name in table_names:
            if table_name.endswith("_News") and table_name != "General_News":
                all_stock_codes.add(table_name.replace("_News", ""))
        
        for stock_code in all_stock_codes:
            try:
                updated_dates = stock_updates.get(stock_code, set())
                
                # If recalculate_all_stock or there were new predictions, update stock table
                if recalculate_all_stock or updated_dates:
                    process_sentiment_to_stock(db_manager, stock_code, updated_dates, recalculate_all_stock)
                else:
                    print(f"⏭️ Skipping {stock_code} - no new predictions")
                    
            except Exception as e:
                print(f"❌ Error updating stock table for {stock_code}: {e}")
    
    # Close database connections
    db_manager.close_connections()
    
    print(f"\n🎉 Sentiment Analysis Pipeline Completed!")
    print(f"📈 Total dates updated: {len(total_updated_dates)}")
    if update_stock_tables:
        print(f"🏢 Stock tables processed: {list(stock_updates.keys())}")
    return total_updated_dates

def main_predict_sentiment_and_update_stock():
    """Legacy function - commented out for now, use new pipeline instead"""
    print("⚠️ This legacy function is disabled. Use run_sentiment_analysis_pipeline() instead.")
    
    # Original code commented out due to dependency on psycopg2
    # stock_codes = ["GAS", "FPT", "IMP", "VCB"]
    # db_manager = get_database_manager()
    
    # for code in stock_codes:
    #     engine = get_engine()
    #     conn = get_connection()
    #     news_table = f"{code}_News"
    #     stock_table = f"{code}_Stock"

    #     print(f"\n🔄 Processing {code}...")
    #     updated_dates = predict_and_update_sentiment(db_manager, news_table)
        
    #     if updated_dates:
    #         news_df = get_news_sentiment_by_dates(engine, news_table, updated_dates)
    #         stock_df = get_stock_data_by_dates(engine, stock_table, updated_dates)
    #         merged_df = news_df.rename(columns={"date": "date"})
    #         update_stock_table_by_dates(conn, stock_table, merged_df)

    #     conn.close()
    #     engine.dispose()
    
    # db_manager.close_connections()
    # print("🎉 Legacy pipeline completed!")

if __name__ == "__main__":
    # For backwards compatibility, run the new pipeline
    run_sentiment_analysis_pipeline()