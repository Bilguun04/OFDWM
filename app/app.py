# filepath: /c:/Users/user/Documents/GitHub/OFDWM/app/app.py
from flask import Flask, render_template
from config import Config
from routes import app_routes
from extensions import mongo  # Updated import

app = Flask(__name__)
app.config.from_object(Config)
mongo.init_app(app)

# Register routes (URLs)
app.register_blueprint(app_routes)

if __name__ == "__main__":
    app.run(debug=True)