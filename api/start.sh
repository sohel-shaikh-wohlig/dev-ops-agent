#!/bin/bash

# DevOps Automation FastAPI Quick Start Script

echo "=================================="
echo "DevOps Automation FastAPI Quick Start"
echo "=================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating from .env.example..."
    cp .env.example .env
    echo "✅ .env file created. Please edit it with your ArgoCD credentials."
    echo ""
    echo "Required variables:"
    echo "  - ARGOCD_SERVER"
    echo "  - ARGOCD_TOKEN (or ARGOCD_USERNAME and ARGOCD_PASSWORD)"
    echo ""
    echo "After editing .env, run this script again."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "=================================="
echo "✅ Setup complete!"
echo "=================================="
echo ""
echo "To start the server:"
echo "  source venv/bin/activate"
echo "  uvicorn app.main:app --reload"
echo ""
echo "API will be available at:"
echo "  http://localhost:8000"
echo "  Documentation: http://localhost:8000/docs"
echo ""
