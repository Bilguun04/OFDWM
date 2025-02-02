import logging
import os
from routes import app_routes

import pandas as pd
from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename

import routes
from monte_carlo import parallel_monte_carlo  # Monte Carlo logic

# Initialize Flask app

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["ALLOWED_EXTENSIONS"] = {"csv"}

app.register_blueprint(app_routes)

# Ensure upload directory exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(message)s")


def allowed_file(filename):
    """Check if the uploaded file is a CSV."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]


@app.route("/")
def index():
    """Render the homepage."""
    return render_template("upload.html")


@app.route("/upload", methods=["POST"])
def upload():
    """Handles CSV uploads and processes Monte Carlo assignment logic."""
    if "teams_file" not in request.files or "incidents_file" not in request.files:
        return jsonify({"error": "Both team and incident CSV files are required!"}), 400

    teams_file = request.files["teams_file"]
    incidents_file = request.files["incidents_file"]

    if teams_file.filename == "" or incidents_file.filename == "":
        return jsonify({"error": "No file selected!"}), 400

    if not (allowed_file(teams_file.filename) and allowed_file(incidents_file.filename)):
        return jsonify({"error": "Only CSV files are allowed!"}), 400

    # Secure filenames and save them
    teams_filename = secure_filename(teams_file.filename)
    incidents_filename = secure_filename(incidents_file.filename)
    teams_filepath = os.path.join(app.config["UPLOAD_FOLDER"], teams_filename)
    incidents_filepath = os.path.join(app.config["UPLOAD_FOLDER"], incidents_filename)

    teams_file.save(teams_filepath)
    incidents_file.save(incidents_filepath)

    # Load CSVs into DataFrames
    teams_df = pd.read_csv(teams_filepath)
    incidents_df = pd.read_csv(incidents_filepath)
    incidents_df = incidents_df[incidents_df["status"].isin(["open", "in_progress"])].copy()

    # Run Monte Carlo Assignment
    best_solution_df, best_cost = parallel_monte_carlo(teams_df, incidents_df, num_runs=20, refine_iters=300)

    # Save result CSV
    result_filename = "best_assignment_parallel.csv"
    result_filepath = os.path.join(app.config["UPLOAD_FOLDER"], result_filename)
    best_solution_df.to_csv(result_filepath, index=False)

    logging.info(f"Best cost found across all parallel runs: {best_cost}")

    return send_file(result_filepath, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)
