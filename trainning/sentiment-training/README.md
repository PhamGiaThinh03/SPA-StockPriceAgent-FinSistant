# **Sentiment Classification for News**
[![Python](https://img.shields.io/badge/Python-3.9+-blue)](https://www.python.org/) [![TensorFlow](https://img.shields.io/badge/TensorFlow-2.x-orange)](https://www.tensorflow.org/) [![License: MIT](https://img.shields.io/badge/License-MIT-green)](https://opensource.org/licenses/MIT)


## 📈 Overview
This project implements deep learning models for classifying the sentiment of news articles 
as Positive, Negative, or Neutral. It uses PhoBERT and XLM-RoBERTa models for accurate 
prediction to support investors and analysts in evaluating market sentiment trends.

## 🎯 Features
- Multi-Version Training: Multiple versions of models for comparison
- Models:
  - PhoBERT (summary & title sentiment classification)
  - XLM-RoBERTa (summary sentiment classification)
- Evaluation metrics:
  - Confusion Matrix
  - Precision-Recall Curve
  - ROC Curve
- Preprocessed Datasets: CSV files for training and evaluation

## 📊 Dataset
Contains news articles with features:
- title: News headline
- summary: Short summary of the article
- sentiment_label: Sentiment (Positive, Negative, Neutral)

---

## 📁 Project Structure
```text
├── PhoBERT_model/
│   ├── training_for_summary/
│   │   ├── training_summary_sentiment_version*.ipynb
│   │   └── output_training_summary_sentiment_version*/    # CSV, PNG, logs
│   └── training_for_title/
│       ├── training_title_sentiment.ipynb
│       └── output_training-title-sentiment/               # CSV, PNG, logs
└── XLM_roberta_model/
    ├── training_xlm_roberta_sentiment_version*.ipynb
    └── output_training_xlm_roberta_sentiment_version*/    # JSON, PNG, logs
```
## 🚀 Quick Start
Prerequisites
```bash
pip install pandas numpy torch transformers scikit-learn matplotlib openpyxl
```