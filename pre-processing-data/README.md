
# Preprocessing and exploratory analysis of news data for the SPA Stock Price Agent project.

## Contents

- **EDA_data.ipynb**: Exploratory Data Analysis (EDA) for news datasets. Includes:
  - Loading raw and processed news data from Excel files.
  - Visualizing distributions of title/content/summary lengths.
  - Checking and visualizing missing data.
  - Industry and sentiment label distributions (pie charts, bar charts).
  - Keyword analysis (unigrams, bigrams, word clouds by industry/sentiment).
  - Sample examples for each industry and sentiment.

- **remove_text.ipynb**: Text cleaning for news articles. Includes:
  - Loading news data from Excel.
  - Removing boilerplate, copyright, and unwanted segments using regex patterns.
  - Saving cleaned results to a new Excel file.

## Usage

1. Open the notebooks in Jupyter or VS Code.
2. Update file paths to match your local or cloud storage if needed.
3. Run cells sequentially for data loading, cleaning, and analysis.

## Requirements

- Python 3.x
- pandas, numpy, matplotlib, seaborn, wordcloud, missingno

Install required packages with:
```python
!pip install pandas numpy matplotlib seaborn wordcloud missingno
```

## Notes
- Data files referenced in the notebooks are stored in Google Drive. Update paths as needed for your environment.
- Outputs include visualizations and cleaned data files for further processing.
