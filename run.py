from app import create_app

# Create the application instance using our factory
app = create_app()

if __name__ == '__main__':
    # Start the Flask development server
    app.run(debug=True)