from flask import Blueprint, request, jsonify, render_template
import pandas as pd
from models import FirefighterModel
from config import Config
import os

app_routes = Blueprint("app_routes", __name__)

def allowed_file(filename):
    """Check if the file is a CSV."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@app_routes.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app_routes.route("/upload", methods=["POST"])
def upload_csv():
    """Handles CSV file uploads."""
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files["file"]
    
    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file format"}), 400
    
    filepath = os.path.join(Config.UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    # Process CSV file
    data = pd.read_csv(filepath)
    for _, row in data.iterrows():
        FirefighterModel.insert_data(row.to_dict())

    return jsonify({"message": "File uploaded and data stored successfully"}), 200

@app_routes.route("/firefighters", methods=["GET"])
def get_firefighters():
    """Fetch all firefighter data."""
    data = FirefighterModel.get_all_data()
    return jsonify(data), 200