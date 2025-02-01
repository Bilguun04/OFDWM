import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "mysecretkey")
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/firefighter_db")
    UPLOAD_FOLDER = "uploads"
    ALLOWED_EXTENSIONS = {"csv"}