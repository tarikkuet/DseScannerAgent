# app/routes.py
from flask import render_template, request,redirect, url_for
from app.models import db, Sector, Category, Stock, DailyPerformance, WatchlistGroup



def register_routes(app):
    @app.route('/')
    def index():
        # 1. Get all 4 filter parameters from the URL
        selected_ticker_id = request.args.get('ticker')
        selected_cat = request.args.get('category')
        selected_sector = request.args.get('sector')
        selected_watchlist = request.args.get('watchlist')

        # 2. Base query
        query = Stock.query

        # 3. Apply filters dynamically
        if selected_ticker_id:
            query = query.filter(Stock.id == selected_ticker_id)
        if selected_cat:
            query = query.join(Category).filter(Category.name == selected_cat)
        if selected_sector:
            query = query.join(Sector).filter(Sector.name == selected_sector)
        if selected_watchlist:
            # Filter via the new Many-to-Many association table!
            query = query.join(Stock.watchlists).filter(WatchlistGroup.id == selected_watchlist)

        # Execute the query
        stocks = query.all()

        # 4. Get the latest prices
        latest_prices = {}
        for stock in stocks:
            latest_record = DailyPerformance.query.filter_by(stock_id=stock.id).order_by(DailyPerformance.trade_date.desc()).first()
            latest_prices[stock.id] = latest_record

        # 5. Data needed to populate the Filter Dropdowns
        all_stocks = Stock.query.order_by(Stock.ticker).all()
        sectors = Sector.query.all()
        categories = Category.query.all()
        watchlists = WatchlistGroup.query.all()

        return render_template(
            'index.html', 
            stocks=stocks,
            latest_prices=latest_prices,
            all_stocks=all_stocks,
            sectors=sectors,
            categories=categories,
            watchlists=watchlists,
            selected_ticker_id=selected_ticker_id,
            selected_cat=selected_cat,
            selected_sector=selected_sector,
            selected_watchlist=selected_watchlist
        )
    # --- NEW ROUTE: Manage Watchlists ---
    @app.route('/manage_watchlist', methods=['POST'])
    def manage_watchlist():
        # Get the form data
        action = request.form.get('action') # Will be 'save' or 'delete'
        watchlist_id = request.form.get('watchlist_id')
        name = request.form.get('name')
        description = request.form.get('description')
        
        # request.form.getlist() automatically grabs all selected items from a multi-select!
        stock_ids = request.form.getlist('stocks') 

        if action == 'delete' and watchlist_id:
            # Delete the entire watchlist (SQLAlchemy handles unlinking the stocks automatically)
            wl = WatchlistGroup.query.get(watchlist_id)
            if wl:
                db.session.delete(wl)
                db.session.commit()

        elif action == 'save' and name:
            if watchlist_id:
                # Update existing watchlist
                wl = WatchlistGroup.query.get(watchlist_id)
                wl.name = name
                wl.description = description
            else:
                # Create a brand new watchlist
                wl = WatchlistGroup(name=name, description=description)
                db.session.add(wl)

            # This is the magic of Many-to-Many! We just wipe the list and give it the new one.
            wl.stocks = [] 
            for sid in stock_ids:
                stock = Stock.query.get(sid)
                if stock:
                    wl.stocks.append(stock)
            
            db.session.commit()

        # Redirect back to the dashboard immediately
        return redirect(request.referrer or url_for('index'))