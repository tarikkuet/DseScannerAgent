# DseScannerAgent - System Architecture

This document outlines the core application architecture and data flow for the DseScannerAgent. The application follows the **Model-View-Controller (MVC)** design pattern to ensure separation of concerns and maintainability.

## Application Data Flow

The following sequence diagram illustrates the lifecycle of a user request (e.g., loading the dashboard with active filters) and how the application's core components interact to deliver the final interface.
```mermaid
sequenceDiagram
    participant User as User's Browser
    participant Route as routes.py (Controller)
    participant Model as models.py (Model)
    participant DB as SQLite Database
    participant View as index.html (View)

    User->>Route: 1. HTTP GET / POST Request (e.g., "?sector=Bank")
    activate Route
    Route->>Model: 2. Queries data using SQLAlchemy ORM
    activate Model
    Model->>DB: 3. Translates Python queries to SQL
    DB-->>Model: 4. Returns raw database rows
    Model-->>Route: 5. Returns structured Python objects
    deactivate Model
    Route->>View: 6. Passes data dictionaries to Jinja2 template
    activate View
    View-->>Route: 7. Renders the final HTML layout
    deactivate View
    Route-->>User: 8. Sends finished HTML page to display
    deactivate Route



Core Components (The MVC Pattern)
1. The Model (app/models.py)
This is the data governance layer. It defines the structure of the database tables (Stocks, Sectors, Watchlists) using SQLAlchemy. It is strictly responsible for data integrity and relationships. It does not contain any business logic or UI code.

2. The Controller (app/routes.py)
This is the "brain" of the application. It receives incoming web requests, determines what data is needed, queries the Models, and decides which View to render. It handles all forms, filtering logic, and data manipulation before passing the results to the frontend.

3. The View (app/templates/)
This is the presentation layer, built using HTML, Bootstrap 5, and Jinja2 templating. It is designed to be "dumb"—it does not query the database directly or make complex business decisions. It simply takes the data provided by the Controller and formats it into the user interface (tables, charts, and modals).