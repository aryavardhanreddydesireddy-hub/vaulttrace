from app import app, initialize_database

initialize_database()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)