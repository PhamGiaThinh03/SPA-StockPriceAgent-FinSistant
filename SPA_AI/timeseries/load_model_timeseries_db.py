import pandas as pd
import numpy as np
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler
from datetime import timedelta
import os
import sys

# Add parent directory for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("⚠️ Supabase not installed. Install with: pip install supabase")

# Try to import centralized database (optional for backwards compatibility)
try:
    from database import SupabaseManager, DatabaseConfig
    CENTRALIZED_DB_AVAILABLE = True
except ImportError:
    CENTRALIZED_DB_AVAILABLE = False


class StockPredictor:
    DEFAULT_SUPABASE_URL = "https://baenxyqklayjtlbmubxe.supabase.co"
    DEFAULT_SUPABASE_KEY = "sb_secret_4Mj3OwBW9VlbhVU6bVrfLA_1olLCYpp"

    def __init__(self, model_path, supabase_config, use_centralized_db=True):
        self.model_path = model_path
        self.supabase_config = supabase_config
        self.model = None
        self.scaler = MinMaxScaler()
        self.window_size = 15  # ✅ Lấy đúng 15 ngày
        self.features = ["Giá đóng cửa", "Positive", "Negative"]
        self.use_centralized_db = use_centralized_db

        # Prioritize centralized database if available
        if use_centralized_db and CENTRALIZED_DB_AVAILABLE:
            try:
                self.db_manager = SupabaseManager()
                self.supabase = self.db_manager.client
                self.table_name = supabase_config["table_name"]
                print(f"✅ Using centralized database for table: {self.table_name}")
            except Exception as e:
                print(f"⚠️ Failed to use centralized database, falling back: {e}")
                self.use_centralized_db = False
                self._setup_direct_connection(supabase_config)
        else:
            self._setup_direct_connection(supabase_config)

    def _setup_direct_connection(self, supabase_config):
        """Setup direct supabase connection as fallback"""
        if SUPABASE_AVAILABLE:
            self.supabase: Client = create_client(
                supabase_config["url"], supabase_config["key"]
            )
            self.table_name = supabase_config["table_name"]
            print(f"⚠️ Using direct connection for table: {self.table_name}")
        else:
            self.supabase = None

    @classmethod
    def create_default_supabase_config(cls, table_name):
        return {
            "url": cls.DEFAULT_SUPABASE_URL,
            "key": cls.DEFAULT_SUPABASE_KEY,
            "table_name": table_name,
        }

    def load_model(self):
        try:
            self.model = tf.keras.models.load_model(self.model_path)
            print(f"✅ Model loaded: {self.model_path}")
            return True
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            return False

    def load_last_window_data(self):
        """Lấy dữ liệu window_size ngày gần nhất có close_price (15 ngày cho model hiện tại)"""
        if not self.supabase:
            print("❌ Supabase client not initialized!")
            return None

        try:
            response = (
                self.supabase.table(self.table_name)
                .select("*")
                .neq("close_price", "")
                .not_.is_("close_price", "null")
                .order("date", desc=True)
                .limit(self.window_size)  # Sử dụng window_size thay vì hardcode 15
                .execute()
            )

            if not response.data:
                print("❌ Không có dữ liệu close_price!")
                return None

            df = pd.DataFrame(response.data)
            df["Ngày"] = pd.to_datetime(df["date"])
            df["Giá đóng cửa"] = pd.to_numeric(
                df["close_price"].astype(str).str.replace(",", ""),
                errors="coerce",
            )

            df = df.sort_values("Ngày").reset_index(drop=True)

            # Xử lý sentiment - đảm bảo tất cả columns có giá trị số
            for col in ["Positive", "Neutral", "Negative"]:
                if col not in df.columns:
                    df[col] = 0
                else:
                    df[col] = (
                        pd.to_numeric(df[col].replace("", "0"), errors="coerce")
                        .fillna(0)
                    )

            print(f"✅ Lấy thành công {len(df)} ngày gần nhất (window_size={self.window_size})")
            
            # Hiển thị chi tiết 15 ngày như yêu cầu
            print("\n📋 CHI TIẾT 15 NGÀY:")
            print("-" * 90)
            print(f"{'STT':<4} {'Ngày':<12} {'Giá đóng cửa':<15} {'Positive':<10} {'Neutral':<10} {'Negative':<10}")
            print("-" * 90)
            
            for idx, row in df.iterrows():
                stt = idx + 1
                ngay = row['Ngày'].strftime('%Y-%m-%d')
                gia = f"{row['Giá đóng cửa']:,.0f}"
                pos = f"{row['Positive']:.0f}"
                neu = f"{row['Neutral']:.0f}"
                neg = f"{row['Negative']:.0f}"
                
                print(f"{stt:<4} {ngay:<12} {gia:<15} {pos:<10} {neu:<10} {neg:<10}")
            
            print("-" * 90)
            return df

        except Exception as e:
            print(f"❌ Error loading last days: {e}")
            return None

    def fit_scaler(self, df):
        scaled = self.scaler.fit_transform(df[self.features])
        return scaled

    def predict_next_10_days(self, df):
        if self.model is None:
            print("❌ Model not loaded!")
            return None, None

        scaled_data = self.fit_scaler(df)
        last_window = scaled_data[-self.window_size:].tolist()
        predictions_scaled = []

        for _ in range(10):
            x_input = np.array([last_window])
            pred = self.model.predict(x_input, verbose=0)[0][0]
            next_input = [pred, 0, 0]
            last_window.append(next_input)
            last_window.pop(0)
            predictions_scaled.append([pred, 0, 0])

        predicted_prices = self.scaler.inverse_transform(
            np.array(predictions_scaled)
        )[:, 0]

        last_date = df["Ngày"].iloc[-1]
        future_dates = [last_date + timedelta(days=i + 1) for i in range(10)]

        return future_dates, predicted_prices

    def update_existing_predictions(self, prediction_dates, predicted_prices):
        if not self.supabase:
            print("❌ Supabase client not initialized!")
            return False

        updated, inserted = 0, 0

        for date, price in zip(prediction_dates, predicted_prices):
            date_str = date.strftime("%Y-%m-%d")

            existing = (
                self.supabase.table(self.table_name)
                .select("id")
                .eq("date", date_str)
                .execute()
            )

            if existing.data:
                self.supabase.table(self.table_name).update(
                    {"predict_price": f"{price:,.0f}"}
                ).eq("date", date_str).execute()
                updated += 1
            else:
                record = {
                    "date": date_str,
                    "open_price": "",
                    "high_price": "",
                    "low_price": "",
                    "close_price": "",
                    "change": "",
                    "change_pct": "",
                    "volume": "",
                    "Positive": "",
                    "Neutral": "",
                    "Negative": "",
                    "predict_price": f"{int(price):,}",
                }
                self.supabase.table(self.table_name).insert(record).execute()
                inserted += 1

        print(f"✅ Updated: {updated}, Inserted: {inserted}")
        return True


