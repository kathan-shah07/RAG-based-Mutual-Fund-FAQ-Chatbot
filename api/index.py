"""
Vercel serverless function handler for FastAPI app.
This file wraps the FastAPI app for Vercel's serverless environment.
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import app
from mangum import Mangum

# Wrap FastAPI app with Mangum for AWS Lambda/Vercel compatibility
# lifespan="off" disables startup/shutdown events (not supported in serverless)
handler = Mangum(app, lifespan="off")

