# ETRM Case Study  

Prototype trade ingestion and monitoring system built as part of the ETRM Developer case study.  

## 📂 Project Structure  
- **etl/** → Python scripts for loading and normalizing broker trades  
- **sql/** → Schema and views (SQLite compatible)  
- **powerbi/** → Power BI report files (`.pbix`)  
- **exports/** → Sample output files / exports  
- **data/** → Raw input files (e.g., broker positions)  

## 🚀 Phase 1 Deliverables  
- ✅ Data ingestion & normalization with SQLite  
- ✅ Trade & position aggregation (`views_positions.sql`)  
- ✅ Power BI dashboards  
  - Portfolio Overview  
  - Trade & Position Details  
  - Risk Dashboard  

## 📊 Outputs  
- **ETRM_Report.pdf** – exported dashboard PDF  
- **ETRM_Report.pbix** – interactive Power BI file  

## ▶️ How to Run  
1. Install requirements:  
   ```bash
   pip install -r requirements.txt
   
2.Load raw data into SQLite using scripts in **etl/**.

3.Apply schema + views in **sql/**.

4.Open `.pbix` in Power BI to explore dashboards.

## ⚙️Tech Stack
**Python (ETL)/**

**SQLite (database)/**

**Power BI (reporting)/**
