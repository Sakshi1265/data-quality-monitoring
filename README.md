
# Data Quality Monitoring System

## Project Overview
This project monitors data quality in CSV files
using Python, Pandas and SQLite.

## Technologies Used
- Python
- Pandas
- NumPy
- SQL
- SQLite
- CSV

## Project Features
- CSV data ingestion
- Data validation
- Duplicate record detection
- Missing value detection
- Baseline profiling
- Data quality alerts
- Freshness monitoring
- Rejected records tracking
- SQLite database storage

## Project Structure

data_quality_monitoring/
- data/
- reports/
- generate_data.py
- main.py
- README.md

## How to Run

1. Install dependencies:
   pip install pandas numpy

2. Generate sample datasets:
   python generate_data.py

3. Run the pipeline:
   python main.py

## Expected Output
- Baseline profile
- Data quality alerts
- Valid records
- Rejected records
- Pipeline execution status
