#!/bin/bash
# Script to install Playwright browsers for Streamlit Cloud
# This script will be run during deployment if needed

echo "Installing Playwright browsers..."
python -m playwright install chromium
python -m playwright install-deps chromium || true
echo "Playwright browsers installed successfully!"

