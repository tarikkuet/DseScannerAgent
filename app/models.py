# app/models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# --- THE NEW ASSOCIATION TABLE ---
# This invisible table manages the Many-to-Many relationship
watchlist_stock_link = db.Table('watchlist_stock_link',
    db.Column('stock_id', db.Integer, db.ForeignKey('stock.id'), primary_key=True),
    db.Column('watchlist_id', db.Integer, db.ForeignKey('watchlist_group.id'), primary_key=True)
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
    company_name = db.Column(db.String(200), nullable=False)
    sector_id = db.Column(db.Integer, db.ForeignKey('sector.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    performances = db.relationship('DailyPerformance', backref='stock', lazy=True)
    indicators = db.relationship('DailyIndicator', backref='stock', lazy=True)
    
    # NEW: The relationship link back to our watchlists via the association table
    watchlists = db.relationship('WatchlistGroup', secondary=watchlist_stock_link, backref=db.backref('stocks', lazy='dynamic'))

# --- THE NEW WATCHLIST ARCHITECTURE ---
class WatchlistGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Note: We don't need a stock_id column here! The association table handles it.

class DailyPerformance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock.id'), nullable=False)
    trade_date = db.Column(db.Date, nullable=False)
    
    open_price = db.Column(db.Float, nullable=False)
    high_price = db.Column(db.Float, nullable=False)
    low_price = db.Column(db.Float, nullable=False)
    close_price = db.Column(db.Float, nullable=False)
    
    # NEW: Yesterday's Close Price (required for Change and Change %)
    ycp = db.Column(db.Float, nullable=True) 
    
    volume = db.Column(db.Integer, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('stock_id', 'trade_date', name='_perf_stock_date_uc'),
    )

class DailyIndicator(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock.id'), nullable=False)
    calc_date = db.Column(db.Date, nullable=False)
    rsi_14 = db.Column(db.Float, nullable=True)
    ema_9 = db.Column(db.Float, nullable=True)
    ema_20 = db.Column(db.Float, nullable=True)
    atr_14 = db.Column(db.Float, nullable=True)

    __table_args__ = (
        db.UniqueConstraint('stock_id', 'calc_date', name='_ind_stock_date_uc'),
    )