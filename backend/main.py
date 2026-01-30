# backend/main.py - This is the entry point for the FastAPI application
# It imports and exposes the app from app_main.py which contains all the endpoints

from app_main import app

# This file serves as the WSGI/ASGI entry point for the application
# Run with: uvicorn main:app --host 0.0.0.0 --port 8000
