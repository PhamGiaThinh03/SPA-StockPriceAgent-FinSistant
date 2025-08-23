# 🚀 SPA VIP - Vietnamese Stock News Processing System

Automated Vietnamese financial news processing pipeline with AI-powered analysis for stock market insights.

## 📁 Project Structure

```
SPA_AI/
├── 📁 crawl/                    # News data collection
├── 📁 summarization/            # AI text summarization
├── 📁 sentiment/                # Sentiment analysis
├── 📁 timeseries/              # Price prediction
├── 📁 industry/                # Industry classification
├── 📁 database/                # Database management
├── 📁 model_AI/                # AI models (download required)
├── main.py                     # Main controller
└── logs/                       # System logs
```

## 🎯 Features

- **News Crawling**: Automated collection from Vietnamese financial sources
- **AI Summarization**: ViT5-based Vietnamese text summarization
- **Sentiment Analysis**: PhoBERT sentiment classification
- **Price Prediction**: LSTM-based stock price forecasting
- **Industry Classification**: Automated news categorization
- **Database Integration**: Centralized Supabase data management

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
pip install -r summarization/requirements.txt
```

### 2. Download AI Models
Download required models from: [Google Drive Link](https://drive.google.com/drive/folders/1Qzf2ZwtcBZEEmwzUaGV4gydIm-APgdT8?usp=drive_link)

Extract to `model_AI/` folder with this structure:
```
model_AI/
├── sentiment_model/
├── summarization_model/
├── timeseries_model/
└── industry_model/
```

### 3. Test Connection
```bash
python database/test_connection.py
```

### 4. Run System
```bash
# Full pipeline
python main.py 

```

## 📊 Database Schema

### News Tables
- Stock-specific: `FPT_News`, `GAS_News`, `IMP_News`, `VCB_News`
- General: `General_News`

### Stock Price Tables
- Price data: `FPT_Stock`, `GAS_Stock`, `IMP_Stock`, `VCB_Stock`

Key fields: `title`, `content`, `date`, `ai_summary`, `sentiment`, `industry`

## 🔄 Workflow

1. **Crawl** → Collect news from Vietnamese sources
2. **Summarize** → Generate AI summaries
3. **Analyze** → Sentiment classification
4. **Predict** → Stock price forecasting
5. **Classify** → Industry categorization

## 🛠️ Troubleshooting

```bash
# Test database connection
python database/test_connection.py

# Check system status
python main.py --status


```

## � Support

For issues or questions, run:
```bash
python main.py --help
```
