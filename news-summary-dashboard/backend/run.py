from app.routes import app

if __name__ == '__main__':
    # Run app on host 0.0.0.0 to allow access from outside the container (if using Docker)
    # port=5000 is a common default port for Flask
    # debug=True to auto-restart server when code changes
    app.run(host='0.0.0.0', port=5000, debug=True)