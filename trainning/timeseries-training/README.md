# Time Series Prediction for Stock Price with Sentiment Analysis

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-2.x-orange.svg)](https://tensorflow.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 📈 Overview

This project implements advanced deep learning models for predicting FPT Corporation stock prices using a combination of historical price data and sentiment analysis from news articles. The system employs multiple neural network architectures including LSTM, GRU, CNN-LSTM hybrid models, and Transformer networks to achieve accurate time series forecasting.

## 🎯 Features

- **Multi-Feature Time Series Prediction**: Combines stock price data with sentiment analysis (Positive, Negative, Neutral)
- **Multiple Model Architectures**: 
  - LSTM (Long Short-Term Memory)
  - GRU (Gated Recurrent Unit)
  - LSTM-GRU Ensemble
- **Flexible Window Sizes**: Support for different lookback windows (7, 15, 30 days)
- **Missing Data Simulation**: Test model robustness with various missing data scenarios
- **Comprehensive Evaluation**: Multiple metrics including RMSE, MAE, R², NMAE, Similarity Score

## 📊 Dataset

The project uses FPT Corporation stock data with the following features:
- **Date**: Trading date
- **Close Price**: Daily closing price (VNĐ)
- **Positive**: Number of positive news
- **Negative**: Number of negative news
- **Neutral**: Number of neutral news

**📁 Full Dataset & Models**: [Google Drive Folder](https://drive.google.com/drive/folders/1-_fSdZFITqVDNYU10o1_mHQbDXCAsHkD?usp=drive_link)
> Contains complete datasets, trained models (.keras files), training logs, and additional resources


## 🏗️ Project Structure

```
timeseries_04082025/
├── 3_feature/                          # 3-feature models (Close Price + Positive + Negative)
│   ├── CNN_LSTM/                       # CNN-LSTM hybrid models
│   │   ├── CNN_LSTM_missing10_window7.ipynb
│   │   ├── CNN_LSTM_missing10_window7.keras
│   │   └── ...
│   ├── GRU/                           # GRU models
│   ├── LSTM/                          # LSTM models
│   └── LSTM_GRU/                      # LSTM-GRU ensemble models
├── 4_feature/                          # 4-feature models (Close Price + Positive + Neutral + Negative)
│   ├── GRU/
│   ├── LSTM/
│   └── LSTM_GRU/

```

## 🚀 Quick Start

### Prerequisites

```bash
# Required packages
pip install pandas numpy tensorflow scikit-learn matplotlib
pip install sqlalchemy psycopg2-binary openpyxl
```


