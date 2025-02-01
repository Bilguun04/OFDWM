from flask import Flask
from config import Config
from routes import app_routes
from flask_pymongo import PyMongo

app = Flask(__name__)
app.config.from_object(Config)  # Load configurations
mongo = PyMongo(app)  # Connect to MongoDB

# Register routes (URLs)
app.register_blueprint(app_routes)

if __name__ == "__main__":
    app.run(debug=True)