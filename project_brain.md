# DseScannerAgent - Project Architecture & Context

## 🎯 Project Overview
A local, Flask-based financial data engineering pipeline and dashboard built to track, scrape, and analyze the Dhaka Stock Exchange (DSE). It features an automated reconciliation engine, robust SQLite database with strict constraints, and a master data management UI.

---

## 🗄️ Database Schema (`app/models.py`)
*Note: Uses SQLAlchemy. Designed with strict constraints to prevent duplicate financial data.*
```python
from app import db
from datetime import datetime

# Association Table for Many-to-Many Watchlist relationship
watchlist_stocks = db.Table('watchlist_stocks',
    db.Column('watchlist_id', db.Integer, db.ForeignKey('watchlist.id'), primary_key=True),
    db.Column('stock_id', db.Integer, db.ForeignKey('stock.id'), primary_key=True)
)

class Sector(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    stocks = db.relationship('Stock', backref='sector', lazy=True)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(10), unique=True, nullable=False)
    stocks = db.relationship('Stock', backref='category', lazy=True)

class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    sector_id = db.Column(db.Integer, db.ForeignKey('sector.id'), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    
    daily_performances = db.relationship('DailyPerformance', backref='stock', lazy=True)
    intraday_ticks = db.relationship('IntradayTick', backref='stock', lazy=True)

class Watchlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    stocks = db.relationship('Stock', secondary=watchlist_stocks, lazy='subquery',
        backref=db.backref('watchlists', lazy=True))

class DailyPerformance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock.id'), nullable=False)
    trade_date = db.Column(db.Date, nullable=False)
    
    open_price = db.Column(db.Float, nullable=False)
    high_price = db.Column(db.Float, nullable=False)
    low_price = db.Column(db.Float, nullable=False)
    close_price = db.Column(db.Float, nullable=False)
    ycp = db.Column(db.Float, nullable=True) # Yesterday's Close Price
    volume = db.Column(db.Integer, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('stock_id', 'trade_date', name='_perf_stock_date_uc'),
    )

class IntradayTick(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    current_price = db.Column(db.Float, nullable=False)
    volume = db.Column(db.Integer, default=0)




⚙️ Core Scripts & Pipeline
1. Initialization & Master Data
reset_db.py: The "nuclear option." Drops the entire SQLite database and recreates all tables from scratch.

dse_initializer.py / update_master_data.py: Scrapes the DSE to build the foundational Stock, Sector, and Category tables.

2. Historical Data Scrapers (The "Time Machine")
seed_dse_archive.py: A bulk web scraper that targets the DSE archive. It dynamically maps HTML tables, sanitizes strings into floats, and walks backward day-by-day (skipping Fridays/Saturdays) to build historical DailyPerformance data. Tracks timeouts in a failed_dates.txt file.

3. Data Reconciliation Engine
smart_sync.py: The CLI synchronization script. Compares the earliest and latest dates in the local database, identifies missing weekdays, and surgically fetches only the missing data to fill gaps without wasting API calls.

retry_failures.py: Reads failed_dates.txt line-by-line to re-attempt fetching days that suffered network timeouts.

4. Application Routing (app/routes.py)
/data_management: UI to view and manage Stocks, Sectors, Categories, and Watchlists.

/data_health: The visual Reconciliation Engine dashboard.

/api/check_gaps: Analyzes the database and returns a JSON list of missing trading days.

/api/sync_day: Receives a POST request with a specific date and triggers a targeted scrape to heal the database. Uses a lazy import to prevent circular dependencies.

5. Maintenance
upgrade_tables.py: A surgical script used to drop and recreate specific tables (like DailyPerformance) when columns change, without destroying Master Data.