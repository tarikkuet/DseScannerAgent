# DseScannerAgent - Database Architecture

This document outlines the SQLite database schema and entity relationships for the DseScannerAgent.

## Entity Relationship Diagram (ERD)
```mermaid
erDiagram
    SECTOR ||--o{ STOCK : contains
    CATEGORY ||--o{ STOCK : categorizes
    STOCK ||--o{ DAILY_PERFORMANCE : tracks_price
    STOCK ||--o{ DAILY_INDICATOR : calculates_math
    STOCK }o--o{ WATCHLIST_GROUP : belongs_to

    SECTOR {
        int id PK
        string name "Unique"
    }
    CATEGORY {
        int id PK
        string name "A, B, N, Z"
    }
    STOCK {
        int id PK
        string ticker "Unique"
        string company_name
        int sector_id FK
        int category_id FK
    }
    DAILY_PERFORMANCE {
        int id PK
        int stock_id FK
        date trade_date
        float open_price
        float high_price
        float low_price
        float close_price
        float ycp "Yesterday Close Price"
        int volume
    }
    DAILY_INDICATOR {
        int id PK
        int stock_id FK
        date calc_date
        float rsi_14
        float ema_9
        float ema_20
        float atr_14
    }
    WATCHLIST_GROUP {
        int id PK
        string name "Unique"
        text description
        datetime created_at
    }
    WATCHLIST_STOCK_LINK {
        int stock_id FK
        int watchlist_id FK
    }
```


Core Tables
1. Structural Data
Sector: Master list of DSE sectors (e.g., Bank, Engineering).

Category: Master list of DSE trading categories (A, B, N, Z).

Stock: The core entity. Every stock belongs to exactly one Sector and one Category.

2. Market Data
DailyPerformance: Stores daily OHLCV (Open, High, Low, Close, Volume) data. Includes ycp for calculating daily change metrics. Enforces a Unique Constraint on (stock_id, trade_date) to prevent duplicate data.

DailyIndicator: Stores pre-calculated technical metrics (RSI, EMA) to ensure UI performance remains fast without recalculating on the fly.

3. User Configuration
WatchlistGroup: Defines custom technical setups or lists created by the user.

watchlist_stock_link: An invisible association table that allows a Many-to-Many relationship. This allows one Stock to exist in multiple Watchlists simultaneously without duplicating records.