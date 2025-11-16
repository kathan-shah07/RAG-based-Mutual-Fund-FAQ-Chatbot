"""
Vercel serverless function handler for FastAPI app.
This file wraps the FastAPI app for Vercel's serverless environment.
"""
from api.main import app
from mangum import Mangum

# Wrap FastAPI app with Mangum for AWS Lambda/Vercel compatibility
handler = Mangum(app, lifespan="off")

