import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "portfolio.sqlite3"

companies = [
    ("Apple Inc.", "AAPL", "Technology", "USA", 3500.0, 394.3, 93.7, 28.0, 86.0, 200.0, 5.0, 12.0, 183.0),
    ("Microsoft Corp.", "MSFT", "Technology", "USA", 3200.0, 245.1, 88.1, 24.0, 91.0, 120.0, 4.0, 8.0, 108.0),
    ("NVIDIA Corp.", "NVDA", "Technology", "USA", 4500.0, 130.5, 72.9, 31.0, 82.0, 80.0, 3.0, 5.0, 72.0),
    ("Alphabet Inc.", "GOOGL", "Technology", "USA", 2800.0, 350.0, 100.1, 26.0, 88.0, 120.0, 5.0, 10.0, 105.0),
    ("Amazon.com Inc.", "AMZN", "Consumer", "USA", 2200.0, 638.0, 59.2, 34.0, 74.0, 350.0, 12.0, 35.0, 303.0),
    ("Tesla Inc.", "TSLA", "Automotive", "USA", 1100.0, 97.7, 7.1, 42.0, 69.0, 75.0, 30.0, 20.0, 25.0),
    ("JPMorgan Chase", "JPM", "Financials", "USA", 850.0, 177.0, 58.5, 22.0, 78.0, 90.0, 8.0, 15.0, 67.0),
    ("HSBC Holdings", "HSBC", "Financials", "UK", 190.0, 70.0, 25.0, 29.0, 72.0, 95.0, 7.0, 17.0, 71.0),
    ("Reliance Industries", "RELIANCE", "Energy", "India", 245.0, 119.0, 9.0, 37.0, 71.0, 150.0, 40.0, 30.0, 80.0),
    ("Tata Consultancy Services", "TCS", "Technology", "India", 205.0, 30.0, 5.0, 18.0, 89.0, 35.0, 3.0, 7.0, 25.0),
    ("Infosys Ltd.", "INFY", "Technology", "India", 105.0, 19.5, 3.2, 20.0, 87.0, 28.0, 2.0, 5.0, 21.0),
    ("HDFC Bank", "HDFCBANK", "Financials", "India", 175.0, 18.0, 4.0, 21.0, 81.0, 22.0, 2.0, 4.0, 16.0),
    ("Toyota Motor Corp.", "TM", "Automotive", "Japan", 310.0, 315.0, 30.0, 25.0, 76.0, 450.0, 70.0, 90.0, 290.0),
    ("Shell plc", "SHEL", "Energy", "UK", 210.0, 323.0, 23.0, 48.0, 61.0, 1200.0, 70.0, 110.0, 1020.0),
    ("Siemens AG", "SIEGY", "Industrials", "Germany", 155.0, 90.0, 10.0, 19.0, 84.0, 180.0, 20.0, 30.0, 130.0),
]

with sqlite3.connect(DB_PATH) as conn:
    conn.execute("DROP TABLE IF EXISTS companies")

    conn.execute("""
        CREATE TABLE companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            ticker TEXT NOT NULL UNIQUE,
            sector TEXT NOT NULL,
            country TEXT NOT NULL,
            market_value REAL NOT NULL,
            revenue REAL NOT NULL,
            profit REAL NOT NULL,
            risk_score REAL NOT NULL,
            esg_score REAL NOT NULL,
            carbon_emissions REAL NOT NULL,
            scope1_emissions REAL NOT NULL,
            scope2_emissions REAL NOT NULL,
            scope3_emissions REAL NOT NULL
        )
    """)

    conn.executemany("""
        INSERT INTO companies (
            company_name,
            ticker,
            sector,
            country,
            market_value,
            revenue,
            profit,
            risk_score,
            esg_score,
            carbon_emissions,
            scope1_emissions,
            scope2_emissions,
            scope3_emissions
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, companies)

    conn.commit()

print(f"Created portfolio database: {DB_PATH}")
print(f"Inserted companies: {len(companies)}")