def run_prediction_for_table(model_path, table_name):
    """
    Run prediction for a single table
    
    Args:
        model_path: Path to the model file
        table_name: Name of the table to predict (e.g., 'GAS_Stock')
    """
    config = StockPredictor.create_default_supabase_config(table_name)
    predictor = StockPredictor(model_path, config)

    if not predictor.load_model():
        return False

    df_last_days = predictor.load_last_window_data()
    if df_last_days is None or len(df_last_days) < predictor.window_size:
        print(f"❌ Không đủ dữ liệu để dự đoán! Cần ít nhất {predictor.window_size} ngày, có {len(df_last_days) if df_last_days is not None else 0} ngày")
        return False

    future_dates, pred_prices = predictor.predict_next_10_days(df_last_days)

    if future_dates is not None:
        success = predictor.update_existing_predictions(future_dates, pred_prices)
        print(f"\n📈 Dự đoán 10 ngày tiếp theo cho {table_name}:")
        for d, p in zip(future_dates, pred_prices):
            print(f"{d.strftime('%Y-%m-%d')}: {p:,.0f} VND")
        return success
    
    return False


def main():
    """Main function for standalone testing"""
    # Configuration - use absolute path to model
    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(current_dir, "..", "model_AI", "timeseries_model", "model_lstm", "LSTM_missing10_window15.keras")
    
    print(f"🔍 Model path: {model_path}")
    print(f"🔍 Model exists: {os.path.exists(model_path)}")
    
    # Test with multiple tables
    tables = ["FPT_Stock", "GAS_Stock", "IMP_Stock", "VCB_Stock"]
    
    print("\n🚀 SPA VIP TIMESERIES PREDICTION")
    print("="*60)
    
    successful_predictions = 0
    total_tables = len(tables)
    
    for table in tables:
        print("\n" + "=" * 50)
        print(f"🚀 Đang xử lý {table}")
        print("=" * 50)
        
        try:
            success = run_prediction_for_table(model_path, table)
            if success:
                successful_predictions += 1
                print(f"✅ {table}: Dự đoán thành công")
            else:
                print(f"❌ {table}: Dự đoán thất bại")
        except Exception as e:
            print(f"❌ {table}: Lỗi - {e}")
    
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    print(f"✅ Successful: {successful_predictions}/{total_tables}")
    print(f"❌ Failed: {total_tables - successful_predictions}/{total_tables}")
    print(f"📈 Success rate: {successful_predictions/total_tables*100:.1f}%")


if __name__ == "__main__":
    main()
