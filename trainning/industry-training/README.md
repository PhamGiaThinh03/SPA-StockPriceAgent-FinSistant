# **Industry Classification for News**
[![Python](https://img.shields.io/badge/Python-3.9+-blue)](https://www.python.org/) [![TensorFlow](https://img.shields.io/badge/TensorFlow-2.x-orange)](https://www.tensorflow.org/) [![License: MIT](https://img.shields.io/badge/License-MIT-green)](https://opensource.org/licenses/MIT)


## 📈 Overview
This project implements deep learning models for classifying news articles into industry sectors.
It uses PhoBERT and XLM-RoBERTa for predicting the relevant industry for each news piece, 
helping investors analyze sector-wise market trends.

## 🎯 Features
- Multiple versions of training for comparison
- Models:
  - PhoBERT (summary & title classification)
  - XLM-RoBERTa (summary classification)
- Evaluation metrics:
  - Confusion Matrix
  - Precision-Recall Curve
  - ROC Curve
- Preprocessed datasets: CSV files for training and evaluation

## 📊 Dataset
Contains news articles with features:
- title: News headline
- summary: Short summary of article
- industry_label: Industry category (Finance, Technology, Energy, Healthcare, Other.)

## 💾 Dataset & Models
Full datasets and trained models are available here: 
[Google Drive Folder](https://drive.google.com/drive/folders/16ZrdzeprnF_FP-vom7iUfisB9nMcaJe3?usp=drive_link)

---

## 📁 Project Structure
```text
├── PhoBERT_model/
│   ├── training_for_summary/
│   │   ├── training_summary_industry_version*.ipynb
│   │   └── output_training_summary_industry_version*/    # CSV, PNG, logs
│   └── training_for_title/
│       ├── training_title_industry.ipynb
│       └── output_training-title-industry/                # CSV, PNG, logs
└── XLM_roberta_model/
    ├── training_xlm_roberta_industry_version*.ipynb
    └── output_training_xlm_roberta_industry_version*/    # JSON, PNG, logs
```
## 🚀 Quick Start
Prerequisites
```bash
pip install pandas numpy torch transformers scikit-learn matplotlib openpyxl
```