"""
Simple Vercel handler for testing - minimal FastAPI app
Use this if the main handler doesn't work
"""
from fastapi import FastAPI
from mangum import Mangum

# Create minimal app for testing
app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "FastAPI on Vercel", "status": "working"}

@app.get("/health")
def health():
    return {"status": "healthy"}

# Export handler for Vercel
handler = Mangum(app)

