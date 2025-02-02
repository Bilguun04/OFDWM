from flask import Blueprint, request, jsonify, render_template
import pandas as pd
from models import FirefighterModel
from config import Config
import os
from logic import main

app_routes = Blueprint("app_routes", __name__)

def allowed_file(filename):
    """Check if the file is a CSV."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@app_routes.route("/", methods=["GET"])
def index():
    return render_template("index.html")

# @app_routes.route("/upload", methods=["POST"])
# def upload_csv():
#     """Handles CSV file uploads."""
#     if "file" not in request.files:
#         return jsonify({"error": "No file uploaded"}), 400

#     file = request.files["file"]

#     if file.filename == "" or not allowed_file(file.filename):
#         return jsonify({"error": "Invalid file format"}), 400

#     filepath = os.path.join(Config.UPLOAD_FOLDER, file.filename)
#     file.save(filepath)

#     # Process CSV file
#     data = pd.read_csv(filepath)

@app_routes.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        # Handle file upload
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["file"]

        if file.filename == "" or not allowed_file(file.filename):
            return jsonify({"error": "Invalid file format"}), 400

        filepath = os.path.join(Config.UPLOAD_FOLDER, file.filename)
        file.save(filepath)

        # Process CSV file
        data = pd.read_csv(filepath)
        
        # Call the main function from logic with the CSV data
        result = main(data)
        
        # Return the result
        return jsonify({"success": "File uploaded and processed", "result": result}), 200
    else:
        # Render the upload form
        return render_template("upload.html")